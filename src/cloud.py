import json
import os

import boto3
from botocore.config import Config


def client(service):
    return boto3.client(
        service,
        endpoint_url=os.environ["AWS_ENDPOINT_URL"],
        region_name=os.environ["AWS_DEFAULT_REGION"],
        config=Config(
            connect_timeout=5,
            read_timeout=25,
            retries={"max_attempts": 2, "mode": "standard"},
            s3={"addressing_style": "path"},
        ),
    )


def validate_quotes(quotes):
    if not isinstance(quotes, list) or not quotes:
        raise ValueError("Expected a nonempty quote array")
    for quote in quotes:
        if not isinstance(quote, dict):
            raise ValueError("Expected quote objects")
        for field in ("text", "author"):
            if not isinstance(quote.get(field), str) or not quote[field].strip():
                raise ValueError(f"Missing {field}")
        if not isinstance(quote.get("tags"), list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in quote["tags"]
        ):
            raise ValueError("Invalid tags")
    if len({(q["text"], q["author"]) for q in quotes}) != len(quotes):
        raise ValueError("Duplicate quotes")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
