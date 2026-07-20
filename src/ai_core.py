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
    """Call Claude with an agent's system prompt + article content.

    Returns a dict matching output_schema (guaranteed via structured outputs).
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
