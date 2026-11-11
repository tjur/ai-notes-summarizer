import os

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate

BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
AWS_REGION_NAME = os.environ["AWS_REGION_NAME"]


llm = ChatBedrock(
    model_id=BEDROCK_MODEL_ID,
    region_name=AWS_REGION_NAME,
    model_kwargs={
        "temperature": 0.2,
        "max_tokens": 1200,
    },
)


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an assistant that analyzes meeting notes and creates concise, practical summaries in English. "
                "Use only information explicitly present in the note. Do not invent missing names, dates, decisions, or tasks."
            ),
        ),
        (
            "user",
            """
Analyze the following note and prepare the response in Markdown.

Rules:
- Use only the information provided in the note.
- Do not add assumptions or external context.
- If information is missing, clearly state that it is not specified.
- Keep the summary concise and practical.

Return exactly the following sections:

# Summary

## Short Summary
A brief description in 3-5 sentences.

## Key Points
A bullet-point list of the most important points.

## Decisions
A list of decisions. If there are no clear decisions, write: "No clear decisions."

## Action Items
A task list in the following format:
- [ ] Task — owner, deadline if provided

If there are no clearly defined action items, write: "No clearly defined action items."

## Risks and Open Questions
A list of risks or open questions. If there are none, write: "None."

Note:
{text}
""",
        ),
    ]
)


chain = prompt | llm


def summarize_text(text: str) -> str:
    result = chain.invoke({"text": text})
    return result.content
