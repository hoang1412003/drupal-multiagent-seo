import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def call_agent(system_prompt: str, content: str, output_schema: dict) -> dict:
    """Gọi Claude với system prompt của 1 agent + nội dung bài viết.

    `content` là khối nội dung đã format sẵn (mỗi agent tự ghép các field nó
    quan tâm - xem docs/architecture.md mục 5). Trả về dict đúng cấu trúc
    output_schema (đảm bảo bằng structured outputs).
    """
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        temperature=0,  # giảm dao động điểm giữa các lần chấm - điều kiện để
                        # calibration ngưỡng từ gold set (Sprint 3) tái lập được
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": content,
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
