"""Read-only loader and integrity validator for functional dataset v2."""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


SCHEMA = [
    "sample_id", "parent_sample_id", "source_url", "variant",
    "expected_label", "target_code", "removed_codes", "injected_codes",
    "annotator", "generator_model", "guideline_version", "created_at",
    "parent_sha256", "content_sha256", "notes",
]

EXPECTED_CORRECTED_IDS = {f"GC-{index:03d}" for index in range(1, 21)}
EXPECTED_COVERAGE_IDS = {
    "CV-A3-01", "CV-A5-01", "CV-A5-02", "CV-A6-01", "CV-A6-02",
    "CV-A7-01", "CV-A7-02", "CV-B6-01", "CV-B7-01",
    "CV-B9-01", "CV-B9-02",
}
EXPECTED_GOLD_PARENTS = {f"G-{index:03d}" for index in range(1, 21)}
VALID_TARGET = re.compile(r"^(?:A[1-7]|B(?:[1-9]|1[01]))$")
VALID_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class FunctionalSample:
    sample_id: str
    parent_sample_id: str
    source_url: str
    variant: str
    expected_label: str
    target_code: str
    removed_codes: Sequence[str]
    injected_codes: Sequence[str]
    annotator: str
    generator_model: str
    guideline_version: str
    created_at: str
    parent_sha256: str
    content_sha256: str
    notes: str
    content_path: Path


class DatasetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DatasetInventory:
    corrected: Sequence[FunctionalSample]
    coverage: Sequence[FunctionalSample]

    @property
    def corrected_ids(self) -> set[str]:
        return {sample.sample_id for sample in self.corrected}

    @property
    def coverage_ids(self) -> set[str]:
        return {sample.sample_id for sample in self.coverage}


@dataclass(frozen=True)
class _Parent:
    source_url: str
    content_path: Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _codes(value: str) -> tuple[str, ...]:
    return tuple(code.strip() for code in value.split(";") if code.strip())


def _content_path(content_dir: Path, sample_id: str) -> Path:
    allowed_root = content_dir.resolve()
    candidate = (content_dir / f"{sample_id}.txt").resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError as error:
        raise DatasetValidationError(
            f"content path escapes allowed root for {sample_id!r}: {candidate}"
        ) from error
    if not candidate.is_file():
        raise DatasetValidationError(
            f"missing content file for {sample_id!r}: {candidate}"
        )
    return candidate


def _require_fields(row: dict[str, str], sample_id: str) -> None:
    required = (
        "sample_id", "parent_sample_id", "source_url", "variant",
        "expected_label", "annotator", "generator_model",
        "guideline_version", "created_at", "parent_sha256",
        "content_sha256", "notes",
    )
    missing = [field for field in required if not (row.get(field) or "").strip()]
    if missing:
        raise DatasetValidationError(
            f"missing required value(s) for {sample_id!r}: {', '.join(missing)}"
        )
    if row["guideline_version"].strip() != "v1.4":
        raise DatasetValidationError(
            f"guideline_version for {sample_id!r} must be 'v1.4'"
        )
    for field in ("parent_sha256", "content_sha256"):
        if not VALID_SHA256.fullmatch(row[field].strip().lower()):
            raise DatasetValidationError(
                f"{field} for {sample_id!r} must be a 64-character SHA-256"
            )


def _validate_variant(
    sample_id: str,
    expected_variant: str,
    expected_label: str,
    target_code: str,
    injected_codes: tuple[str, ...],
) -> None:
    if expected_variant == "corrected":
        if expected_label != "publish":
            raise DatasetValidationError(
                f"corrected sample {sample_id!r} must have expected_label='publish'"
            )
        if target_code:
            raise DatasetValidationError(
                f"corrected sample {sample_id!r} must have an empty target_code"
            )
        if injected_codes:
            raise DatasetValidationError(
                f"corrected sample {sample_id!r} must have empty injected_codes"
            )
        return

    if expected_variant != "criterion-coverage":
        raise DatasetValidationError(f"unsupported expected variant: {expected_variant!r}")
    if not VALID_TARGET.fullmatch(target_code):
        raise DatasetValidationError(
            f"coverage sample {sample_id!r} must have one valid target_code"
        )
    if injected_codes != (target_code,):
        raise DatasetValidationError(
            f"coverage sample {sample_id!r} must inject exactly its target_code"
        )
    required_label = "rejected" if target_code.startswith("A") else "needs_revision"
    if expected_label != required_label:
        raise DatasetValidationError(
            f"target {target_code} requires expected_label={required_label!r}"
        )


def load_manifest(
    path: Path,
    content_dir: Path,
    expected_variant: str,
) -> list[FunctionalSample]:
    path = Path(path)
    content_dir = Path(content_dir)
    if not path.is_file():
        raise DatasetValidationError(f"missing manifest: {path}")

    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        actual_headers = list(reader.fieldnames or [])
        if actual_headers != SCHEMA:
            raise DatasetValidationError(
                f"manifest header mismatch: expected {SCHEMA!r}, got {actual_headers!r}"
            )
        rows = list(reader)

    samples: list[FunctionalSample] = []
    seen: set[str] = set()
    for line_number, row in enumerate(rows, 2):
        sample_id = (row.get("sample_id") or "").strip()
        if sample_id in seen:
            raise DatasetValidationError(f"duplicate sample_id {sample_id!r} at line {line_number}")
        seen.add(sample_id)
        _require_fields(row, sample_id)

        variant = row["variant"].strip()
        if variant != expected_variant:
            raise DatasetValidationError(
                f"variant for {sample_id!r} must be {expected_variant!r}, got {variant!r}"
            )
        content_path = _content_path(content_dir, sample_id)
        content_sha256 = row["content_sha256"].strip().lower()
        if sha256_file(content_path) != content_sha256:
            raise DatasetValidationError(f"content_sha256 mismatch for {sample_id!r}")

        target_code = row["target_code"].strip()
        injected_codes = _codes(row["injected_codes"])
        expected_label = row["expected_label"].strip()
        _validate_variant(
            sample_id,
            expected_variant,
            expected_label,
            target_code,
            injected_codes,
        )
        samples.append(FunctionalSample(
            sample_id=sample_id,
            parent_sample_id=row["parent_sample_id"].strip(),
            source_url=row["source_url"].strip(),
            variant=variant,
            expected_label=expected_label,
            target_code=target_code,
            removed_codes=_codes(row["removed_codes"]),
            injected_codes=injected_codes,
            annotator=row["annotator"].strip(),
            generator_model=row["generator_model"].strip(),
            guideline_version=row["guideline_version"].strip(),
            created_at=row["created_at"].strip(),
            parent_sha256=row["parent_sha256"].strip().lower(),
            content_sha256=content_sha256,
            notes=row["notes"].strip(),
            content_path=content_path,
        ))
    return samples


def _load_parents(manifest: Path, content_dir: Path) -> dict[str, _Parent]:
    if not manifest.is_file():
        raise DatasetValidationError(f"missing parent manifest: {manifest}")
    with manifest.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or [])
        required = {"sample_id", "source_url"}
        if not required.issubset(headers):
            raise DatasetValidationError(
                f"parent manifest {manifest} is missing columns {sorted(required - headers)!r}"
            )
        rows = list(reader)

    parents: dict[str, _Parent] = {}
    for row in rows:
        sample_id = (row.get("sample_id") or "").strip()
        source_url = (row.get("source_url") or "").strip()
        if not sample_id or not source_url:
            raise DatasetValidationError(f"missing parent ID/source_url in {manifest}")
        if sample_id in parents:
            raise DatasetValidationError(f"duplicate parent sample_id {sample_id!r} in {manifest}")
        parents[sample_id] = _Parent(source_url, _content_path(content_dir, sample_id))
    return parents


def _reject_cross_dataset_overlap(datasets: dict[str, dict[str, _Parent]]) -> None:
    owner_by_id: dict[str, str] = {}
    owner_by_path: dict[Path, str] = {}
    for dataset_name, samples in datasets.items():
        for sample_id, sample in samples.items():
            prior_id_owner = owner_by_id.get(sample_id)
            if prior_id_owner is not None:
                raise DatasetValidationError(
                    f"sample ID overlap: {sample_id!r} belongs to {prior_id_owner} and {dataset_name}"
                )
            owner_by_id[sample_id] = dataset_name

            resolved_path = sample.content_path.resolve()
            prior_path_owner = owner_by_path.get(resolved_path)
            if prior_path_owner is not None:
                raise DatasetValidationError(
                    f"content path overlap: {resolved_path} belongs to {prior_path_owner} and {dataset_name}"
                )
            owner_by_path[resolved_path] = dataset_name


def _as_parents(samples: Sequence[FunctionalSample]) -> dict[str, _Parent]:
    return {
        sample.sample_id: _Parent(sample.source_url, sample.content_path)
        for sample in samples
    }


def _validate_parent(sample: FunctionalSample, parents: dict[str, _Parent]) -> None:
    parent = parents.get(sample.parent_sample_id)
    if parent is None:
        raise DatasetValidationError(
            f"parent {sample.parent_sample_id!r} for {sample.sample_id!r} does not exist"
        )
    if sample.source_url != parent.source_url:
        raise DatasetValidationError(
            f"source_url mismatch between {sample.sample_id!r} and parent {sample.parent_sample_id!r}"
        )
    if sample.parent_sha256 != sha256_file(parent.content_path):
        raise DatasetValidationError(
            f"parent_sha256 mismatch for {sample.sample_id!r}"
        )


def _require_exact_ids(name: str, actual: set[str], expected: set[str]) -> None:
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing!r}")
        if extra:
            details.append(f"extra={extra!r}")
        raise DatasetValidationError(f"{name} inventory mismatch: {', '.join(details)}")


def validate_inventory(repo_root: Path) -> DatasetInventory:
    repo_root = Path(repo_root).resolve()
    functional_root = repo_root / "docs" / "functional-tests"
    corrected = load_manifest(
        functional_root / "gold-corrected-labels.csv",
        functional_root / "gold-corrected",
        "corrected",
    )
    coverage = load_manifest(
        functional_root / "criterion-coverage-labels.csv",
        functional_root / "criterion-coverage",
        "criterion-coverage",
    )
    gold = _load_parents(
        repo_root / "docs" / "goldset" / "labels.csv",
        repo_root / "docs" / "goldset" / "raw",
    )
    clean = _load_parents(
        functional_root / "clean_labels.csv",
        functional_root / "clean",
    )
    corrected_parents = _as_parents(corrected)
    coverage_parents = _as_parents(coverage)

    _reject_cross_dataset_overlap({
        "gold": gold,
        "clean": clean,
        "corrected": corrected_parents,
        "coverage": coverage_parents,
    })
    inventory = DatasetInventory(tuple(corrected), tuple(coverage))
    _require_exact_ids("corrected", inventory.corrected_ids, EXPECTED_CORRECTED_IDS)
    _require_exact_ids("coverage", inventory.coverage_ids, EXPECTED_COVERAGE_IDS)
    _require_exact_ids(
        "corrected parent",
        {sample.parent_sample_id for sample in corrected},
        EXPECTED_GOLD_PARENTS,
    )

    for sample in corrected:
        _validate_parent(sample, gold)
    available_coverage_parents = {**clean, **corrected_parents}
    for sample in coverage:
        _validate_parent(sample, available_coverage_parents)
    return inventory


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    sha = commands.add_parser("sha256", help="print the SHA-256 of one file")
    sha.add_argument("path", type=Path)

    manifest = commands.add_parser("validate-manifest", help="validate all existing manifest rows")
    manifest.add_argument("--manifest", required=True, type=Path)
    manifest.add_argument("--content-dir", required=True, type=Path)
    manifest.add_argument(
        "--variant",
        required=True,
        choices=("corrected", "criterion-coverage"),
    )

    commands.add_parser("validate-inventory", help="validate the exact repository inventory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "sha256":
            print(sha256_file(args.path))
        elif args.command == "validate-manifest":
            samples = load_manifest(args.manifest, args.content_dir, args.variant)
            print(f"valid samples: {len(samples)}")
        else:
            inventory = validate_inventory(Path(__file__).resolve().parents[2])
            print(
                f"valid inventory: {len(inventory.corrected)} corrected, "
                f"{len(inventory.coverage)} coverage"
            )
    except (DatasetValidationError, FileNotFoundError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
