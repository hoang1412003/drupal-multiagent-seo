"""Kiem tra tach biet giua gold calibration va functional-clean."""
import csv
import glob
import hashlib
import os
import sys


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
GOLD_LABELS = os.path.join(ROOT, "docs", "goldset", "labels.csv")
CLEAN_LABELS = os.path.join(ROOT, "docs", "functional-tests", "clean_labels.csv")
CORRECTED_LABELS = os.path.join(ROOT, "docs", "functional-tests", "gold-corrected-labels.csv")
COVERAGE_LABELS = os.path.join(ROOT, "docs", "functional-tests", "criterion-coverage-labels.csv")
CLEAN_REVIEW = os.path.join(ROOT, "docs", "evidence", "functional-clean-ai-review-v1.4.csv")
GOLD_RAW = os.path.join(ROOT, "docs", "goldset", "raw")
GOLD_HTML = os.path.join(ROOT, "docs", "goldset", "raw_html")
CLEAN_DIR = os.path.join(ROOT, "docs", "functional-tests", "clean")
CLEAN_HTML = os.path.join(ROOT, "docs", "functional-tests", "raw_html")
CORRECTED_DIR = os.path.join(ROOT, "docs", "functional-tests", "gold-corrected")
COVERAGE_DIR = os.path.join(ROOT, "docs", "functional-tests", "criterion-coverage")
CLEAN_SCHEMA = [
    "sample_id",
    "source_url",
    "variant",
    "expected_label",
    "annotator",
    "date",
    "guideline_version",
    "notes",
]
EXPECTED_C_IDS = [
    "C-001",
    "C-002",
    "C-003",
    "C-004",
    "C-005",
    "C-006",
    "C-007",
    "C-008",
    "C-009",
    "C-010",
]
EXPECTED_GC_IDS = [f"GC-{index:03d}" for index in range(1, 21)]
EXPECTED_CV_IDS = [
    "CV-A3-01",
    "CV-A5-01",
    "CV-A5-02",
    "CV-A6-01",
    "CV-A6-02",
    "CV-A7-01",
    "CV-A7-02",
    "CV-B6-01",
    "CV-B7-01",
    "CV-B9-01",
    "CV-B9-02",
]
REVIEW_SCHEMA = [
    "sample_id",
    "expected_label",
    "annotator",
    "generator_model",
    "guideline_version",
    "reviewed_at",
    "content_sha256",
    "notes",
]
GOLD_LABELS_SHA256 = "ac74ee3e3f11103f8afb0223685aa3e4004dae7e8eaf3b9cd6f716bb58dfcb17"
GOLD_RAW_SHA256 = {
    "G-001": "9337b1d583d2c70b30f85a0dda4532c5bf4b69b595b3291d59a3591fd7773cd8",
    "G-002": "9b2dfad49e3b8077cc74c968668d19dca4c5a375575a934349638bf4b85fb75a",
    "G-003": "dddee943f9b741ee6e2b4edd3b414327b07f352f4324d747d20e3ae5bb91aaa5",
    "G-004": "209e7fe880f3e36d503cd68d45227b9dea3314dadb50cea7b54ff6097ccfc2d4",
    "G-005": "88d96eac6d79b8d039d9f3915ac4b0ec0d77ec5f6813394332b6bb3d9c810847",
    "G-006": "379402cfb717dd4c928307252846fa2d981bd2957e80fb9d6823ac581c1f248e",
    "G-007": "b56b45553522346eda41f3b1c2d14b6cb8e652b554441e53b0802ae9e1ead693",
    "G-008": "59903fa0b08b1f583d0538d77f074da805acbc30a7f7c137b10c286ec0e4270e",
    "G-009": "9dc0f8b785100002639231fa9d13007da87bbddff78d8c7672b40c7ed3109b5c",
    "G-010": "9008e7ab4abc79450c34882bdf1f1b7101484657f75036ba8f949cccad71e4ad",
    "G-011": "6422a8d7d2723c82b6eed7bda1c523d324ea9f90826c2b2bf08f4c96bf3701bf",
    "G-012": "53a695abe60b0391071fd21a65fd4b2a9816e5be24ba6b05373579cc984925c0",
    "G-013": "ab9ce1caed6a2d41d607c2ebfa29b6f41c8c23b6aa7123b6311b17b06405588e",
    "G-014": "e88505b9ba7766a270056626925299b04c2d14697de532d61607129276b5f6f7",
    "G-015": "fcc3ae4714a596c4f2f222a3c3823e69521308dbb47b9d31fc62acee90126509",
    "G-016": "76d33d17c6390e096396deb55c644e396965e34503a5eaf8815bb081c6ba84d6",
    "G-017": "cbf7ec62fe7e25388974ae70486ef87b01bb26b98c4a081be77f5f3f1282f2c1",
    "G-018": "61877c25232629b0962e1e9c45f12df86f4551ba7ba34d8024198ceb6551a6e5",
    "G-019": "333b5a7d379d171264ed75f6f145866b98ebd16a13c9b087af7b7e1a9feffc63",
    "G-020": "ac59552bf24789548f8f557525cbfda05d1659249c4a4d69f3aa1a2bf45237e2",
    "P-001a": "0ca2f424cd00cd7689ae862a13fb7821521118cff46706f4f77eb2dc32403340",
    "P-001b": "c290878a1bd6fd812b9f10716af845d75147c3b088738580f55df1e4eb22a32f",
    "P-002a": "8cd6a0b104ae4937c24d42951802f50b0bf244020a62b47ca03b88942dcd0eb7",
    "P-003a": "1a87943181d84d7ab61754bf24ae35b5e56ae5661fee360ecf3fe6bf834f0a76",
    "P-004a": "c5287d3a2c20b96ffd2a1c95dcd54645ae9338956de3e1ec6c7811b81d938bfc",
    "P-004b": "194a5720ec6d4b87c3ea50216704fc25a13f90e07a0eeabdbf0965dd18def542",
    "P-005a": "54459fd64cf7bdf2f5da0d94e93769abeef221e31304061691bcde43c10723c9",
    "P-006a": "5d6f35c79b5c44e1d0a2224128f5be7f411a4d7df0f4b408ce51feb6528e9513",
    "P-007a": "3f318a83370f463065d53b88e3a800adf0b918f812ceb41027db3b47ca0e3e77",
    "P-007b": "f9b478583a134681ec94cb50865d431a3d8fc153c228ef752a2888d6df322880",
    "P-008a": "af070799b0e0e76648bbc4966db66d3ea76f5fe1122a5bd781aa8a17fbcd37ec",
    "P-009a": "e502e10facf05e617aab3c786f36fc45c9c56a9a5a5f80cb138dfa650ad12d70",
    "P-010a": "a0275ccfb6f88771ed170a6cc3f452fbac4e2badf7be25c915c1629a5bf2ace9",
}

_results = []


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(name, actual, expected):
    _results.append((name, actual == expected, actual, expected))


def test_gold_set_chi_co_33_mau_gp():
    _, rows = read_csv(GOLD_LABELS)
    check("gold có 33 mẫu", len(rows), 33)
    check("gold chỉ có G/P", all(r["sample_id"].startswith(("G-", "P-")) for r in rows), True)
    check("gold chỉ có hai split", {r["split"] for r in rows}, {"gold-real", "gold-pert"})
    check("gold có đúng 20 mẫu gold-real", sum(r["split"] == "gold-real" for r in rows), 20)
    check("gold có đúng 13 mẫu gold-pert", sum(r["split"] == "gold-pert" for r in rows), 13)


def test_functional_clean_co_10_mau_publish():
    headers, rows = read_csv(CLEAN_LABELS)
    sample_ids = [r["sample_id"] for r in rows]
    check("functional có 10 mẫu", len(rows), 10)
    check("functional đúng header/schema", headers, CLEAN_SCHEMA)
    check("functional có đúng C-001 đến C-010", sample_ids, EXPECTED_C_IDS)
    check("functional sample_id duy nhất", len(set(sample_ids)), len(sample_ids))
    check("mọi mẫu là corrected", {r["variant"] for r in rows}, {"corrected"})
    check("mọi nhãn kỳ vọng publish", {r["expected_label"] for r in rows}, {"publish"})


def test_c_duoc_tach_vat_ly_khoi_gold():
    check("gold raw không có C", glob.glob(os.path.join(GOLD_RAW, "C-*.txt")), [])
    check("gold html không có C", glob.glob(os.path.join(GOLD_HTML, "C-*.html")), [])
    check("functional clean đủ TXT", len(glob.glob(os.path.join(CLEAN_DIR, "C-*.txt"))), 10)
    check("functional clean đủ HTML", len(glob.glob(os.path.join(CLEAN_HTML, "C-*.html"))), 10)
    check(
        "functional TXT khớp basename C-001 đến C-010",
        sorted(os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(CLEAN_DIR, "C-*.txt"))),
        EXPECTED_C_IDS,
    )
    check(
        "functional HTML khớp basename C-001 đến C-010",
        sorted(os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(CLEAN_HTML, "C-*.html"))),
        EXPECTED_C_IDS,
    )


def test_bon_lop_du_lieu_tach_vat_ly_va_exact_ids():
    _, gold_rows = read_csv(GOLD_LABELS)
    _, clean_rows = read_csv(CLEAN_LABELS)
    _, corrected_rows = read_csv(CORRECTED_LABELS)
    _, coverage_rows = read_csv(COVERAGE_LABELS)
    id_sets = [
        {row["sample_id"] for row in gold_rows},
        {row["sample_id"] for row in clean_rows},
        {row["sample_id"] for row in corrected_rows},
        {row["sample_id"] for row in coverage_rows},
    ]
    check("corrected có exact GC-001 đến GC-020", sorted(id_sets[2]), EXPECTED_GC_IDS)
    check("coverage có exact 11 canonical IDs", sorted(id_sets[3]), sorted(EXPECTED_CV_IDS))
    check(
        "bốn lớp sample_id không giao nhau",
        len(set().union(*id_sets)),
        sum(len(ids) for ids in id_sets),
    )
    check(
        "gold raw khớp exact manifest IDs",
        sorted(os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(GOLD_RAW, "*.txt"))),
        sorted(id_sets[0]),
    )
    check(
        "corrected TXT khớp exact manifest IDs",
        sorted(os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(CORRECTED_DIR, "GC-*.txt"))),
        EXPECTED_GC_IDS,
    )
    check(
        "coverage TXT khớp exact manifest IDs",
        sorted(os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(COVERAGE_DIR, "CV-*.txt"))),
        sorted(EXPECTED_CV_IDS),
    )


def test_expected_publish_co_dung_30_mau_c_va_gc():
    _, clean_rows = read_csv(CLEAN_LABELS)
    _, corrected_rows = read_csv(CORRECTED_LABELS)
    publish_rows = clean_rows + corrected_rows
    check("expected-publish có đúng 30 mẫu", len(publish_rows), 30)
    check(
        "expected-publish có exact 10 C + 20 GC",
        sorted(row["sample_id"] for row in publish_rows),
        sorted(EXPECTED_C_IDS + EXPECTED_GC_IDS),
    )
    check("30 mẫu đều expected publish", {row["expected_label"] for row in publish_rows}, {"publish"})


def test_review_v14_khoa_10_c_publish_va_hash():
    headers, rows = read_csv(CLEAN_REVIEW)
    check("review v1.4 đúng schema", headers, REVIEW_SCHEMA)
    check("review v1.4 có exact 10 C", [row["sample_id"] for row in rows], EXPECTED_C_IDS)
    check("review v1.4 đều expected publish", {row["expected_label"] for row in rows}, {"publish"})
    check("review v1.4 annotator AI-A1", {row["annotator"] for row in rows}, {"AI-A1"})
    check(
        "review v1.4 không đoán generator model",
        {row["generator_model"] for row in rows},
        {"not-exposed-by-runtime"},
    )
    check("review v1.4 dùng guideline v1.4", {row["guideline_version"] for row in rows}, {"v1.4"})
    check("review v1.4 khóa ngày rà", {row["reviewed_at"] for row in rows}, {"2026-08-17"})
    actual_hashes = {
        sample_id: sha256_file(os.path.join(CLEAN_DIR, f"{sample_id}.txt"))
        for sample_id in EXPECTED_C_IDS
    }
    review_hashes = {row["sample_id"]: row["content_sha256"] for row in rows}
    check("review v1.4 hash khớp 10 C trên disk", review_hashes, actual_hashes)
    check(
        "review v1.4 ghi provenance partially exposed",
        all("AI-annotated-partially-exposed" in row["notes"] for row in rows),
        True,
    )


def test_gold_v1_va_33_raw_hash_bat_bien():
    labels_hash = sha256_file(GOLD_LABELS)
    actual_raw_hashes = {}
    for path in glob.glob(os.path.join(GOLD_RAW, "*.txt")):
        actual_raw_hashes[os.path.splitext(os.path.basename(path))[0]] = sha256_file(path)
    check("gold labels v1 hash bất biến", labels_hash, GOLD_LABELS_SHA256)
    check("33 gold raw hash bất biến", actual_raw_hashes, GOLD_RAW_SHA256)


if __name__ == "__main__":
    test_gold_set_chi_co_33_mau_gp()
    test_functional_clean_co_10_mau_publish()
    test_c_duoc_tach_vat_ly_khoi_gold()
    test_bon_lop_du_lieu_tach_vat_ly_va_exact_ids()
    test_expected_publish_co_dung_30_mau_c_va_gc()
    test_review_v14_khoa_10_c_publish_va_hash()
    test_gold_v1_va_33_raw_hash_bat_bien()

    failed = False
    for name, ok, actual, expected in _results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed = True
            print(f"    thực tế : {actual!r}")
            print(f"    kỳ vọng : {expected!r}")
    sys.exit(1 if failed else 0)
