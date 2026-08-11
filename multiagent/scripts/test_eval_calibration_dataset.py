"""Khoa E5 chi dung hai split calibration trong manifest.

Chay: .venv\\Scripts\\python.exe scripts\\test_eval_calibration_dataset.py
"""
import atexit
import csv
import os
import shutil
import tempfile

from eval_calibration import doc_nhan, gold_ids

_THU_MUC_TAM = []


def check(ten, thuc, mong):
    if thuc != mong:
        raise AssertionError(f"{ten}: mong {mong!r}, thuc {thuc!r}")
    print(f"[PASS] {ten}")


def fixture_dataset(bo_file=None):
    thu_muc = tempfile.mkdtemp(prefix="e5-gold-")
    _THU_MUC_TAM.append(thu_muc)
    labels = os.path.join(thu_muc, "labels.csv")
    raw = os.path.join(thu_muc, "raw")
    os.mkdir(raw)
    with open(labels, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sample_id", "split", "label"])
        writer.writeheader()
        writer.writerows([
            {"sample_id": "G-001", "split": "gold-real",
             "label": "needs_revision"},
            {"sample_id": "P-001a", "split": "gold-pert", "label": "rejected"},
            {"sample_id": "C-001", "split": "functional-clean", "label": "publish"},
        ])
    for sid in ("G-001", "P-001a"):
        if f"{sid}.txt" != bo_file:
            with open(os.path.join(raw, f"{sid}.txt"), "w", encoding="utf-8") as f:
                f.write(sid)
    return labels, raw


def test_chi_lay_hai_split_gold():
    labels, raw = fixture_dataset()
    check("ID calibration", gold_ids(labels, raw), ["G-001", "P-001a"])
    check("nhan calibration", doc_nhan(labels),
          {"G-001": "needs_revision", "P-001a": "rejected"})


def test_gold_id_thieu_file_phai_dung():
    labels, raw = fixture_dataset(bo_file="P-001a.txt")
    try:
        gold_ids(labels, raw)
    except FileNotFoundError as error:
        check("neu dung ID thieu", "P-001a" in str(error), True)
    else:
        raise AssertionError("gold_ids phai dung khi thieu file")


@atexit.register
def _don_dep():
    for thu_muc in _THU_MUC_TAM:
        shutil.rmtree(thu_muc)


if __name__ == "__main__":
    test_chi_lay_hai_split_gold()
    test_gold_id_thieu_file_phai_dung()
