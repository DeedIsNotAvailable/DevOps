import argparse
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

from botocore.exceptions import ClientError

from cloud import client, json_bytes, validate_quotes


def wait_ready():
    deadline = time.monotonic() + 120
    last_error = None
    while time.monotonic() < deadline:
        try:
            client("s3").list_buckets()
            client("sqs").list_queues()
            print("Floci S3 and SQS APIs are ready")
            return
        except Exception as error:
            last_error = error
            time.sleep(2)
    raise TimeoutError(f"Floci did not become ready: {last_error}")


def configure():
    outputs = json.loads(Path("/runtime/terraform-output.json").read_text())
    values = {
        "S3_BUCKET": outputs["bucket_name"]["value"],
        "SQS_QUEUE_URL": outputs["queue_url"]["value"],
    }
    for value in values.values():
        if not isinstance(value, str) or "\n" in value or "\r" in value:
            raise ValueError("Invalid Terraform output")
    Path("/runtime/app.env").write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8"
    )
    print(f"Connection settings exported from Terraform: {values}")


def queue_messages():
    query = urlencode({"QueueUrl": os.environ["SQS_QUEUE_URL"]})
    # Floci's inspection API includes in-flight jobs and does not consume them.
    with urlopen(f"{os.environ['AWS_ENDPOINT_URL']}/_aws/sqs/messages?{query}", timeout=10) as response:
        return json.load(response)["messages"]


def check_result(job):
    key = f"results/{job['job_id']}.json"
    response = client("s3").get_object(Bucket=os.environ["S3_BUCKET"], Key=key)
    body = response["Body"].read()
    quotes = json.loads(body)
    validate_quotes(quotes)
    if any(message["MessageId"] == job["message_id"] for message in queue_messages()):
        return None
    return body, quotes


def submit():
    job_id = str(uuid4())
    response = client("sqs").send_message(
        QueueUrl=os.environ["SQS_QUEUE_URL"], MessageBody=json.dumps({"job_id": job_id})
    )
    job = {"job_id": job_id, "message_id": response["MessageId"]}
    Path("out").mkdir(exist_ok=True)
    Path("out/last-job.json").write_bytes(json_bytes(job))
    print(f"Sent exactly one job: {job_id}", flush=True)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            result = check_result(job)
            if result:
                body, quotes = result
                Path("out/result.json").write_bytes(body)
                print(f"Validated {len(quotes)} quotes in S3; message {job['message_id']} is deleted")
                print(f"Downloaded s3://{os.environ['S3_BUCKET']}/results/{job_id}.json to out/result.json")
                return
        except ClientError as error:
            if error.response["Error"]["Code"] not in ("NoSuchKey", "404"):
                raise
        time.sleep(1)
    raise TimeoutError("Job did not finish in 180 seconds; inspect make logs")


def verify():
    job = json.loads(Path("out/last-job.json").read_text())
    result = check_result(job)
    if result is None:
        raise RuntimeError("The message still exists (possibly in flight)")
    body, quotes = result
    print(f"Verified S3 object: {len(quotes)} quotes; message is absent, including in-flight messages")


def status():
    print("Buckets:", client("s3").list_buckets().get("Buckets", []))
    print("Queues:", client("sqs").list_queues().get("QueueUrls", []))
    if os.environ.get("SQS_QUEUE_URL"):
        print("Messages (including in-flight):", queue_messages())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["wait", "configure", "submit", "verify", "status"])
    args = parser.parse_args()
    {"wait": wait_ready, "configure": configure, "submit": submit,
     "verify": verify, "status": status}[args.command]()
