import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def call_agent(system_prompt: str, title: str, body: str, output_schema: dict) -> dict:
    """Gọi Claude với system prompt của 1 agent + nội dung bài viết.

    Trả về dict đúng cấu trúc output_schema (đảm bảo bằng structured outputs).
    """
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Title: {title}\n\nBody: {body}",
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": output_schema,
            }
        },
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
