"""Khoa contract manifest candidate AI v1.4 va provenance cua no.

Chay: .venv\\Scripts\\python.exe scripts\\test_goldset_ai_v14.py
"""
import csv
from collections import Counter
from hashlib import sha256
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[2]
LABELS_AI = REPO / "docs" / "goldset" / "labels-ai-v1.4.csv"
GOLD_V1 = REPO / "docs" / "goldset" / "labels.csv"

_hong = False


def check(ten, thuc, mong):
    global _hong
    if thuc != mong:
        _hong = True
        print(f"[FAIL] {ten}: mong {mong!r}, thuc {thuc!r}")
    else:
        print(f"[PASS] {ten}")


def main() -> int:
    with open(LABELS_AI, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    check(
        "du cot manifest candidate",
        set(rows[0]),
        {
            "sample_id", "source_url", "split", "variant", "injected_codes",
            "defect_codes", "label", "annotator", "date", "guideline_version",
            "notes", "provenance",
        },
    )
    check("33 rows", len(rows), 33)
    check("20 G", sum(r["sample_id"].startswith("G-") for r in rows), 20)
    check("13 P", sum(r["sample_id"].startswith("P-") for r in rows), 13)
    check("label counts", Counter(r["label"] for r in rows),
          Counter({"needs_revision": 23, "rejected": 10}))
    check("candidate provenance",
          {r["provenance"] for r in rows}, {"AI-annotated-partially-exposed"})
    check("guideline v1.4", {r["guideline_version"] for r in rows}, {"v1.4"})
    check("gold v1 unchanged", sha256(GOLD_V1.read_bytes()).hexdigest(),
          "ac74ee3e3f11103f8afb0223685aa3e4004dae7e8eaf3b9cd6f716bb58dfcb17")
    return 1 if _hong else 0


if __name__ == "__main__":
    sys.exit(main())
