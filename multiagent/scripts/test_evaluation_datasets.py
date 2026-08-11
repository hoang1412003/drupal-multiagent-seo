"""Kiem tra tach biet giua gold calibration va functional-clean."""
import csv
import glob
import os
import sys


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
GOLD_LABELS = os.path.join(ROOT, "docs", "goldset", "labels.csv")
CLEAN_LABELS = os.path.join(ROOT, "docs", "functional-tests", "clean_labels.csv")
GOLD_RAW = os.path.join(ROOT, "docs", "goldset", "raw")
GOLD_HTML = os.path.join(ROOT, "docs", "goldset", "raw_html")
CLEAN_DIR = os.path.join(ROOT, "docs", "functional-tests", "clean")
CLEAN_HTML = os.path.join(ROOT, "docs", "functional-tests", "raw_html")

_results = []


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(name, actual, expected):
    _results.append((name, actual == expected, actual, expected))


def test_gold_set_chi_co_33_mau_gp():
    rows = read_csv(GOLD_LABELS)
    check("gold có 33 mẫu", len(rows), 33)
    check("gold chỉ có G/P", all(r["sample_id"].startswith(("G-", "P-")) for r in rows), True)
    check("gold chỉ có hai split", {r["split"] for r in rows}, {"gold-real", "gold-pert"})


def test_functional_clean_co_10_mau_publish():
    rows = read_csv(CLEAN_LABELS)
    check("functional có 10 mẫu", len(rows), 10)
    check("mọi mẫu là corrected", {r["variant"] for r in rows}, {"corrected"})
    check("mọi nhãn kỳ vọng publish", {r["expected_label"] for r in rows}, {"publish"})


def test_c_duoc_tach_vat_ly_khoi_gold():
    check("gold raw không có C", glob.glob(os.path.join(GOLD_RAW, "C-*.txt")), [])
    check("gold html không có C", glob.glob(os.path.join(GOLD_HTML, "C-*.html")), [])
    check("functional clean đủ TXT", len(glob.glob(os.path.join(CLEAN_DIR, "C-*.txt"))), 10)
    check("functional clean đủ HTML", len(glob.glob(os.path.join(CLEAN_HTML, "C-*.html"))), 10)


if __name__ == "__main__":
    test_gold_set_chi_co_33_mau_gp()
    test_functional_clean_co_10_mau_publish()
    test_c_duoc_tach_vat_ly_khoi_gold()

    failed = False
    for name, ok, actual, expected in _results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed = True
            print(f"    thực tế : {actual!r}")
            print(f"    kỳ vọng : {expected!r}")
    sys.exit(1 if failed else 0)
