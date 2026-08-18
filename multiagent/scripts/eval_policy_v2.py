"""Core evaluator versioned cho candidate ``cam-nang-vn-v2``.

Module scope co y khong import ``ai_core`` hay bat ky agent/provider nao.
Dataset va release contract phai duoc validate truoc; chi default paid path
moi lazy-import bon agent. Test/preflight tiem ``agent_runner`` nen hoan toan
offline va duoc danh dau ``is_fixture=true`` trong raw.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

import yaml

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from decision_policy import (  # noqa: E402
    AGENT_ORDER,
    POLICY_V2,
    PolicyContractError,
    evaluate,
    require_policy_version,
)
from drupal_client import _extract_image_alt  # noqa: E402
from label_helper import parse_sample  # noqa: E402
from review_platform.pricing import estimate_usage  # noqa: E402


DATASET_KINDS = frozenset({"e1", "gold", "corrected", "coverage"})
LABELS = frozenset({"publish", "needs_revision", "rejected"})
GUIDELINE_VERSION = "v1.4"
RUBRIC_VERSION = "v1"
SCHEMA_VERSION = 1
LABEL_PROVENANCE = "AI-annotated-partially-exposed"
E1_IDS = tuple(f"G-{index:03d}" for index in range(1, 11))
GOLD_IDS = (
    *(f"G-{index:03d}" for index in range(1, 21)),
    "P-001a", "P-001b", "P-002a", "P-003a", "P-004a", "P-004b",
    "P-005a", "P-006a", "P-007a", "P-007b", "P-008a", "P-009a",
    "P-010a",
)
CLEAN_IDS = tuple(f"C-{index:03d}" for index in range(1, 11))
GOLD_CORRECTED_IDS = tuple(f"GC-{index:03d}" for index in range(1, 21))
CORRECTED_IDS = CLEAN_IDS + GOLD_CORRECTED_IDS
COVERAGE_IDS = (
    "CV-A3-01", "CV-A5-01", "CV-A5-02", "CV-A6-01", "CV-A6-02",
    "CV-A7-01", "CV-A7-02", "CV-B6-01", "CV-B7-01", "CV-B9-01", "CV-B9-02",
)

_DATASET_MANIFEST_PATHS = {
    "e1": ("docs/goldset/labels-ai-v1.4.csv", "docs/goldset/sources.md"),
    "gold": ("docs/goldset/labels-ai-v1.4.csv", "docs/goldset/sources.md"),
    "corrected": (
        "docs/functional-tests/clean_labels.csv",
        "docs/evidence/functional-clean-ai-review-v1.4.csv",
        "docs/functional-tests/gold-corrected-labels.csv",
    ),
    "coverage": ("docs/functional-tests/criterion-coverage-labels.csv",),
}

RELEASE_FIELDS = (
    "dataset_kind",
    "policy_version",
    "guideline_version",
    "rubric_version",
    "guideline_hash",
    "rubric_hash",
    "prompt_version",
    "model",
    "scoring_hash",
    "policy_hash",
    "safety_rules_hash",
    "fact_kb_hash",
    "brand_kb_hash",
    "embedding_hash",
    "embedding_provenance",
    "weights",
    "dataset_manifest_hashes",
    "content_hashes_sha256",
    "data_head",
    "git_head",
    "assessment_as_of",
    "output_path",
    "ordered_sample_ids",
)


class EvaluationContractError(ValueError):
    """Release, dataset hoac raw inventory khong con dang tin cay."""


@dataclass(frozen=True)
class EvaluationSample:
    sample_id: str
    fields: dict
    expected_label: str
    split: str
    source_url: str
    content_sha256: str
    # Chi co gia tri cho dataset "corrected" (GC-*) va "coverage" (CV-*);
    # None cho e1/gold va cho C-* (khong co parent).
    parent_sample_id: str | None = None
    target_code: str | None = None


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as error:
        raise EvaluationContractError(f"khong doc duoc artifact: {path}") from error


def _canonical_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EvaluationContractError("release tuple khong JSON-canonical duoc") from error
    return _sha256_bytes(encoded)


def _validate_dataset_kind(kind: str) -> str:
    if kind not in DATASET_KINDS:
        raise EvaluationContractError(f"unknown dataset kind: {kind!r}")
    return kind


def _validate_assessment_date(value: str) -> str:
    if not isinstance(value, str):
        raise EvaluationContractError("assessment_as_of phai la YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise EvaluationContractError("assessment_as_of phai la YYYY-MM-DD") from error
    if parsed.isoformat() != value:
        raise EvaluationContractError("assessment_as_of phai la YYYY-MM-DD")
    return value


def _validate_sha(name: str, value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise EvaluationContractError(f"{name} phai la SHA-256 chu thuong")
    return value


def _validate_git_commit(name: str, value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise EvaluationContractError(f"{name} phai la Git SHA-1 40 ky tu")
    return value


def _fields_from_file(path: Path) -> dict:
    parsed = parse_sample(str(path))
    body = parsed.get("body", "") or ""
    return {
        "title": parsed.get("title", "") or "",
        "body": body,
        "summary": parsed.get("summary", "") or "",
        "meta_description": parsed.get("meta_description", "") or "",
        "url_alias": parsed.get("url_alias", "") or "",
        "image_alt": _extract_image_alt({"relationships": {}}, body),
    }


def _labels_rows(repo_root: Path) -> list[dict]:
    path = repo_root / "docs" / "goldset" / "labels-ai-v1.4.csv"
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as error:
        raise EvaluationContractError(f"khong doc duoc labels manifest: {path}") from error
    if len(rows) != 33:
        raise EvaluationContractError(
            f"labels AI-v1.4 phai co exact 33 row, nhan {len(rows)}"
        )
    ids = [row.get("sample_id") for row in rows]
    if ids != list(GOLD_IDS):
        raise EvaluationContractError("labels AI-v1.4 sai canonical ordered IDs")
    for row in rows:
        sample_id = row["sample_id"]
        if row.get("label") not in LABELS:
            raise EvaluationContractError(f"{sample_id} co label khong hop le")
        if row.get("guideline_version") != GUIDELINE_VERSION:
            raise EvaluationContractError(f"{sample_id} sai guideline_version")
        if row.get("provenance") != LABEL_PROVENANCE:
            raise EvaluationContractError(f"{sample_id} sai label provenance")
        if row.get("split") not in {"gold-real", "gold-pert"}:
            raise EvaluationContractError(f"{sample_id} sai gold split")
    return rows


def _csv_rows(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as error:
        raise EvaluationContractError(f"khong doc duoc manifest: {path}") from error


def _gold_corrected_rows(repo_root: Path) -> list[dict]:
    """20 GC, moi cai la ban sua cua mot bai gold G-001..020, ky vong publish."""
    path = repo_root / "docs" / "functional-tests" / "gold-corrected-labels.csv"
    rows = _csv_rows(path)
    if len(rows) != 20:
        raise EvaluationContractError(
            f"gold-corrected-labels phai co exact 20 row, nhan {len(rows)}"
        )
    ids = tuple(row.get("sample_id") for row in rows)
    if ids != GOLD_CORRECTED_IDS:
        raise EvaluationContractError("gold-corrected-labels sai canonical ordered IDs")
    for row in rows:
        sample_id = row["sample_id"]
        if row.get("expected_label") != "publish":
            raise EvaluationContractError(f"{sample_id} corrected phai expected_label publish")
        if row.get("guideline_version") != GUIDELINE_VERSION:
            raise EvaluationContractError(f"{sample_id} sai guideline_version")
        if not row.get("parent_sample_id"):
            raise EvaluationContractError(f"{sample_id} thieu parent_sample_id")
        _validate_sha(f"{sample_id}.content_sha256 (manifest)", row.get("content_sha256"))
    return rows


def _clean_rows_corrected(repo_root: Path) -> list[dict]:
    """10 C: doi chieu clean_labels.csv (v1.3, co source_url) voi
    functional-clean-ai-review-v1.4.csv (v1.4, co content_sha256)."""
    legacy_path = repo_root / "docs" / "functional-tests" / "clean_labels.csv"
    review_path = repo_root / "docs" / "evidence" / "functional-clean-ai-review-v1.4.csv"
    legacy_rows = {row.get("sample_id"): row for row in _csv_rows(legacy_path)}
    review_rows = {row.get("sample_id"): row for row in _csv_rows(review_path)}
    if set(legacy_rows) != set(CLEAN_IDS) or set(review_rows) != set(CLEAN_IDS):
        raise EvaluationContractError(
            "clean C-001..010 khong khop giua clean_labels.csv va functional-clean-ai-review-v1.4.csv"
        )
    merged = []
    for sample_id in CLEAN_IDS:
        legacy = legacy_rows[sample_id]
        review = review_rows[sample_id]
        if legacy.get("expected_label") != review.get("expected_label"):
            raise EvaluationContractError(
                f"{sample_id} expected_label lech giua clean_labels va functional-clean-ai-review-v1.4"
            )
        if review.get("guideline_version") != GUIDELINE_VERSION:
            raise EvaluationContractError(f"{sample_id} sai guideline_version")
        _validate_sha(f"{sample_id}.content_sha256 (manifest)", review.get("content_sha256"))
        merged.append({
            "sample_id": sample_id,
            "source_url": legacy.get("source_url", ""),
            "expected_label": review["expected_label"],
            "content_sha256": review["content_sha256"],
        })
    return merged


def _criterion_coverage_rows(repo_root: Path) -> list[dict]:
    """11 CV, moi cai injected dung mot target_code tu mot parent corrected/clean."""
    path = repo_root / "docs" / "functional-tests" / "criterion-coverage-labels.csv"
    rows = _csv_rows(path)
    if len(rows) != 11:
        raise EvaluationContractError(
            f"criterion-coverage-labels phai co exact 11 row, nhan {len(rows)}"
        )
    ids = tuple(row.get("sample_id") for row in rows)
    if ids != COVERAGE_IDS:
        raise EvaluationContractError("criterion-coverage-labels sai canonical ordered IDs")
    for row in rows:
        sample_id = row["sample_id"]
        if row.get("expected_label") not in LABELS:
            raise EvaluationContractError(f"{sample_id} co expected_label khong hop le")
        if row.get("guideline_version") != GUIDELINE_VERSION:
            raise EvaluationContractError(f"{sample_id} sai guideline_version")
        if not row.get("target_code"):
            raise EvaluationContractError(f"{sample_id} thieu target_code")
        if not row.get("parent_sample_id"):
            raise EvaluationContractError(f"{sample_id} thieu parent_sample_id")
        _validate_sha(f"{sample_id}.content_sha256 (manifest)", row.get("content_sha256"))
    return rows


def load_dataset(kind: str, repo_root: Path) -> list[EvaluationSample]:
    """Doc exact e1/gold/corrected/coverage theo thu tu canonical."""
    kind = _validate_dataset_kind(kind)
    repo_root = Path(repo_root).resolve()

    if kind in ("e1", "gold"):
        rows = _labels_rows(repo_root)
        selected = rows[:10] if kind == "e1" else rows
        expected_ids = E1_IDS if kind == "e1" else GOLD_IDS
        if tuple(row["sample_id"] for row in selected) != expected_ids:
            raise EvaluationContractError(f"{kind} sai ordered sample IDs")
        raw_dir = repo_root / "docs" / "goldset" / "raw"
        samples = []
        for row in selected:
            sample_id = row["sample_id"]
            path = raw_dir / f"{sample_id}.txt"
            if not path.is_file():
                raise EvaluationContractError(f"thieu sample content: {sample_id}")
            samples.append(
                EvaluationSample(
                    sample_id=sample_id,
                    fields=_fields_from_file(path),
                    expected_label=row["label"],
                    split="e1" if kind == "e1" else row["split"],
                    source_url=row.get("source_url", ""),
                    content_sha256=_sha256_file(path),
                )
            )
        return samples

    if kind == "corrected":
        clean_dir = repo_root / "docs" / "functional-tests" / "clean"
        gold_corrected_dir = repo_root / "docs" / "functional-tests" / "gold-corrected"
        rows_with_dir = (
            [(row, clean_dir) for row in _clean_rows_corrected(repo_root)]
            + [(row, gold_corrected_dir) for row in _gold_corrected_rows(repo_root)]
        )
    else:  # coverage
        coverage_dir = repo_root / "docs" / "functional-tests" / "criterion-coverage"
        rows_with_dir = [(row, coverage_dir) for row in _criterion_coverage_rows(repo_root)]

    samples = []
    for row, raw_dir in rows_with_dir:
        sample_id = row["sample_id"]
        path = raw_dir / f"{sample_id}.txt"
        if not path.is_file():
            raise EvaluationContractError(f"thieu sample content: {sample_id}")
        actual_hash = _sha256_file(path)
        manifest_hash = row.get("content_sha256")
        if manifest_hash and actual_hash != manifest_hash:
            raise EvaluationContractError(
                f"{sample_id} content_sha256 lech manifest: file={actual_hash} manifest={manifest_hash}"
            )
        samples.append(
            EvaluationSample(
                sample_id=sample_id,
                fields=_fields_from_file(path),
                expected_label=row["expected_label"],
                split=kind,
                source_url=row.get("source_url", ""),
                content_sha256=actual_hash,
                parent_sample_id=row.get("parent_sample_id") or None,
                target_code=row.get("target_code") or None,
            )
        )
    return samples


def _git(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=repo_root, text=True, encoding="utf-8"
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise EvaluationContractError(f"khong doc duoc git {' '.join(args)}") from error


def _resolve_data_head(repo_root: Path, pinned: str | None) -> str:
    if pinned is None:
        return _validate_git_commit(
            "data_head",
            _git(
                repo_root,
                "log",
                "-1",
                "--format=%H",
                "--",
                "docs/goldset",
                "docs/functional-tests",
            ),
        )
    pinned = _validate_git_commit("data_head", pinned)
    _git(repo_root, "cat-file", "-e", f"{pinned}^{{commit}}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", pinned, "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise EvaluationContractError("pinned data_head khong la ancestor cua HEAD")
    snapshot = subprocess.run(
        [
            "git", "diff", "--quiet", pinned, "--",
            "docs/goldset", "docs/functional-tests",
        ],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if snapshot.returncode == 1:
        raise EvaluationContractError("data snapshot drift tu pinned data_head")
    if snapshot.returncode != 0:
        raise EvaluationContractError("khong verify duoc pinned data snapshot")
    return pinned


def _bundle_hash(repo_root: Path, relative_paths: tuple[str, ...]) -> str:
    artifacts = {
        relative: _sha256_file(repo_root / relative)
        for relative in relative_paths
    }
    return _canonical_sha256(artifacts)


def _model_name() -> str:
    # Lazy-import sau khi dataset/date/artifact da validate. Import module
    # chi de doc exact production MODEL, khong tao client va khong goi API.
    import ai_core

    model = ai_core.MODEL
    if not isinstance(model, str) or not model.strip():
        raise EvaluationContractError("ai_core.MODEL khong hop le")
    return model


def _validate_samples(samples: list[EvaluationSample]) -> list[str]:
    if not isinstance(samples, list) or not samples:
        raise EvaluationContractError("samples phai la list khong rong")
    ids = []
    for sample in samples:
        if not isinstance(sample, EvaluationSample):
            raise EvaluationContractError("sample sai EvaluationSample contract")
        if not sample.sample_id or sample.sample_id in ids:
            raise EvaluationContractError(f"duplicate sample_id: {sample.sample_id!r}")
        if not isinstance(sample.fields, dict):
            raise EvaluationContractError(f"{sample.sample_id}.fields phai la object")
        if sample.expected_label not in LABELS:
            raise EvaluationContractError(f"{sample.sample_id}.expected_label khong hop le")
        _validate_sha(f"{sample.sample_id}.content_sha256", sample.content_sha256)
        ids.append(sample.sample_id)
    return ids


def build_runtime_contract(
    repo_root: Path,
    dataset_kind: str,
    samples: list[EvaluationSample],
    assessment_as_of: str,
    output_path: Path,
    *,
    data_head: str | None = None,
) -> dict:
    """Khoa moi dimension co the lam hai run khong con so sanh duoc."""
    repo_root = Path(repo_root).resolve()
    dataset_kind = _validate_dataset_kind(dataset_kind)
    assessment_as_of = _validate_assessment_date(assessment_as_of)
    ordered_ids = _validate_samples(samples)
    output_path = Path(output_path).resolve()

    policy_path = repo_root / "multiagent" / "src" / "decision_policy.py"
    scoring_path = repo_root / "multiagent" / "config" / "scoring.yaml"
    safety_path = repo_root / "multiagent" / "src" / "kb" / "safety_rules.json"
    fact_kb_path = repo_root / "multiagent" / "src" / "kb" / "specs.json"
    brand_kb_path = repo_root / "multiagent" / "src" / "agents" / "brand_rules.json"
    guideline_path = repo_root / "docs" / "goldset" / "annotation-guideline.md"
    rubric_path = repo_root / "docs" / "rubrics.md"

    # Doc/validate tat ca artifact truoc khi lazy-import ai_core.
    hashes = {
        "policy_hash": _sha256_file(policy_path),
        "scoring_hash": _sha256_file(scoring_path),
        "safety_rules_hash": _sha256_file(safety_path),
        "fact_kb_hash": _sha256_file(fact_kb_path),
        "brand_kb_hash": _sha256_file(brand_kb_path),
        "guideline_hash": _sha256_file(guideline_path),
        "rubric_hash": _sha256_file(rubric_path),
    }
    prompt_version = _bundle_hash(
        repo_root,
        (
            "multiagent/src/agents/content_quality.py",
            "multiagent/src/agents/seo.py",
            "multiagent/src/agents/brand_voice.py",
            "multiagent/src/agents/compliance.py",
            "multiagent/src/agents/fact_check.py",
        ),
    )
    embedding_hash = _bundle_hash(
        repo_root,
        ("multiagent/src/embeddings.py", "multiagent/src/retrieval.py"),
    )
    dataset_manifest_hashes = {
        relative: _sha256_file(repo_root / relative)
        for relative in _DATASET_MANIFEST_PATHS[dataset_kind]
    }
    try:
        scoring = yaml.safe_load(scoring_path.read_text(encoding="utf-8"))
        weights = scoring["cam_nang:vi"]["weights"]
    except (OSError, KeyError, TypeError, yaml.YAMLError) as error:
        raise EvaluationContractError("khong doc duoc weights cam_nang:vi") from error
    if set(weights) != set(AGENT_ORDER) or any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or value <= 0
        for value in weights.values()
    ):
        raise EvaluationContractError("weights cam_nang:vi khong hop le")

    git_head = _git(repo_root, "rev-parse", "HEAD")
    data_head = _resolve_data_head(repo_root, data_head)
    _validate_git_commit("git_head", git_head)
    _validate_git_commit("data_head", data_head)

    release_tuple = {
        "dataset_kind": dataset_kind,
        "policy_version": POLICY_V2,
        "guideline_version": GUIDELINE_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "guideline_hash": hashes["guideline_hash"],
        "rubric_hash": hashes["rubric_hash"],
        "prompt_version": prompt_version,
        "model": _model_name(),
        "scoring_hash": hashes["scoring_hash"],
        "policy_hash": hashes["policy_hash"],
        "safety_rules_hash": hashes["safety_rules_hash"],
        "fact_kb_hash": hashes["fact_kb_hash"],
        "brand_kb_hash": hashes["brand_kb_hash"],
        "embedding_hash": embedding_hash,
        "embedding_provenance": {
            "model": "BAAI/bge-m3",
            "mode": "remote" if os.environ.get("EMBEDDING_SPACE_URL") else "local",
            "endpoint": os.environ.get("EMBEDDING_SPACE_URL") or None,
        },
        "weights": {name: float(weights[name]) for name in AGENT_ORDER},
        "dataset_manifest_hashes": dataset_manifest_hashes,
        "content_hashes_sha256": {
            sample.sample_id: sample.content_sha256 for sample in samples
        },
        "data_head": data_head,
        "git_head": git_head,
        "assessment_as_of": assessment_as_of,
        "output_path": str(output_path),
        "ordered_sample_ids": ordered_ids,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_kind": dataset_kind,
        "policy_version": POLICY_V2,
        "assessment_as_of": assessment_as_of,
        "output_path": str(output_path),
        "ordered_sample_ids": ordered_ids,
        "weights": {name: float(weights[name]) for name in AGENT_ORDER},
        "pricing_path": str(
            (repo_root / "multiagent" / "config" / "model_pricing.yaml").resolve()
        ),
        "release_tuple": release_tuple,
        "release_sha256": _canonical_sha256(release_tuple),
        "label_provenance": LABEL_PROVENANCE,
    }


def _validate_runtime_contract(contract: dict, output_path: Path | None = None) -> None:
    if not isinstance(contract, dict):
        raise EvaluationContractError("runtime_contract phai la object")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise EvaluationContractError("runtime contract sai schema_version")
    try:
        policy = require_policy_version(
            contract.get("policy_version"), allow_legacy_default=False
        )
    except PolicyContractError as error:
        raise EvaluationContractError(f"policy_version: {error}") from error
    if policy != POLICY_V2:
        raise EvaluationContractError("policy_version evaluator phai exact v2")
    _validate_dataset_kind(contract.get("dataset_kind"))
    _validate_assessment_date(contract.get("assessment_as_of"))

    release = contract.get("release_tuple")
    if not isinstance(release, dict):
        raise EvaluationContractError("thieu release_tuple")
    for field in RELEASE_FIELDS:
        if field not in release:
            raise EvaluationContractError(f"release tuple thieu {field}")
    if set(release) != set(RELEASE_FIELDS):
        extra = sorted(set(release) - set(RELEASE_FIELDS))
        raise EvaluationContractError(f"release tuple co field la: {extra}")
    if release["policy_version"] != policy:
        raise EvaluationContractError("release policy_version khong khop")
    if release["guideline_version"] != GUIDELINE_VERSION:
        raise EvaluationContractError("release guideline_version khong khop")
    if release["rubric_version"] != RUBRIC_VERSION:
        raise EvaluationContractError("release rubric_version khong khop")
    if release["dataset_kind"] != contract["dataset_kind"]:
        raise EvaluationContractError("release dataset_kind khong khop")
    if release["assessment_as_of"] != contract["assessment_as_of"]:
        raise EvaluationContractError("release assessment_as_of khong khop")
    if release["output_path"] != contract.get("output_path"):
        raise EvaluationContractError("release output_path khong khop")
    if release["ordered_sample_ids"] != contract.get("ordered_sample_ids"):
        raise EvaluationContractError("release ordered_sample_ids khong khop")
    if (
        not isinstance(release["ordered_sample_ids"], list)
        or not release["ordered_sample_ids"]
        or len(release["ordered_sample_ids"]) != len(set(release["ordered_sample_ids"]))
    ):
        raise EvaluationContractError("release ordered_sample_ids khong hop le")
    if output_path is not None and str(Path(output_path).resolve()) != contract.get("output_path"):
        raise EvaluationContractError("output path khong khop runtime contract")
    _validate_sha("release_sha256", contract.get("release_sha256"))
    if _canonical_sha256(release) != contract["release_sha256"]:
        raise EvaluationContractError("release_sha256 khong khop release tuple")
    for name in (
        "prompt_version", "guideline_hash", "rubric_hash", "scoring_hash",
        "policy_hash", "safety_rules_hash",
        "fact_kb_hash", "brand_kb_hash", "embedding_hash",
    ):
        _validate_sha(name, release[name])
    _validate_git_commit("data_head", release["data_head"])
    _validate_git_commit("git_head", release["git_head"])
    if not isinstance(release["model"], str) or not release["model"].strip():
        raise EvaluationContractError("release model khong hop le")
    manifests = release["dataset_manifest_hashes"]
    if not isinstance(manifests, dict) or not manifests:
        raise EvaluationContractError(
            "dataset_manifest_hashes phai la object khong rong"
        )
    for name, value in manifests.items():
        if not isinstance(name, str) or not name:
            raise EvaluationContractError("dataset manifest name khong hop le")
        _validate_sha(f"dataset manifest {name}", value)
    embedding = release["embedding_provenance"]
    if (
        not isinstance(embedding, dict)
        or embedding.get("model") != "BAAI/bge-m3"
        or embedding.get("mode") not in {"local", "remote"}
    ):
        raise EvaluationContractError("embedding_provenance khong hop le")
    content_hashes = release["content_hashes_sha256"]
    if not isinstance(content_hashes, dict):
        raise EvaluationContractError("content_hashes_sha256 phai la object")
    if list(content_hashes) != release["ordered_sample_ids"]:
        raise EvaluationContractError("content hashes khong theo ordered sample IDs")
    for sample_id, value in content_hashes.items():
        _validate_sha(f"content hash {sample_id}", value)
    weights = contract.get("weights")
    if not isinstance(weights, dict) or set(weights) != set(AGENT_ORDER):
        raise EvaluationContractError("runtime weights khong hop le")
    if release["weights"] != weights:
        raise EvaluationContractError("release weights khong khop runtime weights")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or value <= 0
        for value in weights.values()
    ):
        raise EvaluationContractError("runtime weights khong hop le")
    pricing_path = contract.get("pricing_path")
    if not isinstance(pricing_path, str) or not Path(pricing_path).is_file():
        raise EvaluationContractError("pricing_path khong hop le")


def _validate_sample_against_contract(
    sample: EvaluationSample, runtime_contract: dict
) -> None:
    _validate_samples([sample])
    ids = runtime_contract["ordered_sample_ids"]
    if sample.sample_id not in ids:
        raise EvaluationContractError(f"sample {sample.sample_id} khong nam trong release")
    expected_hash = runtime_contract["release_tuple"]["content_hashes_sha256"].get(
        sample.sample_id
    )
    if expected_hash != sample.content_sha256:
        raise EvaluationContractError(f"sample {sample.sample_id} content hash drift")


def _default_agent_runner(*, fields: dict, policy_version: str,
                          assessment_as_of: str) -> dict:
    if os.environ.get("VF_ALLOW_PAID_EVAL") != "1":
        raise EvaluationContractError(
            "VF_ALLOW_PAID_EVAL phai bang 1 truoc default paid agent runner"
        )
    # Chi den day moi duoc import production agent/provider path.
    from agents import brand_voice, compliance, content_quality, seo

    results = {}
    calls = (
        ("content_quality", lambda: content_quality.run(
            fields, policy_version=policy_version
        )),
        ("seo", lambda: seo.run(fields)),
        ("brand", lambda: brand_voice.run(fields)),
        ("compliance", lambda: compliance.run(
            fields, policy_version=policy_version
        )),
    )
    for name, call in calls:
        try:
            results[name] = call()
        except Exception:
            results[name] = None
    return results


def _diagnostic_score(agent_results: dict, weights: dict) -> float | None:
    if agent_results.get("compliance") is None:
        return None
    available = {}
    for agent in AGENT_ORDER:
        result = agent_results.get(agent)
        if result is None:
            continue
        score = result.get("score") if isinstance(result, dict) else None
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or not 0 <= float(score) <= 100
        ):
            raise EvaluationContractError(f"{agent}.score khong hop le")
        available[agent] = float(score)
    denominator = sum(weights[name] for name in available)
    if denominator <= 0:
        return None
    return sum(weights[name] * score for name, score in available.items()) / denominator


def _cost_payload(usage: list[dict], pricing_path: Path) -> dict:
    try:
        estimated = estimate_usage(usage, pricing_path)
    except ValueError as error:
        raise EvaluationContractError(f"usage/pricing khong hop le: {error}") from error
    return {
        "input_tokens": estimated.input_tokens,
        "output_tokens": estimated.output_tokens,
        "estimated_usd": (
            None if estimated.estimated_usd is None
            else format(estimated.estimated_usd, "f")
        ),
        "pricing_version": estimated.pricing_version,
        "effective_at": estimated.effective_at.isoformat(),
        "currency": estimated.currency,
        "source": estimated.source,
        "unknown_models": list(estimated.unknown_models),
    }


def run_policy_sample(
    sample: EvaluationSample,
    runtime_contract: dict,
    *,
    agent_runner: Callable[..., dict] | None = None,
) -> dict:
    """Chay mot sample; expected label chi duoc ghep SAU agent runner."""
    _validate_runtime_contract(runtime_contract)
    _validate_sample_against_contract(sample, runtime_contract)
    runner = agent_runner or _default_agent_runner
    usage = []
    started = time.perf_counter()

    if agent_runner is None:
        import ai_core

        ai_core.USAGE_LOG.clear()
        try:
            agent_results = runner(
                fields=dict(sample.fields),
                policy_version=runtime_contract["policy_version"],
                assessment_as_of=runtime_contract["assessment_as_of"],
            )
            usage = list(ai_core.USAGE_LOG)
        finally:
            ai_core.USAGE_LOG.clear()
    else:
        agent_results = runner(
            fields=dict(sample.fields),
            policy_version=runtime_contract["policy_version"],
            assessment_as_of=runtime_contract["assessment_as_of"],
        )

    if not isinstance(agent_results, dict):
        raise EvaluationContractError("agent_runner phai tra object")
    final_score = _diagnostic_score(agent_results, runtime_contract["weights"])
    try:
        evaluated = evaluate(
            sample.fields,
            agent_results,
            assessment_as_of=runtime_contract["assessment_as_of"],
            final_score=final_score,
        )
    except PolicyContractError as error:
        raise EvaluationContractError(
            f"sample {sample.sample_id} vi pham policy result contract: {error}"
        ) from error
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

    return {
        "sample_id": sample.sample_id,
        "expected_label": sample.expected_label,
        "split": sample.split,
        "source_url": sample.source_url,
        "content_sha256": sample.content_sha256,
        "parent_sample_id": sample.parent_sample_id,
        "target_code": sample.target_code,
        "decision": evaluated["decision"],
        "final_score": evaluated["final_score"],
        "decision_basis": evaluated["decision_basis"],
        "effective_findings": evaluated["effective_findings"],
        "advisory_findings": evaluated["advisory_findings"],
        "criteria": {
            name: (
                agent_results[name].get("criteria", [])
                if isinstance(agent_results.get(name), dict)
                else None
            )
            for name in AGENT_ORDER
        },
        "coverage": evaluated["coverage"],
        "drift": evaluated["drift"],
        "incomplete_assessment": evaluated["incomplete_assessment"],
        "missing_agents": evaluated["missing_agents"],
        "usage": usage,
        "cost": _cost_payload(
            usage, Path(runtime_contract["pricing_path"])
        ),
        "latency": {"milliseconds": elapsed_ms},
        "status": "complete",
        "release_tuple": deepcopy_json(runtime_contract["release_tuple"]),
    }


def deepcopy_json(value: Any) -> Any:
    """Copy JSON value va dong thoi bao dam raw co the serialize."""
    try:
        return json.loads(
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        )
    except (TypeError, ValueError) as error:
        raise EvaluationContractError("value khong JSON-serializable") from error


def _new_meta(runtime_contract: dict, repeats: int, is_fixture: bool) -> dict:
    # Giu ca cac field release phang (consumer/report doc truc tiep) va tuple
    # day du (resume so sanh nguyen khoi, khong bo sot dimension nao).
    return {
        **deepcopy_json(runtime_contract["release_tuple"]),
        "schema_version": SCHEMA_VERSION,
        "repeats": repeats,
        "release_tuple": deepcopy_json(runtime_contract["release_tuple"]),
        "release_sha256": runtime_contract["release_sha256"],
        "label_provenance": runtime_contract.get("label_provenance"),
        "is_fixture": is_fixture,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usage_events": 0,
    }


def _load_resume(
    output_path: Path,
    runtime_contract: dict,
    repeats: int,
    is_fixture: bool,
) -> dict:
    try:
        raw = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationContractError("raw resume khong doc/parse duoc") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("_meta"), dict):
        raise EvaluationContractError("raw resume thieu _meta")
    if not isinstance(raw.get("results"), list):
        raise EvaluationContractError("raw resume results phai la list")
    expected_meta = {
        **runtime_contract["release_tuple"],
        "schema_version": SCHEMA_VERSION,
        "repeats": repeats,
        "release_tuple": runtime_contract["release_tuple"],
        "release_sha256": runtime_contract["release_sha256"],
        "label_provenance": runtime_contract.get("label_provenance"),
        "is_fixture": is_fixture,
    }
    for field, expected in expected_meta.items():
        if raw["_meta"].get(field) != expected:
            raise EvaluationContractError(f"raw resume lech release field {field}")
    return raw


def _inventory_prefix(
    raw: dict,
    samples: list[EvaluationSample],
    repeats: int,
    runtime_contract: dict,
) -> list[tuple[str, int]]:
    expected = [
        (sample.sample_id, repeat)
        for sample in samples
        for repeat in range(1, repeats + 1)
    ]
    actual = []
    seen = set()
    for row in raw["results"]:
        if not isinstance(row, dict):
            raise EvaluationContractError("raw result phai la object")
        key = (row.get("sample_id"), row.get("repeat_index"))
        if key in seen:
            raise EvaluationContractError(f"duplicate sample/repeat: {key}")
        seen.add(key)
        actual.append(key)
        if row.get("release_tuple") != runtime_contract["release_tuple"]:
            raise EvaluationContractError(f"result {key} lech release tuple")
        if row.get("status") != "complete":
            raise EvaluationContractError(f"result {key} status khong complete")
    if actual != expected[:len(actual)]:
        raise EvaluationContractError("sample/repeat inventory co hole hoac sai thu tu")
    if len(actual) > len(expected):
        raise EvaluationContractError("sample/repeat inventory vuot contract")
    return expected


def _write_atomic(path: Path, raw: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(
                raw, handle, ensure_ascii=False, indent=2, allow_nan=False
            )
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def run_samples(
    samples: list[EvaluationSample],
    output_path: Path,
    runtime_contract: dict,
    *,
    repeats: int = 1,
    agent_runner: Callable[..., dict] | None = None,
    paid_authorization: dict | None = None,
) -> dict:
    """Chay/resume theo prefix, ghi atomic sau tung sample/repeat."""
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise EvaluationContractError("repeats phai la so nguyen duong")
    output_path = Path(output_path).resolve()
    _validate_runtime_contract(runtime_contract, output_path)
    ids = _validate_samples(samples)
    if ids != runtime_contract["ordered_sample_ids"]:
        raise EvaluationContractError("samples khong khop ordered sample IDs")
    if agent_runner is None:
        if (
            not isinstance(paid_authorization, dict)
            or paid_authorization.get("authorized") is not True
            or paid_authorization.get("is_fixture") is not False
            or paid_authorization.get("dataset_kind") != runtime_contract["dataset_kind"]
            or paid_authorization.get("runtime_release_sha256")
            != runtime_contract["release_sha256"]
        ):
            raise EvaluationContractError(
                "default provider path bat buoc co paid authorization dung runtime release"
            )
        token_hash = paid_authorization.get("confirmation_token_hash")
        if (
            not isinstance(token_hash, str)
            or len(token_hash) != 64
            or any(char not in "0123456789abcdef" for char in token_hash)
        ):
            raise EvaluationContractError("paid authorization token hash khong hop le")
        if os.environ.get("VF_ALLOW_PAID_EVAL") != "1":
            raise EvaluationContractError(
                "VF_ALLOW_PAID_EVAL phai bang 1 truoc default paid runner"
            )
    is_fixture = agent_runner is not None

    if output_path.exists():
        raw = _load_resume(output_path, runtime_contract, repeats, is_fixture)
    else:
        raw = {
            "_meta": _new_meta(runtime_contract, repeats, is_fixture),
            "results": [],
        }
    expected = _inventory_prefix(raw, samples, repeats, runtime_contract)
    completed = len(raw["results"])

    samples_by_id = {sample.sample_id: sample for sample in samples}
    for sample_id, repeat_index in expected[completed:]:
        row = run_policy_sample(
            samples_by_id[sample_id],
            runtime_contract,
            agent_runner=agent_runner,
        )
        row["repeat_index"] = repeat_index
        raw["results"].append(row)
        raw["_meta"]["usage_events"] += len(row["usage"])
        _write_atomic(output_path, raw)

    _inventory_prefix(raw, samples, repeats, runtime_contract)
    if len(raw["results"]) != len(expected):
        raise EvaluationContractError("sample/repeat inventory thieu ket qua")
    return raw


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate publish policy v2")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument(
        "--dataset", choices=("e1", "gold", "corrected", "coverage"), required=True
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--assessment-as-of", required=True)
    parser.add_argument("--confirmation-token")
    parser.add_argument(
        "--repo-root", default=str(Path(__file__).resolve().parents[2])
    )
    return parser


def cli(argv: list[str] | None = None) -> int:
    """Preflight $0 hoac authorized paid run; khong co nhanh --force."""
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    output_path = Path(args.output).resolve()

    # Verify frozen manifest TRUOC build_runtime_contract lazy-import ai_core.
    from policy_release import (
        authorize_paid_run,
        build_preflight,
        verify,
    )

    manifest = verify(Path(args.manifest), repo_root)
    manifest.pop("verified", None)
    samples = load_dataset(args.dataset, repo_root)
    runtime_contract = build_runtime_contract(
        repo_root,
        args.dataset,
        samples,
        args.assessment_as_of,
        output_path,
        data_head=manifest["data_head"],
    )
    repeats = 5 if args.dataset == "e1" else 1
    if args.preflight:
        result = build_preflight(
            manifest,
            runtime_contract,
            repeats=repeats,
            repo_root=repo_root,
        )
    else:
        if not args.confirmation_token:
            raise EvaluationContractError(
                "--run bat buoc co --confirmation-token"
            )
        authorization = authorize_paid_run(
            manifest,
            args.dataset,
            output_path,
            args.assessment_as_of,
            args.confirmation_token,
            runtime_contract=runtime_contract,
        )
        raw = run_samples(
            samples,
            output_path,
            runtime_contract,
            repeats=repeats,
            paid_authorization=authorization,
        )
        result = {
            "dataset_kind": args.dataset,
            "result_count": len(raw["results"]),
            "output_path": str(output_path),
            "release_sha256": manifest["release_sha256"],
            "is_fixture": raw["_meta"]["is_fixture"],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
