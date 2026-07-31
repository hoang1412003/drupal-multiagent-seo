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


if __name__ == "__main__":
    with open(PAIRS, encoding="utf-8") as f:
        pairs = json.load(f)

    r1 = recall_at_k(pairs, 1)
    r3 = recall_at_k(pairs, 3)
    print(f"\nrecall@1 = {r1:.2f}")
    print(f"recall@3 = {r3:.2f}  (tieu chi >= 0.90)")
    print("DAT" if r3 >= 0.9 else "CHUA DAT - sua chunking truoc, doi embedding sau (rag-design muc 5)")
    sys.exit(0 if r3 >= 0.9 else 1)
