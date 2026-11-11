import os
import logging
import urllib.parse

import boto3

from summarizer import summarize_text


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["BUCKET_NAME"]
INPUT_PREFIX = os.environ.get["INPUT_PREFIX"]
OUTPUT_PREFIX = os.environ.get["OUTPUT_PREFIX"]


def lambda_handler(event: dict, context):
    """Receive updated note files, summarize, and upload to S3 bucket output path."""
    logger.info("Received event: %s", event)

    records = event.get("Records", [])

    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        if bucket != BUCKET_NAME:
            logger.warning("Ignoring object from unexpected bucket: %s", bucket)
            continue

        if not key.startswith(INPUT_PREFIX):
            logger.info("Ignoring key outside input prefix: %s", key)
            continue

        if not key.endswith((".txt", ".md")):
            logger.info("Ignoring unsupported file type: %s", key)
            continue

        logger.info("Processing s3://%s/%s", bucket, key)

        text = read_text_from_s3(bucket, key)

        if not text.strip():
            logger.warning("File is empty: %s", key)
            continue

        summary = summarize_text(text)

        output_key = build_output_key(key)

        write_text_to_s3(bucket, output_key, summary)

        logger.info("Summary saved to s3://%s/%s", bucket, output_key)

    return {
        "statusCode": 200,
        "message": "Processing completed",
    }


def read_text_from_s3(bucket: str, key: str) -> str:
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read()
    return content.decode("utf-8")


def write_text_to_s3(bucket: str, key: str, text: str) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=text.encode("utf-8"),
        ContentType="text/markdown; charset=utf-8",
    )


def build_output_key(input_key: str) -> str:
    filename = input_key.replace(INPUT_PREFIX, "", 1)

    if filename.endswith(".txt"):
        filename = filename[:-4]
    elif filename.endswith(".md"):
        filename = filename[:-3]

    return f"{OUTPUT_PREFIX}{filename}-summary.md"
