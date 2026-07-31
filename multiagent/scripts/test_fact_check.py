"""Test logic fact_check (CP3) bang fake extract/compare/retriever - khong
goi LLM hay KB that. Kiem 3 nhanh quan trong:
  - so lieu lech (cung model) -> flag critical
  - khong tra duoc (retrieve rong) -> KHONG flag
  - thong so tra ve khac model -> compare tra 'unverifiable' -> KHONG flag
Chay: .venv\\Scripts\\python.exe scripts\\test_fact_check.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import fact_check

CLAIM_VF8 = {"model": "VF 8", "metric": "tam_hoat_dong", "value": "500km",
             "field": "body", "excerpt": "VF 8 chạy 500km"}


def test_mismatch_makes_critical_flag():
    flags = fact_check.run(
        {"body": "VF 8 chạy 500km"},
        extract_fn=lambda f: [CLAIM_VF8],
        retriever=lambda q, ct, lc, **k: [{"text": "VF 8: 420km", "model": "VF 8", "score": 0.9, "source_url": "u"}],
        compare_fn=lambda pairs: [{"index": 0, "verdict": "mismatch", "reason": "500 != 420"}],
    )
    assert len(flags) == 1, f"phai co 1 flag, got {len(flags)}"
    assert flags[0]["severity"] == "critical"
    assert flags[0]["field"] == "body"
    assert "sai lệch" in flags[0]["rule"].lower()
    print("[PASS] so lieu lech -> flag critical")


def test_not_found_no_flag():
    flags = fact_check.run(
        {"body": "Model XYZ chạy 999km"},
        extract_fn=lambda f: [{"model": "XYZ", "metric": "tam_hoat_dong",
                               "value": "999km", "field": "body", "excerpt": "XYZ 999km"}],
        retriever=lambda q, ct, lc, **k: [],  # khong tra duoc
        compare_fn=lambda pairs: (_ for _ in ()).throw(AssertionError("khong duoc goi compare khi khong co hit")),
    )
    assert flags == [], "khong tra duoc -> khong flag (muc 'khong kiem chung duoc')"
    print("[PASS] khong tra duoc -> khong flag")


def test_unverifiable_no_flag():
    flags = fact_check.run(
        {"body": "VF 8 chạy 500km"},
        extract_fn=lambda f: [CLAIM_VF8],
        retriever=lambda q, ct, lc, **k: [{"text": "VF 9: 438km", "model": "VF 9", "score": 0.6, "source_url": "u"}],
        compare_fn=lambda pairs: [{"index": 0, "verdict": "unverifiable", "reason": "thong so la VF 9, khong phai VF 8"}],
    )
    assert flags == [], "khac model -> unverifiable -> khong flag"
    print("[PASS] khac model -> unverifiable -> khong flag")


def test_no_claims_no_llm():
    flags = fact_check.run(
        {"body": "bài không có số liệu"},
        extract_fn=lambda f: [],
        retriever=lambda *a, **k: (_ for _ in ()).throw(AssertionError("khong duoc retrieve khi khong co claim")),
        compare_fn=lambda pairs: (_ for _ in ()).throw(AssertionError("khong duoc compare")),
    )
    assert flags == [], "khong co claim -> khong flag, khong goi retrieve/compare"
    print("[PASS] khong co claim -> dung som")


if __name__ == "__main__":
    test_mismatch_makes_critical_flag()
    test_not_found_no_flag()
    test_unverifiable_no_flag()
    test_no_claims_no_llm()
    print("OK")
