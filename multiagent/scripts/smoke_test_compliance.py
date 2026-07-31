"""Smoke test thủ công cho src/agents/compliance.py — gọi Claude API thật
kết hợp với rule-based blacklist, xác nhận run() trả về đúng cấu trúc và
rule-based flag được gộp đúng vào danh sách flags.

Cách chạy (sau khi đã điền ANTHROPIC_API_KEY trong .env):
    .venv\\Scripts\\python.exe scripts\\smoke_test_compliance.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.compliance import run, match_blacklist

title = "VF3 - Chiếc xe điện tốt nhất thế giới, giảm giá không giới hạn"
body = (
    "VinFast VF3 là chiếc xe điện tốt nhất thế giới hiện nay, với mức giá "
    "không đối thủ nào sánh được. Chương trình giảm giá không giới hạn, "
    "đây là cơ hội duy nhất trong đời để sở hữu xe điện."
)

if __name__ == "__main__":
    fields = {"title": title, "body": body, "meta_description": ""}
    result = run(fields)
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

    # Xac nhan rule-based flags duoc hop nhat dung: goi match_blacklist()
    # tren cung van ban ma run() da xu ly, roi kiem tra tat ca rule
    # tu match_blacklist() deu co mat trong result["flags"]
    rule_flags = match_blacklist(f"{title}\n{body}")
    expected_rules = {f["rule"] for f in rule_flags}
    actual_rules = {f["rule"] for f in result["flags"]}
    assert expected_rules.issubset(actual_rules), (
        f"Rule-based flags phai co mat trong ket qua merge. "
        f"Thieu: {expected_rules - actual_rules}"
    )
    print(f"PASS: {len(expected_rules)} rule-based rule(s) co mat trong ket qua merge")

    # --- CP3 fact-check: claim VF 8 500km (cong bo that 420km) phai bi bat ---
    print("\n--- CP3 fact-check ---")
    fc_fields = {
        "title": "Đánh giá VF 8",
        "body": "Với một lần sạc đầy, VinFast VF 8 có thể đi tới 500km.",
        "meta_description": "",
    }
    fc_result = run(fc_fields)
    fc_flags = [f for f in fc_result["flags"] if "sai lệch" in f["rule"].lower()]
    print(f"fact-check flags: {fc_flags}")
    # Luu y: can chay src/kb/build_kb.py truoc. Neu KB chua dung, fact-check
    # bo qua (khong flag) - khi do in canh bao thay vi assert cung.
    if fc_flags:
        print("PASS: CP3 bat duoc claim VF 8 500km sai lech")
    else:
        print("LUU Y: khong co flag CP3 - kiem tra da chay build_kb.py chua, "
              "va so lieu KB da verify chua (sources.md muc 2)")
