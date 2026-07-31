"""Test compliance.run() gop flag fact-check dung, va khi fact_check loi
(KB chua dung) thi KHONG lam sap compliance. Monkeypatch fact_check + LLM
de khong goi API/KB that.
Chay: .venv\\Scripts\\python.exe scripts\\test_compliance_factcheck_merge.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import compliance, fact_check

# Stub LLM cua compliance: khong flag LLM, score 100
compliance.call_agent = lambda *a, **k: {"score": 100, "flags": []}


def test_factcheck_flag_merged():
    fact_check.run = lambda fields, **k: [
        {"field": "body", "severity": "critical", "rule": "Thông tin sai lệch so với thông số công bố chính thức", "excerpt": "VF 8 chạy 500km"}
    ]
    compliance.fact_check = fact_check  # dam bao compliance dung dung module da patch
    result = compliance.run({"title": "", "body": "VF 8 chạy 500km", "meta_description": ""})
    fc = [f for f in result["flags"] if "sai lệch" in f["rule"].lower()]
    assert len(fc) == 1, f"flag fact-check phai duoc gop, got {result['flags']}"
    print("[PASS] flag fact-check duoc gop vao compliance")


def test_factcheck_error_does_not_break():
    def boom(fields, **k):
        raise RuntimeError("KB chua dung")

    compliance.fact_check.run = boom
    result = compliance.run({"title": "", "body": "abc", "meta_description": ""})
    assert isinstance(result["flags"], list), "loi fact-check khong duoc lam sap run()"
    print("[PASS] loi fact-check khong lam sap compliance")


if __name__ == "__main__":
    test_factcheck_flag_merged()
    test_factcheck_error_does_not_break()
    print("OK")
