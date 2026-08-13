"""E2 - do recall@k cua KB fact-check (docs/evaluation-plan.md muc 4.2,
docs/rag-design.md muc 5). Can KB da dung: chay src/kb/build_kb.py truoc.

recall@k = ti le truy van co model dung nam trong top-k.
Tieu chi: recall@3 >= 0.9 (KB fact-check noi vao quyen phu quyet).
Chay: .venv\\Scripts\\python.exe scripts\\eval_retrieval.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retrieval import retrieve

PAIRS = os.path.join(os.path.dirname(__file__), "retrieval_eval_pairs.json")
THRESHOLD = 0.9


def recall_at_k(pairs, k):
    hit = 0
    for p in pairs:
        results = retrieve(p["query"], "cam_nang", "vi", top_k=k)
        models = [r["model"] for r in results]
        if p["expected_model"] in models:
            hit += 1
        else:
            print(f"  MISS@{k}: '{p['query']}' -> {models} (mong doi {p['expected_model']})")
    return hit / len(pairs)


def load_pairs():
    with open(PAIRS, encoding="utf-8") as handle:
        return json.load(handle)


def evaluate(pairs=None) -> dict:
    pairs = load_pairs() if pairs is None else pairs
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("E2 fact-check can it nhat mot query")
    r1 = recall_at_k(pairs, 1)
    r3 = recall_at_k(pairs, 3)
    return {
        "query_count": len(pairs),
        "recall_at_1": r1,
        "recall_at_3": r3,
        "threshold": THRESHOLD,
        "passed": r3 >= THRESHOLD,
    }


def print_report(result: dict) -> int:
    r1 = result["recall_at_1"]
    r3 = result["recall_at_3"]
    threshold = result["threshold"]
    passed = result["passed"]
    print(f"\nrecall@1 = {r1:.2f}")
    print(f"recall@3 = {r3:.2f}  (tieu chi >= {threshold:.2f})")
    print("DAT" if passed else "CHUA DAT - sua chunking truoc, doi embedding sau (rag-design muc 5)")
    return 0 if passed else 1


def main() -> int:
    return print_report(evaluate())


if __name__ == "__main__":
    sys.exit(main())
