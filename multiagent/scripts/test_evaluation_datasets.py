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
GOLD_LABELS_SHA256 = "07e444e445b74c317ea5de5b26bcf340186b871cc74615ea42cd7269af992ce6"
GOLD_RAW_SHA256 = {
    "G-001": "0a554f261673edc205f73271a74fa40460a9553aff46cdad4b833531b8054095",
    "G-002": "4da3f7926a217a75c7ef615a930503aa8b3d4fa75d82b1aed1b6e1af78f26d8b",
    "G-003": "e028b5fe884a3912deffd2a9ee5ff818cb1529a0ce6a1577ed5e5c357007b3b5",
    "G-004": "495c1c5965a7e4598691f813cb6322a4b14c9060f9b9e69bdf5489c7d5f04e76",
    "G-005": "b8c747eca8a21e156e66338ba0ee61e42dbf18425cb57103b2794e5c0e3ea302",
    "G-006": "cb7424df07e64e51df561b0ca36f2ff054acaed3e15a823a5c6c1962ce109bf4",
    "G-007": "af99cd70b4d4718c54d8c5c568a85fb11b5a241843673b2aa424cf07d37e1de7",
    "G-008": "d858ae2f3b6928bb7d1b799875cb6e310775172cabaf688f428c4f7f8a6c6da2",
    "G-009": "4e3de31ad69e2c13f10553a5111ff53cef2409f78a89eb981a79afd140dc0350",
    "G-010": "d9c25f99a6e92758b9d925eb2af5c2a06828c619373128554d1caa411e06624a",
    "G-011": "88bec505d377789cfea8b353a1c8731d4bcce33b60c69eb78005a1d0ce88233c",
    "G-012": "c29ddd5deb28fbdb8a94058db4539f89218b383f09714989d17b1a36ae6278d9",
    "G-013": "b5bf7371eb8cd66fa3d918d92d4c2fd559228f6712b5b627813aecdb4e4fddac",
    "G-014": "f4767fc1b52c7995dbdc02a086706251d895bded00051ce01ddbcb84d7d25794",
    "G-015": "df4238b0320bbf6b9e3756cb8b83756f7e99f8c8a77c62fc5b92aeb4f9626a99",
    "G-016": "9dc0ea867856519cc758c239eae09d7fedfcde6835d58fb248a738c7d336efda",
    "G-017": "7faaf34a79efff49882f31e418fa0bb310a39495d07f96d0d3e3fe8b8748853d",
    "G-018": "5018287914ca2fb9e818a95aea17d8a998368e8ed68db3f4da751bc64016dc24",
    "G-019": "c885e42c1d1c9326bce443899d42480e3b5bb1b8059a4410001ce1184aee74a3",
    "G-020": "b6ff4f37597c42a59a1f61dbebfa54f52a748ac9fdc920c3a43d849f747186e4",
    "P-001a": "37123588e43268347eed69a37af0c6bdf7232eea5eebaf152bf8a6c14bdc3786",
    "P-001b": "41550ae26c28aadd32a563d32fad27ea3a01975eefb0250084e9b3be3122dc3b",
    "P-002a": "500df6d44b6a1011aacfeb70e2e86e64eecf7849fec9bbe32d0d2010abb452a2",
    "P-003a": "6475a5c7f40773d77e18648688673bfdea517527a72bc0662a4a234855b958f5",
    "P-004a": "4b8f10b3eefb22174d350666c09ba3e1906936b8e6aac7959664520807736c31",
    "P-004b": "6204bbb27219de6f05eba6c74e337dc9c04d282d3e6aa6c411442819473b7d22",
    "P-005a": "bdd3c63a3b395cead58bb9ad684cfecfdc8bf726047f68e7696056bde43d9c53",
    "P-006a": "4f113f6c9f8d9eed06f83d2a989237a8e19f66fb0ae54d1208c4bde0ddd32be1",
    "P-007a": "4a48db29e30df79c8e6464c9337dc33df08e3d7a473452df48400d0fe3ab285e",
    "P-007b": "38e4d244527b8d469ba13a374fc4d5725af981eb814f3f5618e8e9c390316472",
    "P-008a": "ae867e4f3028955931cede2db737a0a60000b97f6ad6be308f3ce609e810f9ba",
    "P-009a": "96f7d800f4aa2eba1e09b02b028f7fc75d03f13afe47103d04be7a5f603985cf",
    "P-010a": "b9d7c0af286809a05bcdbcc4159ee7a3fcaa6e851067c1dae4cc13d95bcbc0fa",
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
