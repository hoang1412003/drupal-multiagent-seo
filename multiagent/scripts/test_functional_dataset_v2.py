"""Behavior tests for the corrected/criterion-coverage dataset contract.

Run from ``multiagent``::

    .venv\\Scripts\\python.exe scripts\\test_functional_dataset_v2.py

Every expected value below is literal or computed with ``hashlib`` rather
than with the production helper under test.
"""
from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
# The managed sandbox cannot write to the host-wide default TEMP directory.
# Keep real TemporaryDirectory fixtures inside this worktree.
tempfile.tempdir = str(SCRIPT_DIR)

from functional_dataset_v2 import (  # noqa: E402
    DatasetValidationError,
    _Parent,
    _reject_cross_dataset_overlap,
    load_manifest,
    sha256_file,
    validate_inventory,
)


SCHEMA = [
    "sample_id", "parent_sample_id", "source_url", "variant",
    "expected_label", "target_code", "removed_codes", "injected_codes",
    "annotator", "generator_model", "guideline_version", "created_at",
    "parent_sha256", "content_sha256", "notes",
]

EXPECTED_GC_IDS = {f"GC-{index:03d}" for index in range(1, 21)}
EXPECTED_CV_IDS = {
    "CV-A3-01", "CV-A5-01", "CV-A5-02", "CV-A6-01", "CV-A6-02",
    "CV-A7-01", "CV-A7-02", "CV-B6-01", "CV-B7-01",
    "CV-B9-01", "CV-B9-02",
}

CV_PARENTS = {
    "CV-A3-01": "GC-006",
    "CV-A5-01": "GC-003",
    "CV-A5-02": "GC-018",
    "CV-A6-01": "GC-010",
    "CV-A6-02": "C-008",
    "CV-A7-01": "C-005",
    "CV-A7-02": "GC-019",
    "CV-B6-01": "C-001",
    "CV-B7-01": "GC-018",
    "CV-B9-01": "GC-011",
    "CV-B9-02": "GC-016",
}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, str]], headers=SCHEMA) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _base_row(variant: str, sample_id: str) -> dict[str, str]:
    coverage = variant == "criterion-coverage"
    target = "A3" if coverage else ""
    return {
        "sample_id": sample_id,
        "parent_sample_id": "GC-001" if coverage else "G-001",
        "source_url": "/source/G-001",
        "variant": variant,
        "expected_label": "rejected" if coverage else "publish",
        "target_code": target,
        "removed_codes": "" if coverage else "B3;B8",
        "injected_codes": target,
        "annotator": "A1",
        "generator_model": "gpt-5",
        "guideline_version": "v1.4",
        "created_at": "2026-08-17",
        "parent_sha256": "1" * 64,
        "content_sha256": "",
        "notes": "fixture",
    }


def _manifest_fixture(
    root: Path,
    *,
    variant: str = "corrected",
    sample_id: str | None = None,
    overrides: dict[str, str] | None = None,
    headers=SCHEMA,
    create_content: bool = True,
) -> tuple[Path, Path, dict[str, str]]:
    sid = sample_id or ("CV-A3-01" if variant == "criterion-coverage" else "GC-001")
    content_dir = root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    payload = f"content for {sid}".encode("utf-8")
    row = _base_row(variant, sid)
    row["content_sha256"] = _digest(payload)
    row.update(overrides or {})
    if create_content:
        content_path = content_dir / f"{sid}.txt"
        content_path.parent.mkdir(parents=True, exist_ok=True)
        content_path.write_bytes(payload)
    manifest = root / "manifest.csv"
    _write_csv(manifest, [row], headers)
    return manifest, content_dir, row


def _make_repo(root: Path) -> None:
    gold_dir = root / "docs" / "goldset" / "raw"
    clean_dir = root / "docs" / "functional-tests" / "clean"
    corrected_dir = root / "docs" / "functional-tests" / "gold-corrected"
    coverage_dir = root / "docs" / "functional-tests" / "criterion-coverage"
    for directory in (gold_dir, clean_dir, corrected_dir, coverage_dir):
        directory.mkdir(parents=True, exist_ok=True)

    gold_rows = []
    for index in range(1, 21):
        sid = f"G-{index:03d}"
        source = f"/source/{sid}"
        (gold_dir / f"{sid}.txt").write_text(f"gold {sid}", encoding="utf-8")
        gold_rows.append({"sample_id": sid, "source_url": source})
    _write_csv(
        root / "docs" / "goldset" / "labels.csv",
        gold_rows,
        ["sample_id", "source_url"],
    )

    clean_rows = []
    for index in range(1, 11):
        sid = f"C-{index:03d}"
        source = f"/source/{sid}"
        (clean_dir / f"{sid}.txt").write_text(f"clean {sid}", encoding="utf-8")
        clean_rows.append({"sample_id": sid, "source_url": source})
    _write_csv(
        root / "docs" / "functional-tests" / "clean_labels.csv",
        clean_rows,
        ["sample_id", "source_url"],
    )

    corrected_rows = []
    corrected_sources: dict[str, str] = {}
    for index in range(1, 21):
        sid = f"GC-{index:03d}"
        parent = f"G-{index:03d}"
        source = f"/source/{parent}"
        payload = f"corrected {sid}".encode("utf-8")
        path = corrected_dir / f"{sid}.txt"
        path.write_bytes(payload)
        row = _base_row("corrected", sid)
        row.update({
            "parent_sample_id": parent,
            "source_url": source,
            "parent_sha256": _digest((gold_dir / f"{parent}.txt").read_bytes()),
            "content_sha256": _digest(payload),
        })
        corrected_rows.append(row)
        corrected_sources[sid] = source
    _write_csv(
        root / "docs" / "functional-tests" / "gold-corrected-labels.csv",
        corrected_rows,
    )

    coverage_rows = []
    for sid in sorted(EXPECTED_CV_IDS):
        target = sid.split("-")[1]
        parent = CV_PARENTS[sid]
        if parent.startswith("GC-"):
            parent_path = corrected_dir / f"{parent}.txt"
            source = corrected_sources[parent]
        else:
            parent_path = clean_dir / f"{parent}.txt"
            source = f"/source/{parent}"
        payload = f"coverage {sid}".encode("utf-8")
        (coverage_dir / f"{sid}.txt").write_bytes(payload)
        row = _base_row("criterion-coverage", sid)
        row.update({
            "parent_sample_id": parent,
            "source_url": source,
            "target_code": target,
            "injected_codes": target,
            "expected_label": "rejected" if target.startswith("A") else "needs_revision",
            "parent_sha256": _digest(parent_path.read_bytes()),
            "content_sha256": _digest(payload),
        })
        coverage_rows.append(row)
    _write_csv(
        root / "docs" / "functional-tests" / "criterion-coverage-labels.csv",
        coverage_rows,
    )


def _expect_error(name: str, action, fragment: str) -> None:
    try:
        action()
    except DatasetValidationError as error:
        if fragment.casefold() not in str(error).casefold():
            raise AssertionError(
                f"{name}: expected error containing {fragment!r}, got {error!r}"
            ) from error
        print(f"[PASS] {name}")
    else:
        raise AssertionError(f"{name}: expected DatasetValidationError")


# Mutation caught: deleting the seen-ID check would accept the second row.
def test_duplicate_sample_id_bi_tu_choi() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, row = _manifest_fixture(root)
        _write_csv(manifest, [row, row])
        _expect_error(
            "duplicate sample_id",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "duplicate",
        )


# Mutation caught: accepting a subset/superset of the schema would pass one case.
def test_header_thieu_hoac_thua_bi_tu_choi() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(root, headers=SCHEMA[:-1])
        _expect_error(
            "missing header",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "header",
        )
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(root, headers=SCHEMA + ["extra"])
        _expect_error(
            "extra header",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "header",
        )


# Mutations caught: string-prefix path checks and omission of file existence check.
def test_path_escape_va_content_file_thieu_bi_tu_choi() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(root, sample_id="../escaped")
        _expect_error(
            "path escape",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "path",
        )
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(root, create_content=False)
        _expect_error(
            "missing content file",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "missing",
        )


# Mutation caught: trusting content_sha256 without hashing the bytes would pass.
def test_content_sha256_sai_bi_tu_choi() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(
            root, overrides={"content_sha256": "0" * 64}
        )
        _expect_error(
            "content sha mismatch",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "content_sha256",
        )


# Mutations caught: relaxing either corrected invariant accepts its subcase.
def test_corrected_phai_publish_va_khong_injected_codes() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(
            root, overrides={"expected_label": "needs_revision"}
        )
        _expect_error(
            "corrected label",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "publish",
        )
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(
            root, overrides={"injected_codes": "B3"}
        )
        _expect_error(
            "corrected injected codes",
            lambda: load_manifest(manifest, content_dir, "corrected"),
            "injected_codes",
        )


# Mutation caught: accepting zero/multiple/different injected targets passes a subcase.
def test_coverage_phai_co_dung_mot_target_trung_injected_code() -> None:
    invalid = (
        {"target_code": "", "injected_codes": ""},
        {"target_code": "A3", "injected_codes": "A3;A5"},
        {"target_code": "A3", "injected_codes": "A5"},
    )
    for index, overrides in enumerate(invalid, 1):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, content_dir, _ = _manifest_fixture(
                root, variant="criterion-coverage", overrides=overrides
            )
            _expect_error(
                f"coverage target case {index}",
                lambda: load_manifest(manifest, content_dir, "criterion-coverage"),
                "target",
            )


# Mutation caught: reversing or omitting the A/B-to-label decision rule would pass.
def test_target_a_rejected_va_target_b_needs_revision() -> None:
    cases = (
        ({"target_code": "A3", "injected_codes": "A3", "expected_label": "needs_revision"}, "rejected"),
        ({"target_code": "B6", "injected_codes": "B6", "expected_label": "rejected"}, "needs_revision"),
    )
    for overrides, expected_word in cases:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, content_dir, _ = _manifest_fixture(
                root, variant="criterion-coverage", overrides=overrides
            )
            _expect_error(
                f"target label {overrides['target_code']}",
                lambda: load_manifest(manifest, content_dir, "criterion-coverage"),
                expected_word,
            )


# Mutations caught: skipping parent existence/hash/source checks accepts a subcase.
def test_parent_hien_huu_phai_khop_sha256_va_source_url() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "gold-corrected-labels.csv"
        headers, rows = _read_csv(manifest)
        rows[0]["parent_sha256"] = "0" * 64
        _write_csv(manifest, rows, headers)
        _expect_error("parent sha mismatch", lambda: validate_inventory(root), "parent_sha256")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "gold-corrected-labels.csv"
        headers, rows = _read_csv(manifest)
        rows[0]["parent_sample_id"] = "G-999"
        _write_csv(manifest, rows, headers)
        _expect_error("missing parent", lambda: validate_inventory(root), "parent")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "criterion-coverage-labels.csv"
        headers, rows = _read_csv(manifest)
        rows[0]["source_url"] = "/wrong-source"
        _write_csv(manifest, rows, headers)
        _expect_error("parent source mismatch", lambda: validate_inventory(root), "source_url")


# Mutation caught: keeping only the A/B severity rule would accept A5 under CV-A3-01.
def test_coverage_target_phai_khop_canonical_id() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "criterion-coverage-labels.csv"
        headers, rows = _read_csv(manifest)
        row = next(item for item in rows if item["sample_id"] == "CV-A3-01")
        row.update({"target_code": "A5", "injected_codes": "A5"})
        _write_csv(manifest, rows, headers)
        _expect_error(
            "canonical coverage target",
            lambda: validate_inventory(root),
            "canonical target_code",
        )


# Mutation caught: validating only the set of 20 G parents permits pair swaps.
def test_corrected_parent_phai_khop_canonical_id() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "gold-corrected-labels.csv"
        headers, rows = _read_csv(manifest)
        gold_dir = root / "docs" / "goldset" / "raw"
        by_id = {row["sample_id"]: row for row in rows}
        for corrected_id, parent_id in (("GC-001", "G-002"), ("GC-002", "G-001")):
            by_id[corrected_id].update({
                "parent_sample_id": parent_id,
                "source_url": f"/source/{parent_id}",
                "parent_sha256": _digest((gold_dir / f"{parent_id}.txt").read_bytes()),
            })
        _write_csv(manifest, rows, headers)
        _expect_error(
            "canonical corrected parent",
            lambda: validate_inventory(root),
            "canonical parent_sample_id",
        )


# Mutation caught: accepting any clean GC/C parent permits a different clean control.
def test_coverage_parent_phai_khop_canonical_id() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "criterion-coverage-labels.csv"
        headers, rows = _read_csv(manifest)
        row = next(item for item in rows if item["sample_id"] == "CV-A3-01")
        parent_path = root / "docs" / "functional-tests" / "clean" / "C-002.txt"
        row.update({
            "parent_sample_id": "C-002",
            "source_url": "/source/C-002",
            "parent_sha256": _digest(parent_path.read_bytes()),
        })
        _write_csv(manifest, rows, headers)
        _expect_error(
            "canonical coverage parent",
            lambda: validate_inventory(root),
            "canonical parent_sample_id",
        )


# Mutation caught: accepting partial or expanded inventories passes a subcase.
def test_inventory_khoa_exact_20_gc_va_11_cv() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        inventory = validate_inventory(root)
        if inventory.corrected_ids != EXPECTED_GC_IDS:
            raise AssertionError(f"wrong GC inventory: {inventory.corrected_ids!r}")
        if inventory.coverage_ids != EXPECTED_CV_IDS:
            raise AssertionError(f"wrong CV inventory: {inventory.coverage_ids!r}")
        print("[PASS] exact 20 GC + 11 CV inventory")

        manifest = root / "docs" / "functional-tests" / "gold-corrected-labels.csv"
        headers, rows = _read_csv(manifest)
        _write_csv(manifest, rows[:-1], headers)
        _expect_error("missing inventory ID", lambda: validate_inventory(root), "missing")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "gold-corrected-labels.csv"
        headers, rows = _read_csv(manifest)
        payload = b"corrected GC-021"
        path = root / "docs" / "functional-tests" / "gold-corrected" / "GC-021.txt"
        path.write_bytes(payload)
        extra = dict(rows[0])
        extra.update({"sample_id": "GC-021", "content_sha256": _digest(payload)})
        _write_csv(manifest, rows + [extra], headers)
        _expect_error("extra inventory ID", lambda: validate_inventory(root), "extra")


# Mutation caught: omitting cross-dataset ID separation accepts the collision.
def test_id_giua_bon_lop_khong_duoc_giao_nhau() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _make_repo(root)
        manifest = root / "docs" / "functional-tests" / "criterion-coverage-labels.csv"
        headers, rows = _read_csv(manifest)
        payload = b"coverage collision"
        collision_path = root / "docs" / "functional-tests" / "criterion-coverage" / "GC-001.txt"
        collision_path.write_bytes(payload)
        rows[0].update({"sample_id": "GC-001", "content_sha256": _digest(payload)})
        _write_csv(manifest, rows, headers)
        _expect_error("cross-dataset ID", lambda: validate_inventory(root), "overlap")


# Mutation caught: removing the resolved-path branch from the overlap validator
# accepts two different IDs that resolve to the same file inside an allowed root.
def test_content_path_overlap_di_toi_overlap_validator() -> None:
    with tempfile.TemporaryDirectory() as temp:
        allowed_root = Path(temp).resolve()
        shared_path = (allowed_root / "shared.txt").resolve()
        shared_path.write_text("same resolved path", encoding="utf-8")
        shared_path.relative_to(allowed_root)
        datasets = {
            "corrected": {"GC-001": _Parent("/source/G-001", shared_path)},
            "coverage": {"CV-A3-01": _Parent("/source/G-006", shared_path)},
        }
        _expect_error(
            "cross-dataset path",
            lambda: _reject_cross_dataset_overlap(datasets),
            "content path overlap",
        )


# CLI mutation caught: writing instead of only reading changes the fixture snapshot.
def test_sha256_va_cli_validate_manifest_chi_doc() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest, content_dir, _ = _manifest_fixture(root)
        content_path = content_dir / "GC-001.txt"
        expected = _digest(content_path.read_bytes())
        if sha256_file(content_path) != expected:
            raise AssertionError("sha256_file returned the wrong digest")

        before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        sha_result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "functional_dataset_v2.py"), "sha256", str(content_path)],
            text=True,
            capture_output=True,
            check=False,
        )
        if sha_result.returncode != 0 or sha_result.stdout.strip() != expected:
            raise AssertionError(f"sha256 CLI failed: {sha_result.stdout!r} {sha_result.stderr!r}")
        validate_result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "functional_dataset_v2.py"),
                "validate-manifest",
                "--manifest", str(manifest),
                "--content-dir", str(content_dir),
                "--variant", "corrected",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if validate_result.returncode != 0 or "1" not in validate_result.stdout:
            raise AssertionError(
                f"validate-manifest CLI failed: {validate_result.stdout!r} {validate_result.stderr!r}"
            )
        after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        if after != before:
            raise AssertionError("read-only CLI changed the fixture tree")
        print("[PASS] sha256 + validate-manifest CLI are read-only")


if __name__ == "__main__":
    tests = (
        test_duplicate_sample_id_bi_tu_choi,
        test_header_thieu_hoac_thua_bi_tu_choi,
        test_path_escape_va_content_file_thieu_bi_tu_choi,
        test_content_sha256_sai_bi_tu_choi,
        test_corrected_phai_publish_va_khong_injected_codes,
        test_coverage_phai_co_dung_mot_target_trung_injected_code,
        test_target_a_rejected_va_target_b_needs_revision,
        test_parent_hien_huu_phai_khop_sha256_va_source_url,
        test_coverage_target_phai_khop_canonical_id,
        test_corrected_parent_phai_khop_canonical_id,
        test_coverage_parent_phai_khop_canonical_id,
        test_inventory_khoa_exact_20_gc_va_11_cv,
        test_id_giua_bon_lop_khong_duoc_giao_nhau,
        test_content_path_overlap_di_toi_overlap_validator,
        test_sha256_va_cli_validate_manifest_chi_doc,
    )
    for test in tests:
        test()
    print(f"\n{len(tests)} test functions passed")
