import os

import aws_cdk as cdk
from dotenv import load_dotenv

from ai_notes_summarizer.ai_notes_summarizer_stack import AiNotesSummarizerStack, Config

load_dotenv()

app = cdk.App()

AiNotesSummarizerStack(
    app,
    "AiNotesSummarizerStack",
    env=cdk.Environment(
        account=os.environ["AWS_ACCOUNT_ID"],
        region=os.environ["AWS_REGION"],
    ),
    config=Config(
        input_prefix=os.environ.get("INPUT_PREFIX", "input/"),
        output_prefix=os.environ.get("OUTPUT_PREFIX", "summarized/"),
        bedrock_model_id=os.environ.get(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        ),
    ),
)

app.synth()
