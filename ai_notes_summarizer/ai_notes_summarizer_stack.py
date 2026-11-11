import os
from dataclasses import dataclass
from aws_cdk import (
    CfnOutput,
    Duration,
    DockerVolume,
    RemovalPolicy,
    Stack,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_s3,
    aws_s3_notifications,
)
from constructs import Construct


@dataclass
class Config:
    input_prefix: str
    output_prefix: str
    bedrock_model_id: str


# create local cache directory
pip_cache_dir = os.path.abspath(".cache/pip")
os.makedirs(pip_cache_dir, exist_ok=True)

class AiNotesSummarizerStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            config: Config,
            **kwargs,

        ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        stack = Stack.of(self)

        # create S3 bucket
        bucket = aws_s3.Bucket(
            self,
            id="NotesBucket",
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # create lambda function using code defined in lambda_src directory;
        # deployment-ready artifacts must be put into /asset-output directory on Docker container
        summarizer_fn = aws_lambda.Function(
            self,
            "NotesSummarizerFunction",
            runtime=aws_lambda.Runtime.PYTHON_3_14,
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset(
                "lambda_src",
                bundling={
                    "image": aws_lambda.Runtime.PYTHON_3_14.bundling_image,  # Docker container
                    "environment": {
                        "HOME": "/tmp",
                        "PIP_CACHE_DIR": "/tmp/pip-cache",
                    },
                    "volumes": [
                        DockerVolume(
                            host_path=pip_cache_dir,
                            container_path="/tmp/pip-cache",
                        )
                    ],
                    "command": [
                        "bash",
                        "-c",
                        # install requirements (with caching) and copy lambda code
                        (
                            "mkdir -p /tmp/pip-cache &&"
                            "pip install --cache-dir /tmp/pip-cache -r requirements.txt -t /asset-output &&"
                            "cp -au . /asset-output"
                        ),
                    ],
                },
            ),
            timeout=Duration.seconds(120),
            memory_size=1024,
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "OUTPUT_PREFIX": config.output_prefix,
                "BEDROCK_MODEL_ID": config.bedrock_model_id,
                "AWS_REGION_NAME": stack.region,
            },
            log_group=aws_logs.LogGroup(stack, "LogGroup", retention=aws_logs.RetentionDays.ONE_WEEK),
            description="Function summarizing uploaded S3 notes using Amazon Bedrock and uploading the result to S3 output path."
        )

        # grant read and write access for lambda
        bucket.grant_read_write(summarizer_fn)

        summarizer_fn.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        for suffix in [".txt", ".md"]:
            bucket.add_event_notification(
                aws_s3.EventType.OBJECT_CREATED,
                aws_s3_notifications.LambdaDestination(summarizer_fn),
                aws_s3.NotificationKeyFilter(prefix=config.input_prefix, suffix=suffix),
            )

        # outputs
        CfnOutput(
            self,
            "NotesBucketName",
            value=bucket.bucket_name,
        )
