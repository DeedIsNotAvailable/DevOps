import json
import os
from pathlib import Path
import signal
import time
import traceback

from cloud import client, json_bytes, validate_quotes
from scrape import scrape_quotes


def process_message(message, sqs, s3, bucket, queue_url):
    job = json.loads(message["Body"])
    if not isinstance(job.get("job_id"), str) or not job["job_id"]:
        raise ValueError("Missing job_id")
    key = f"results/{job['job_id']}.json"
    quotes = scrape_quotes()
    validate_quotes(quotes)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json_bytes(quotes),
        ContentType="application/json; charset=utf-8",
        Metadata={"job-id": job["job_id"]},
    )
    # Acknowledge ONLY after S3 confirms the result was stored.
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
    print(f"Completed {job['job_id']}: {len(quotes)} quotes, s3://{bucket}/{key}; message deleted", flush=True)


def main():
    sqs, s3 = client("sqs"), client("s3")
    bucket, queue_url = os.environ["S3_BUCKET"], os.environ["SQS_QUEUE_URL"]
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # Fail early if deploy was called with missing resources or wrong settings.
    s3.head_bucket(Bucket=bucket)
    sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])
    Path("/tmp/worker-ready").touch()
    print(f"Waiting for jobs at {queue_url}; results bucket: {bucket}", flush=True)
    while not stopping:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=10
            )
            for message in response.get("Messages", []):
                try:
                    process_message(message, sqs, s3, bucket, queue_url)
                except Exception:
                    traceback.print_exc()
                    # Keep the job and make it eligible for a later retry.
                    sqs.change_message_visibility(
                        QueueUrl=queue_url,
                        ReceiptHandle=message["ReceiptHandle"],
                        VisibilityTimeout=10,
                    )
                    time.sleep(2)
        except Exception:
            traceback.print_exc()
            time.sleep(2)


if __name__ == "__main__":
    main()
