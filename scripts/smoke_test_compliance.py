"""Smoke test thủ công cho src/agents/compliance.py — gọi Claude API thật
kết hợp với rule-based blacklist, xác nhận run() trả về đúng cấu trúc và
rule-based flag được gộp đúng vào danh sách flags.

Cách chạy (sau khi đã điền ANTHROPIC_API_KEY trong .env):
    .venv\\Scripts\\python.exe scripts\\smoke_test_compliance.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.compliance import run

title = "VF3 - Chiếc xe điện tốt nhất thế giới, giảm giá không giới hạn"
body = (
    "VinFast VF3 là chiếc xe điện tốt nhất thế giới hiện nay, với mức giá "
    "không đối thủ nào sánh được. Chương trình giảm giá không giới hạn, "
    "đây là cơ hội duy nhất trong đời để sở hữu xe điện."
)

if __name__ == "__main__":
    result = run(title, body)
    print(f"score={result['score']}")
    print(f"flags ({len(result['flags'])}):")
    for f in result["flags"]:
        print(f"  {f}")

    assert isinstance(result["score"], int), "score phai la int"
    assert isinstance(result["flags"], list), "flags phai la list"

    critical_flags = [f for f in result["flags"] if f["severity"] == "critical"]
    assert len(critical_flags) >= 1, (
        "Phai co it nhat 1 flag critical tu rule-based (van ban chua 'tot nhat')"
    )
    print("PASS: co flag critical tu rule-based nhu ky vong")
