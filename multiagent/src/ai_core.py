import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

_client = None

# Nhật ký token của các lần gọi LLM, để đo chi phí thật (E4) thay vì ước
# lượng bằng cách đếm ký tự chia 4 - với tiếng Việt cách ước lượng đó sai
# đáng kể (docs/evaluation-plan.md mục 4.4).
#
# Dùng danh sách ở mức module thay vì đổi kiểu trả về của call_agent(): đổi
# kiểu trả về sẽ buộc sửa cả 4 agent, trong khi ở đây chỉ cần quan sát. Danh
# sách KHÔNG tự xoá - người gọi tự reset khi muốn đo một khoảng.
USAGE_LOG: "list[dict]" = []


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
        # 1024 QUÁ NHỎ - đã gây lỗi thật: chấm bài G-001 (2234 từ), Content
        # Quality tìm được nhiều lỗi nên JSON bị cắt đúng ở token thứ 1024,
        # parse hỏng, agent bị đánh dấu lỗi và Aggregator lặng lẽ chia lại
        # trọng số cho 3 agent còn lại. Bài càng dài càng dễ dính.
        #
        # Tiếng Việt tốn token gấp 2-3 lần tiếng Anh cho cùng nội dung, nên
        # phần gợi ý sửa bằng tiếng Việt chạm trần rất sớm.
        #
        # Nâng trần KHÔNG làm tăng chi phí: Anthropic tính tiền theo số token
        # thực sinh ra, không theo trần.
        max_tokens=4096,
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
    USAGE_LOG.append(
        {
            "model": MODEL,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
    )

    # Bắt cụt sớm và nói rõ nguyên nhân. Không có nhánh này thì JSON cụt rơi
    # xuống json.loads() và văng ra "Unterminated string at column 1963" -
    # thông báo đó không hề gợi ý rằng vấn đề là max_tokens, nên rất dễ đi
    # sửa nhầm chỗ (docs/architecture.md mục 7 - "validate ngay khi nhận").
    if response.stop_reason == "max_tokens":
        raise ValueError(
            f"LLM trả về bị cắt cụt vì chạm trần max_tokens "
            f"({response.usage.output_tokens} token). Nội dung quá dài hoặc "
            f"agent tìm ra quá nhiều lỗi - cần nâng max_tokens trong ai_core.py."
        )

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
