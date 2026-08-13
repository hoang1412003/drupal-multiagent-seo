"""Loader manifest evaluation co allowlist va provenance validation."""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path, PurePosixPath
import re

from review_platform.admin import sanitization


REPO_ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_DIR = (REPO_ROOT / "docs" / "evidence").resolve()
MANIFEST_PATH = EVIDENCE_DIR / "evaluation-manifest.json"
EXPERIMENTS = frozenset(f"E{number}" for number in range(1, 7))
STATUSES = frozenset({"valid", "pending", "historical_invalid"})
_FIELDS = frozenset({
    "experiment",
    "status",
    "score_path_snapshot",
    "head_commit",
    "prompt_version",
    "model",
    "run_at",
    "evidence_path",
    "metadata_complete",
    "summary",
})
_SHA1_PATTERN = re.compile(r"[0-9a-f]{40}")


class ManifestError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExperimentView:
    experiment: str
    status: str
    score_path_snapshot: str | None
    head_commit: str | None
    prompt_version: str | None
    model: str | None
    run_at: str | None
    evidence_path: str | None
    metadata_complete: bool
    summary: str
    evidence_file: Path | None

    @property
    def provenance_warning(self) -> str | None:
        if self.metadata_complete:
            return None
        return "Provenance chưa đầy đủ; không suy diễn các trường còn thiếu."


def _optional_text(entry: Mapping, field: str, *, maximum: int = 200) -> str | None:
    value = entry.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} phai la chuoi khong rong hoac null")
    return sanitization.sanitize_text(value.strip(), maximum)


def _validate_iso_utc(value: str | None) -> None:
    if value is None:
        return
    if not value.endswith("Z"):
        raise ManifestError("run_at phai la UTC ISO-8601 ket thuc bang Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestError("run_at khong phai ISO-8601 hop le") from exc


def _manifest_file(path) -> Path:
    candidate = Path(path).resolve()
    if not candidate.is_relative_to(EVIDENCE_DIR) or candidate.suffix.casefold() != ".json":
        raise ManifestError("manifest phai la JSON trong docs/evidence")
    if not candidate.is_file():
        raise ManifestError("khong tim thay evaluation manifest")
    return candidate


def _evidence_file(raw_path: str | None, *, required: bool) -> Path | None:
    if raw_path is None:
        if required:
            raise ManifestError("trang thai nay bat buoc co evidence_path")
        return None
    if not isinstance(raw_path, str) or not raw_path.strip() or "\\" in raw_path:
        raise ManifestError("evidence_path khong hop le")
    pure = PurePosixPath(raw_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ManifestError("evidence_path khong duoc tuyet doi hoac traversal")
    if pure.parts[:2] != ("docs", "evidence"):
        raise ManifestError("evidence_path phai nam trong docs/evidence")
    candidate = (REPO_ROOT / Path(*pure.parts)).resolve()
    if not candidate.is_relative_to(EVIDENCE_DIR):
        raise ManifestError("evidence resolve ra ngoai docs/evidence")
    if candidate.suffix.casefold() not in {".json", ".txt"}:
        raise ManifestError("evidence chi cho phep JSON hoac text")
    if not candidate.is_file():
        raise ManifestError("evidence duoc tham chieu khong ton tai")
    return candidate


def _parse_entry(raw) -> ExperimentView:
    if not isinstance(raw, Mapping) or frozenset(raw) != _FIELDS:
        raise ManifestError("entry phai la object dung schema")
    experiment = raw["experiment"]
    status = raw["status"]
    if experiment not in EXPERIMENTS:
        raise ManifestError("experiment chi duoc E1 den E6")
    if status not in STATUSES:
        raise ManifestError("status evaluation khong hop le")
    metadata_complete = raw["metadata_complete"]
    if not isinstance(metadata_complete, bool):
        raise ManifestError("metadata_complete phai la boolean")

    score_path_snapshot = _optional_text(raw, "score_path_snapshot")
    head_commit = _optional_text(raw, "head_commit", maximum=40)
    prompt_version = _optional_text(raw, "prompt_version")
    model = _optional_text(raw, "model")
    run_at = _optional_text(raw, "run_at")
    evidence_path = _optional_text(raw, "evidence_path", maximum=500)
    summary = _optional_text(raw, "summary", maximum=1000)
    if summary is None:
        raise ManifestError("summary bat buoc")
    _validate_iso_utc(run_at)
    if head_commit is not None and _SHA1_PATTERN.fullmatch(head_commit.casefold()) is None:
        raise ManifestError("head_commit phai la SHA-1 40 ky tu")

    if status == "pending":
        if evidence_path is not None or run_at is not None:
            raise ManifestError("pending bat buoc evidence_path/run_at null")
        evidence_file = None
    else:
        evidence_file = _evidence_file(evidence_path, required=True)

    if metadata_complete and any(
        value is None
        for value in (
            score_path_snapshot,
            head_commit,
            prompt_version,
            model,
            run_at,
            evidence_path,
        )
    ):
        raise ManifestError("metadata_complete=true nhung provenance con thieu")

    return ExperimentView(
        experiment=experiment,
        status=status,
        score_path_snapshot=score_path_snapshot,
        head_commit=head_commit,
        prompt_version=prompt_version,
        model=model,
        run_at=run_at,
        evidence_path=evidence_path,
        metadata_complete=metadata_complete,
        summary=summary,
        evidence_file=evidence_file,
    )


def load_manifest(path=MANIFEST_PATH) -> tuple[ExperimentView, ...]:
    manifest_file = _manifest_file(path)
    try:
        raw = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError("khong doc duoc evaluation manifest") from exc
    if not isinstance(raw, list):
        raise ManifestError("evaluation manifest root phai la list")
    entries = tuple(_parse_entry(entry) for entry in raw)
    experiments = [entry.experiment for entry in entries]
    if len(experiments) != len(set(experiments)):
        raise ManifestError("evaluation manifest co experiment trung")
    if set(experiments) != EXPERIMENTS:
        raise ManifestError("evaluation manifest phai co du E1 den E6")
    return tuple(sorted(entries, key=lambda entry: int(entry.experiment[1:])))


def find_experiment(entries, experiment: str) -> ExperimentView | None:
    if experiment not in EXPERIMENTS:
        return None
    return next((entry for entry in entries if entry.experiment == experiment), None)


def read_evidence(entry: ExperimentView, *, maximum_bytes: int = 5_000_000):
    if entry.evidence_file is None:
        raise FileNotFoundError(entry.experiment)
    content = entry.evidence_file.read_bytes()
    if len(content) > maximum_bytes:
        raise ManifestError("evidence vuot gioi han hien thi")
    media_type = (
        "application/json"
        if entry.evidence_file.suffix.casefold() == ".json"
        else "text/plain"
    )
    return content, media_type
