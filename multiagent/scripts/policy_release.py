"""Freeze/verify release va khoa paid run cho publish policy v2.

Manifest khong nam trong tap artifact tu bam cua chinh no. ``freeze`` ghi
``release_source_commit=HEAD`` cua toan bo protected source/data; commit chi
chua manifest sau do khong tao self-hash loop. Khong co ``--force``.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from decision_policy import POLICY_V2, PolicyContractError, require_policy_version  # noqa: E402
from review_platform.pricing import estimate_usage  # noqa: E402


SCHEMA_VERSION = 1
PROTOCOL_REL = "docs/evidence/corrected-publish-coverage-v1-protocol.md"
MANIFEST_REL = "docs/evidence/publish-policy-v2-manifest.json"
PAID_DATASETS = ("e1", "gold", "corrected", "coverage", "smoke")
MEASURED_DATASETS = ("e1", "gold", "corrected", "coverage")
INDEPENDENT_LABEL_STATUS = "not_demonstrated"

_STATIC_PROTECTED = (
    PROTOCOL_REL,
    "docs/evaluation-plan.md",
    "docs/goldset/annotation-guideline.md",
    "docs/goldset/labels-ai-v1.4.csv",
    "docs/goldset/labels.csv",
    "docs/goldset/sources.md",
    "docs/rubrics.md",
    "docs/functional-tests/gold-corrected-labels.csv",
    "docs/functional-tests/criterion-coverage-labels.csv",
    "multiagent/config/model_pricing.yaml",
    "multiagent/config/scoring.yaml",
    "multiagent/scripts/eval_policy_v2.py",
    "multiagent/scripts/eval_policy_v2_metrics.py",
    "multiagent/scripts/functional_dataset_v2.py",
    "multiagent/scripts/policy_release.py",
    "multiagent/src/ai_core.py",
    "multiagent/src/decision_policy.py",
    "multiagent/src/embeddings.py",
    "multiagent/src/graph.py",
    "multiagent/src/retrieval.py",
    "multiagent/src/scoring.py",
    "multiagent/src/state.py",
    "multiagent/src/agents/brand_rules.json",
    "multiagent/src/agents/brand_voice.py",
    "multiagent/src/agents/compliance.py",
    "multiagent/src/agents/content_quality.py",
    "multiagent/src/agents/fact_check.py",
    "multiagent/src/agents/seo.py",
    "multiagent/src/kb/safety_rules.json",
    "multiagent/src/kb/specs.json",
)
_DATA_GLOBS = (
    ("docs/goldset/raw", "*.txt", 33),
    ("docs/functional-tests/clean", "*.txt", 10),
    ("docs/functional-tests/gold-corrected", "*.txt", 20),
    ("docs/functional-tests/criterion-coverage", "*.txt", 11),
)
_GOLD_IDS = (
    *(f"G-{index:03d}" for index in range(1, 21)),
    "P-001a", "P-001b", "P-002a", "P-003a", "P-004a", "P-004b",
    "P-005a", "P-006a", "P-007a", "P-007b", "P-008a", "P-009a",
    "P-010a",
)


class ReleaseContractError(ValueError):
    """Manifest/artifact/token khong du de mo paid gate."""


def _canonical_sha256(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ReleaseContractError("value khong JSON-canonical duoc") from error
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ReleaseContractError(f"khong doc duoc artifact: {path}") from error


def _validate_sha(name: str, value: Any, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ReleaseContractError(f"{name} khong phai hash {length} ky tu")
    return value


def _git(repo_root: Path, *args: str, check: bool = True) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise ReleaseContractError("khong chay duoc git") from error
    if check and completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise ReleaseContractError(f"git {' '.join(args)} that bai: {message}")
    return completed.stdout.strip()


def protected_paths(repo_root: Path) -> tuple[str, ...]:
    """Exact source/data paths duoc freeze; manifest co y bi loai khoi tap."""
    repo_root = Path(repo_root).resolve()
    paths = list(_STATIC_PROTECTED)
    for directory, pattern, expected_count in _DATA_GLOBS:
        found = sorted(
            path.relative_to(repo_root).as_posix()
            for path in (repo_root / directory).glob(pattern)
            if path.is_file()
        )
        if len(found) != expected_count:
            raise ReleaseContractError(
                f"protected dataset {directory} phai co {expected_count} file, "
                f"nhan {len(found)}"
            )
        paths.extend(found)
    if MANIFEST_REL in paths:
        raise ReleaseContractError("manifest khong duoc tu bam chinh no")
    missing = [relative for relative in paths if not (repo_root / relative).is_file()]
    if missing:
        raise ReleaseContractError(f"thieu protected artifact: {missing[0]}")
    if len(paths) != len(set(paths)):
        raise ReleaseContractError("protected artifact path bi trung")
    return tuple(sorted(paths))


def _read_manifest(path: Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseContractError(f"manifest khong doc/parse duoc: {path}") from error
    if not isinstance(value, dict):
        raise ReleaseContractError("manifest phai la object")
    return value


def _write_manifest(path: Path, manifest: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(
                manifest, handle, ensure_ascii=False, indent=2, allow_nan=False
            )
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _validate_policy(manifest: dict) -> None:
    try:
        policy = require_policy_version(
            manifest.get("policy_version"), allow_legacy_default=False
        )
    except PolicyContractError as error:
        raise ReleaseContractError(f"policy_version: {error}") from error
    if policy != POLICY_V2:
        raise ReleaseContractError("policy_version release phai exact v2")


def _validate_skeleton(manifest: dict) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseContractError("schema_version khong hop le")
    _validate_policy(manifest)
    if "data_head" not in manifest:
        raise ReleaseContractError("manifest thieu data_head")
    _validate_sha("data_head", manifest["data_head"], 40)
    if manifest.get("independent_label_reliability") != INDEPENDENT_LABEL_STATUS:
        raise ReleaseContractError(
            "independent_label_reliability phai la not_demonstrated"
        )
    paid = manifest.get("paid_runs")
    if not isinstance(paid, dict) or set(paid) != set(PAID_DATASETS):
        raise ReleaseContractError("paid_runs phai co exact nam gate")
    if not isinstance(manifest.get("approval"), dict):
        raise ReleaseContractError("manifest thieu approval")


def _artifacts(repo_root: Path) -> dict[str, str]:
    return {
        relative: _sha256_file(repo_root / relative)
        for relative in protected_paths(repo_root)
    }


def _csv_ids(path: Path, expected_count: int) -> list[str]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            ids = [row.get("sample_id", "") for row in csv.DictReader(handle)]
    except OSError as error:
        raise ReleaseContractError(f"khong doc duoc dataset manifest: {path}") from error
    if len(ids) != expected_count or len(ids) != len(set(ids)) or not all(ids):
        raise ReleaseContractError(f"dataset manifest {path.name} sai inventory")
    return ids


def _dataset_registry(repo_root: Path, artifacts: dict) -> dict:
    e1_ids = list(_GOLD_IDS[:10])
    gold_ids = list(_GOLD_IDS)
    corrected_ids = _csv_ids(
        repo_root / "docs/functional-tests/gold-corrected-labels.csv", 20
    )
    coverage_ids = _csv_ids(
        repo_root / "docs/functional-tests/criterion-coverage-labels.csv", 11
    )

    def entry(ids: list[str], directory: str) -> dict:
        hashes = {}
        for sample_id in ids:
            relative = f"{directory}/{sample_id}.txt"
            if relative not in artifacts:
                raise ReleaseContractError(f"dataset thieu artifact {relative}")
            hashes[sample_id] = artifacts[relative]
        return {"ordered_ids": ids, "content_hashes_sha256": hashes}

    return {
        "e1": entry(e1_ids, "docs/goldset/raw"),
        "gold": entry(gold_ids, "docs/goldset/raw"),
        "corrected": entry(
            corrected_ids, "docs/functional-tests/gold-corrected"
        ),
        "coverage": entry(
            coverage_ids, "docs/functional-tests/criterion-coverage"
        ),
        "smoke": {"ordered_ids": [], "content_hashes_sha256": {}},
    }


def _validate_data_snapshot(repo_root: Path, data_head: str) -> str:
    """Data HEAD la checkpoint snapshot, khong phai last-touch commit."""
    data_head = _validate_sha("data_head", data_head, 40)
    _git(repo_root, "cat-file", "-e", f"{data_head}^{{commit}}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", data_head, "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ReleaseContractError("data_head khong la ancestor cua HEAD")
    snapshot = subprocess.run(
        [
            "git", "diff", "--quiet", data_head, "--",
            "docs/goldset", "docs/functional-tests",
        ],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if snapshot.returncode == 1:
        raise ReleaseContractError("data snapshot drift tu data_head")
    if snapshot.returncode != 0:
        raise ReleaseContractError("khong verify duoc data snapshot")
    return data_head


def _protocol_commit(repo_root: Path) -> str:
    value = _git(repo_root, "log", "-1", "--format=%H", "--", PROTOCOL_REL)
    return _validate_sha("protocol_commit", value, 40)


def _common_release(manifest: dict) -> dict:
    return {
        "policy_version": manifest["policy_version"],
        "data_head": manifest["data_head"],
        "release_source_commit": manifest["release_source_commit"],
        "protocol_commit": manifest["protocol_commit"],
        "model": manifest["model"],
        "artifacts": manifest["artifacts"],
        "datasets": manifest["datasets"],
    }


def freeze(manifest_path: Path, repo_root: Path) -> dict:
    """Freeze tren clean protected HEAD; khong sua artifact/source nao."""
    repo_root = Path(repo_root).resolve()
    manifest_path = Path(manifest_path).resolve()
    manifest = _read_manifest(manifest_path)
    _validate_skeleton(manifest)
    paths = protected_paths(repo_root)
    dirty = _git(repo_root, "status", "--porcelain", "--", *paths)
    if dirty:
        raise ReleaseContractError(f"dirty protected paths:\n{dirty}")
    _validate_data_snapshot(repo_root, manifest["data_head"])
    head = _validate_sha("release_source_commit", _git(repo_root, "rev-parse", "HEAD"), 40)
    artifacts = _artifacts(repo_root)
    protocol_commit = _protocol_commit(repo_root)

    # Lazy-import chi de doc exact production model; khong tao provider client.
    import ai_core

    frozen = deepcopy_json(manifest)
    frozen.update({
        "release_source_commit": head,
        "protocol_commit": protocol_commit,
        "policy_hash": artifacts["multiagent/src/decision_policy.py"],
        "protocol_hash": artifacts[PROTOCOL_REL],
        "model": ai_core.MODEL,
        "artifacts": artifacts,
        "datasets": _dataset_registry(repo_root, artifacts),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    })
    frozen["release_tuple"] = _common_release(frozen)
    frozen["release_sha256"] = _canonical_sha256(frozen["release_tuple"])
    _write_manifest(manifest_path, frozen)
    return frozen


def deepcopy_json(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ReleaseContractError("manifest value khong JSON duoc") from error


def _require_frozen_fields(manifest: dict) -> None:
    for field in (
        "data_head", "release_source_commit", "protocol_commit",
        "policy_hash", "protocol_hash", "model", "artifacts", "datasets",
        "release_tuple", "release_sha256",
    ):
        if field not in manifest or manifest[field] in (None, ""):
            raise ReleaseContractError(f"manifest thieu {field}")
    _validate_sha("release_source_commit", manifest["release_source_commit"], 40)
    _validate_sha("protocol_commit", manifest["protocol_commit"], 40)
    _validate_sha("policy_hash", manifest["policy_hash"])
    _validate_sha("protocol_hash", manifest["protocol_hash"])
    _validate_sha("release_sha256", manifest["release_sha256"])


def _validate_frozen_in_memory(manifest: dict) -> None:
    _validate_skeleton(manifest)
    _require_frozen_fields(manifest)
    if manifest["policy_hash"] != manifest["artifacts"].get(
        "multiagent/src/decision_policy.py"
    ):
        raise ReleaseContractError("policy_hash khong khop artifacts")
    if manifest["protocol_hash"] != manifest["artifacts"].get(PROTOCOL_REL):
        raise ReleaseContractError("protocol_hash khong khop artifacts")
    if manifest["release_tuple"] != _common_release(manifest):
        raise ReleaseContractError("release_tuple khong khop manifest")
    if _canonical_sha256(manifest["release_tuple"]) != manifest["release_sha256"]:
        raise ReleaseContractError("release_sha256 khong khop release_tuple")
    datasets = manifest["datasets"]
    if not isinstance(datasets, dict) or set(datasets) != set(PAID_DATASETS):
        raise ReleaseContractError("datasets registry khong hop le")
    for kind, entry in datasets.items():
        if not isinstance(entry, dict):
            raise ReleaseContractError(f"datasets.{kind} phai la object")
        ids = entry.get("ordered_ids")
        hashes = entry.get("content_hashes_sha256")
        if not isinstance(ids, list) or len(ids) != len(set(ids)):
            raise ReleaseContractError(f"datasets.{kind}.ordered_ids khong hop le")
        if not isinstance(hashes, dict) or list(hashes) != ids:
            raise ReleaseContractError(f"datasets.{kind}.content hashes khong khop")
        for sample_id, value in hashes.items():
            _validate_sha(f"datasets.{kind}.{sample_id}", value)


def verify(manifest_path: Path, repo_root: Path) -> dict:
    """Verify schema, ancestry, exact artifacts va dataset registry."""
    repo_root = Path(repo_root).resolve()
    manifest = _read_manifest(Path(manifest_path))
    _validate_frozen_in_memory(manifest)
    head = _validate_sha("HEAD", _git(repo_root, "rev-parse", "HEAD"), 40)
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor",
         manifest["release_source_commit"], head],
        cwd=repo_root, capture_output=True, check=False,
    )
    if ancestor.returncode != 0:
        raise ReleaseContractError("release_source_commit khong la ancestor cua HEAD")
    protocol_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor",
         manifest["protocol_commit"], manifest["release_source_commit"]],
        cwd=repo_root, capture_output=True, check=False,
    )
    if protocol_ancestor.returncode != 0:
        raise ReleaseContractError(
            "protocol_commit phai la ancestor cua release_source_commit"
        )
    expected_paths = protected_paths(repo_root)
    if set(manifest["artifacts"]) != set(expected_paths):
        raise ReleaseContractError("artifact inventory mismatch")
    for relative in expected_paths:
        actual = _sha256_file(repo_root / relative)
        if manifest["artifacts"].get(relative) != actual:
            raise ReleaseContractError(f"artifact drift: {relative}")
    if _dataset_registry(repo_root, manifest["artifacts"]) != manifest["datasets"]:
        raise ReleaseContractError("dataset registry drift")
    _validate_data_snapshot(repo_root, manifest["data_head"])
    return {**deepcopy_json(manifest), "verified": True}


def confirmation_token(
    *,
    manifest: dict,
    dataset_kind: str,
    ordered_ids: list[str],
    assessment_as_of: str,
    output_path: Path,
    runtime_contract: dict | None = None,
) -> str:
    _validate_frozen_in_memory(manifest)
    if dataset_kind not in PAID_DATASETS:
        raise ReleaseContractError(f"unknown paid dataset: {dataset_kind}")
    expected_ids = manifest["datasets"][dataset_kind]["ordered_ids"]
    if ordered_ids != expected_ids:
        raise ReleaseContractError("ordered IDs khong khop frozen dataset")
    try:
        assessment = datetime.strptime(assessment_as_of, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError) as error:
        raise ReleaseContractError("assessment_as_of phai la YYYY-MM-DD") from error
    payload = {
        "schema_version": SCHEMA_VERSION,
        "dataset_kind": dataset_kind,
        "ordered_ids": ordered_ids,
        "content_hashes_sha256": manifest["datasets"][dataset_kind][
            "content_hashes_sha256"
        ],
        "release_tuple": manifest["release_tuple"],
        "release_sha256": manifest["release_sha256"],
        "runtime_release_sha256": (
            manifest["release_sha256"]
            if runtime_contract is None
            else runtime_contract.get("release_sha256")
        ),
        "assessment_as_of": assessment,
        "output_path": str(Path(output_path).resolve()),
    }
    return _canonical_sha256(payload)


def authorize_paid_run(
    manifest: dict,
    dataset_kind: str,
    output_path: Path,
    assessment_as_of: str,
    confirmation: str,
    runtime_contract: dict | None = None,
) -> dict:
    # Policy la dimension dau tien: version la dung truoc moi import/call.
    _validate_policy(manifest)
    _validate_frozen_in_memory(manifest)
    if dataset_kind not in PAID_DATASETS:
        raise ReleaseContractError(f"unknown paid dataset: {dataset_kind}")
    expected = confirmation_token(
        manifest=manifest,
        dataset_kind=dataset_kind,
        ordered_ids=manifest["datasets"][dataset_kind]["ordered_ids"],
        assessment_as_of=assessment_as_of,
        output_path=output_path,
        runtime_contract=runtime_contract,
    )
    if not isinstance(confirmation, str) or not hmac.compare_digest(expected, confirmation):
        raise ReleaseContractError("confirmation token mismatch")
    if os.environ.get("VF_ALLOW_PAID_EVAL") != "1":
        raise ReleaseContractError("VF_ALLOW_PAID_EVAL phai bang 1")
    return {
        "authorized": True,
        "is_fixture": False,
        "dataset_kind": dataset_kind,
        "release_sha256": manifest["release_sha256"],
        "runtime_release_sha256": (
            manifest["release_sha256"]
            if runtime_contract is None
            else runtime_contract.get("release_sha256")
        ),
        "confirmation_token_hash": hashlib.sha256(
            confirmation.encode("utf-8")
        ).hexdigest(),
    }


def build_preflight(
    manifest: dict,
    runtime_contract: dict,
    *,
    repeats: int,
    repo_root: Path,
) -> dict:
    _validate_frozen_in_memory(manifest)
    dataset_kind = runtime_contract.get("dataset_kind")
    ids = runtime_contract.get("ordered_sample_ids")
    if dataset_kind not in ("e1", "gold"):
        raise ReleaseContractError("core preflight chi ho tro e1|gold")
    if ids != manifest["datasets"][dataset_kind]["ordered_ids"]:
        raise ReleaseContractError("runtime ordered IDs khong khop manifest")
    if runtime_contract.get("policy_version") != manifest["policy_version"]:
        raise ReleaseContractError("runtime policy khong khop manifest")
    runtime_release = runtime_contract.get("release_tuple") or {}
    if runtime_release.get("data_head") != manifest["data_head"]:
        raise ReleaseContractError("runtime data_head khong khop manifest")
    if runtime_release.get("model") != manifest["model"]:
        raise ReleaseContractError("runtime model khong khop manifest")
    if runtime_release.get("policy_hash") != manifest["policy_hash"]:
        raise ReleaseContractError("runtime policy_hash khong khop manifest")
    if (
        runtime_release.get("content_hashes_sha256")
        != manifest["datasets"][dataset_kind]["content_hashes_sha256"]
    ):
        raise ReleaseContractError("runtime content hashes khong khop manifest")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ReleaseContractError("repeats khong hop le")
    max_calls = len(ids) * repeats * 8
    max_input = max_calls * 12_000
    max_output = max_calls * 4_096
    pricing_path = Path(repo_root) / "multiagent/config/model_pricing.yaml"
    estimate = estimate_usage(
        [{
            "model": manifest["model"],
            "input_tokens": max_input,
            "output_tokens": max_output,
        }],
        pricing_path,
    )
    token = confirmation_token(
        manifest=manifest,
        dataset_kind=dataset_kind,
        ordered_ids=ids,
        assessment_as_of=runtime_contract["assessment_as_of"],
        output_path=Path(runtime_contract["output_path"]),
        runtime_contract=runtime_contract,
    )
    return {
        "schema_version": 1,
        "kind": "preflight_only_not_experiment_result",
        "dataset_kind": dataset_kind,
        "sample_count": len(ids),
        "repeats": repeats,
        "usage_events": 0,
        "estimated_max_calls": max_calls,
        "estimated_max_input_tokens": max_input,
        "estimated_max_output_tokens": max_output,
        "estimated_max_cost_usd": (
            None if estimate.estimated_usd is None
            else format(estimate.estimated_usd, "f")
        ),
        "pricing_version": estimate.pricing_version,
        "pricing_effective_at": estimate.effective_at.isoformat(),
        "pricing_source": estimate.source,
        "confirmation_token": token,
        "release_sha256": manifest["release_sha256"],
        "runtime_release_sha256": runtime_contract["release_sha256"],
        "assessment_as_of": runtime_contract["assessment_as_of"],
        "output_path": runtime_contract["output_path"],
    }


def _reference(path: Path) -> dict:
    path = Path(path).resolve()
    return {"path": str(path), "sha256": _sha256_file(path)}


def _verified_json(reference: dict) -> dict:
    if not isinstance(reference, dict):
        raise ReleaseContractError("evidence reference phai la object")
    path = Path(reference.get("path", ""))
    if _sha256_file(path) != reference.get("sha256"):
        raise ReleaseContractError(f"evidence hash mismatch: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseContractError(f"evidence JSON khong hop le: {path}") from error
    if not isinstance(value, dict):
        raise ReleaseContractError(f"evidence phai la object: {path}")
    return value


def record_preflight(
    manifest_path: Path, repo_root: Path, dataset_kind: str, preflight_path: Path
) -> dict:
    manifest = verify(manifest_path, repo_root)
    manifest.pop("verified", None)
    if dataset_kind not in PAID_DATASETS:
        raise ReleaseContractError(f"unknown paid dataset: {dataset_kind}")
    reference = _reference(preflight_path)
    payload = _verified_json(reference)
    if (
        payload.get("kind") != "preflight_only_not_experiment_result"
        or payload.get("dataset_kind") != dataset_kind
        or payload.get("usage_events") != 0
        or payload.get("release_sha256") != manifest["release_sha256"]
    ):
        raise ReleaseContractError("preflight dataset/usage khong hop le")
    token = payload.get("confirmation_token")
    _validate_sha("confirmation_token", token)
    runtime_release_sha = _validate_sha(
        "runtime_release_sha256", payload.get("runtime_release_sha256")
    )
    expected_token = confirmation_token(
        manifest=manifest,
        dataset_kind=dataset_kind,
        ordered_ids=manifest["datasets"][dataset_kind]["ordered_ids"],
        assessment_as_of=payload.get("assessment_as_of"),
        output_path=Path(payload.get("output_path", "")),
        runtime_contract={"release_sha256": runtime_release_sha},
    )
    if not hmac.compare_digest(token, expected_token):
        raise ReleaseContractError("confirmation token mismatch")
    manifest["paid_runs"][dataset_kind] = {
        "status": "preflighted",
        "preflight": reference,
        "runtime_release_sha256": runtime_release_sha,
        "confirmation_token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
    }
    _write_manifest(manifest_path, manifest)
    return manifest


def _validate_core_raw(
    manifest: dict,
    dataset_kind: str,
    raw: dict,
    raw_path: Path,
) -> None:
    meta = raw.get("_meta")
    if not isinstance(meta, dict):
        raise ReleaseContractError("raw thieu _meta")
    if meta.get("is_fixture") is not False:
        raise ReleaseContractError("fixture raw khong duoc record measured")
    if meta.get("dataset_kind") != dataset_kind:
        raise ReleaseContractError("raw dataset_kind khong khop")

    expected_ids = manifest["datasets"][dataset_kind]["ordered_ids"]
    if meta.get("ordered_sample_ids") != expected_ids:
        raise ReleaseContractError("raw ordered sample IDs khong khop manifest")
    expected_repeats = 5 if dataset_kind == "e1" else 1
    if meta.get("repeats") != expected_repeats:
        raise ReleaseContractError("raw repeats khong khop protocol")

    release = meta.get("release_tuple")
    if not isinstance(release, dict):
        raise ReleaseContractError("raw thieu release_tuple")
    release_sha = _validate_sha("raw release_sha256", meta.get("release_sha256"))
    if _canonical_sha256(release) != release_sha:
        raise ReleaseContractError("raw release_sha256 khong khop release_tuple")
    expected_release = {
        "dataset_kind": dataset_kind,
        "policy_version": manifest["policy_version"],
        "model": manifest["model"],
        "data_head": manifest["data_head"],
        "policy_hash": manifest["policy_hash"],
        "content_hashes_sha256": manifest["datasets"][dataset_kind][
            "content_hashes_sha256"
        ],
        "ordered_sample_ids": expected_ids,
    }
    for field, expected in expected_release.items():
        if release.get(field) != expected:
            raise ReleaseContractError(f"raw release field {field} khong khop")
    if Path(release.get("output_path", "")).resolve() != Path(raw_path).resolve():
        raise ReleaseContractError("raw release output_path khong khop file")

    results = raw.get("results")
    if not isinstance(results, list):
        raise ReleaseContractError("raw results phai la list")
    expected_inventory = [
        (sample_id, repeat)
        for sample_id in expected_ids
        for repeat in range(1, expected_repeats + 1)
    ]
    actual_inventory = []
    for row in results:
        if not isinstance(row, dict):
            raise ReleaseContractError("raw result phai la object")
        actual_inventory.append((row.get("sample_id"), row.get("repeat_index")))
        if row.get("status") != "complete":
            raise ReleaseContractError("raw result status khong complete")
        if row.get("release_tuple") != release:
            raise ReleaseContractError("raw result release_tuple khong khop")
    if actual_inventory != expected_inventory:
        raise ReleaseContractError("raw sample/repeat inventory khong khop")


def record_result(
    manifest_path: Path,
    repo_root: Path,
    dataset_kind: str,
    *,
    raw_path: Path | None,
    report_path: Path,
) -> dict:
    manifest = verify(manifest_path, repo_root)
    manifest.pop("verified", None)
    if dataset_kind not in MEASURED_DATASETS:
        raise ReleaseContractError(f"dataset khong co measured result: {dataset_kind}")
    if dataset_kind in {"e1", "gold"} and raw_path is None:
        raise ReleaseContractError(f"{dataset_kind} bat buoc co raw_path")
    raw_reference = _reference(raw_path) if raw_path is not None else None
    report_reference = _reference(report_path)
    if raw_reference is not None:
        raw = _verified_json(raw_reference)
        _validate_core_raw(manifest, dataset_kind, raw, Path(raw_path))
    _verified_json(report_reference)
    prior = manifest["paid_runs"].get(dataset_kind)
    manifest["paid_runs"][dataset_kind] = {
        "status": "measured",
        "raw": raw_reference,
        "report": report_reference,
    }
    if isinstance(prior, dict) and prior.get("status") == "preflighted":
        for field in (
            "preflight", "runtime_release_sha256", "confirmation_token_hash"
        ):
            manifest["paid_runs"][dataset_kind][field] = prior.get(field)
        if (
            raw_reference is not None
            and raw["_meta"]["release_sha256"]
            != prior.get("runtime_release_sha256")
        ):
            raise ReleaseContractError("raw runtime release lech preflight")
    _write_manifest(manifest_path, manifest)
    return manifest


def _drift_count(raw: dict) -> int:
    rows = raw.get("results", [])
    if not isinstance(rows, list):
        raise ReleaseContractError("raw results khong hop le")
    return sum(
        len(row.get("drift", []))
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("drift", []), list)
    )


def approve(manifest_path: Path, repo_root: Path) -> dict:
    """Recompute gate tu evidence da bam hash; khong tin paid_runs.status."""
    manifest = verify(manifest_path, repo_root)
    manifest.pop("verified", None)
    for kind in MEASURED_DATASETS:
        entry = manifest["paid_runs"].get(kind)
        if not isinstance(entry, dict):
            raise ReleaseContractError(f"thieu measured evidence {kind}")

    from eval_policy_v2_metrics import gold_metrics, stability_metrics

    e1_raw = _verified_json(manifest["paid_runs"]["e1"].get("raw"))
    gold_raw = _verified_json(manifest["paid_runs"]["gold"].get("raw"))
    corrected = _verified_json(manifest["paid_runs"]["corrected"].get("report"))
    coverage = _verified_json(manifest["paid_runs"]["coverage"].get("report"))
    e1 = stability_metrics(e1_raw)
    gold = gold_metrics(gold_raw)

    gates = {
        "e1_decision_consistency": e1["decision_consistency"] >= 0.90,
        "gold_kappa": gold["kappa"] is not None and gold["kappa"] >= 0.60,
        "gold_rejected_recall": (
            gold["recall"]["rejected"] is not None
            and gold["recall"]["rejected"] >= 0.80
        ),
        "gold_needs_revision_recall": (
            gold["recall"]["needs_revision"] is not None
            and gold["recall"]["needs_revision"] >= 0.80
        ),
        "gold_false_publish": (
            gold["false_publish_count"] == 0
            and gold["false_publish_denominator"] == 33
        ),
        "corrected_publish": (
            corrected.get("corrected_publish_count") == 30
            and corrected.get("corrected_total") == 30
        ),
        "paired_recovery": (
            corrected.get("paired_recovery_count") == 20
            and corrected.get("paired_recovery_total") == 20
        ),
        "coverage_target_decision_parent": (
            coverage.get("target_decision_parent_pass_count") == 11
            and coverage.get("coverage_total") == 11
        ),
        "coverage_failure": coverage.get("failure_count") == 0,
        "drift": (
            corrected.get("drift_count") == 0
            and coverage.get("drift_count") == 0
            and _drift_count(e1_raw) == 0
            and _drift_count(gold_raw) == 0
        ),
    }
    level_b = "pass" if all(gates.values()) else "fail"
    manifest["approval"] = {
        "measured_complete": True,
        "level_b": level_b,
        "technical_gates": gates,
        "independent_label_reliability": INDEPENDENT_LABEL_STATUS,
        # Limited pilot can chi duoc mo o smoke gate rieng co nguoi duyet.
        "approved_for_limited_pilot": False,
        "recomputed_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest["independent_label_reliability"] = INDEPENDENT_LABEL_STATUS
    _write_manifest(manifest_path, manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish policy v2 release guard")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("verify", "freeze", "approve"):
        current = sub.add_parser(command)
        current.add_argument("--manifest", required=True)
        current.add_argument("--repo-root", required=True)
    preflight = sub.add_parser("record-preflight")
    preflight.add_argument("--manifest", required=True)
    preflight.add_argument("--repo-root", required=True)
    preflight.add_argument("--dataset", choices=PAID_DATASETS, required=True)
    preflight.add_argument("--path", required=True)
    result = sub.add_parser("record-result")
    result.add_argument("--manifest", required=True)
    result.add_argument("--repo-root", required=True)
    result.add_argument("--dataset", choices=MEASURED_DATASETS, required=True)
    result.add_argument("--raw")
    result.add_argument("--report", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = Path(args.manifest)
    repo = Path(args.repo_root)
    if args.command == "verify":
        result = verify(manifest, repo)
    elif args.command == "freeze":
        result = freeze(manifest, repo)
    elif args.command == "record-preflight":
        result = record_preflight(manifest, repo, args.dataset, Path(args.path))
    elif args.command == "record-result":
        result = record_result(
            manifest,
            repo,
            args.dataset,
            raw_path=Path(args.raw) if args.raw else None,
            report_path=Path(args.report),
        )
    else:
        result = approve(manifest, repo)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
