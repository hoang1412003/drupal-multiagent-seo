"""Snapshot metadata config/profile/KB an toan cho trang quan tri read-only."""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import yaml

from review_platform.admin import sanitization


MULTIAGENT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class PolicySource:
    label: str
    relative_path: str
    kind: str


@dataclass(frozen=True)
class PolicyFileView:
    label: str
    relative_path: str
    sha256: str
    modified_at: datetime
    metadata: tuple[tuple[str, str], ...]
    error: str | None


@dataclass(frozen=True)
class ProfileAssignmentView:
    site_slug: str
    site_name: str
    connector_type: str
    site_active: bool
    intake_paused: bool
    profile_code: str
    market_code: str
    language_code: str
    content_type: str
    profile_status: str
    policy_version: str
    policy_metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class KBSummaryView:
    collection: str
    content_type: str
    langcode: str
    chunk_count: int
    metadata_excerpt: str
    embedding_model: str | None
    embedding_dimension: int | None


POLICY_SOURCES = (
    PolicySource("Scoring", "config/scoring.yaml", "scoring"),
    PolicySource(
        "Quy tắc Compliance",
        "src/agents/compliance_rules.json",
        "compliance",
    ),
    PolicySource("Quy tắc Brand Voice", "src/agents/brand_rules.json", "brand"),
    PolicySource("Nguồn thông số Fact-check", "src/kb/specs.json", "specs"),
)
_ALLOWED_RELATIVE_PATHS = frozenset(source.relative_path for source in POLICY_SOURCES)
_POLICY_SNAPSHOT_KEYS = (
    ("release", "Release"),
    ("score_path_snapshot", "Score-path snapshot"),
    ("prompt_version", "Prompt version"),
    ("rubric_version", "Rubric version"),
    ("model", "Model chấm"),
    ("scoring_key", "Scoring key"),
    ("scoring_sha256", "Scoring SHA-256"),
    ("compliance_rules_sha256", "Compliance rules SHA-256"),
    ("brand_rules_sha256", "Brand rules SHA-256"),
    ("factcheck_kb_specs_sha256", "Fact-check specs SHA-256"),
    ("brand_guideline_sha256", "Brand guideline SHA-256"),
    ("brand_corpus_index_sha256", "Brand corpus index SHA-256"),
    ("embedding_model", "Embedding model kỳ vọng"),
    ("embedding_dimension", "Embedding dimension kỳ vọng"),
)
_KB_META_KEYS = (
    "model",
    "verified",
    "sample_id",
    "topic_group",
    "source_url",
    "embedding_model",
    "embedding_dimension",
)


class UnsafePolicyPathError(ValueError):
    pass


def _display(value) -> str:
    if value is None or value == "":
        return "Chưa version hóa"
    if value is True:
        return "Có"
    if value is False:
        return "Không"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(sanitization.sanitize_text(item, 100) for item in value)
    return sanitization.sanitize_text(value, 200)


def _resolve_allowed_path(relative_path: str) -> Path:
    """Resolve mot ten trong allowlist; request web khong truyen duoc vao day."""
    normalized = Path(relative_path).as_posix()
    if normalized not in _ALLOWED_RELATIVE_PATHS:
        raise UnsafePolicyPathError("nguon policy nam ngoai allowlist")
    root = MULTIAGENT_ROOT.resolve()
    candidate = (root / normalized).resolve()
    if not candidate.is_relative_to(root):
        raise UnsafePolicyPathError("nguon policy thoat khoi multiagent root")
    return candidate


def _scoring_metadata(raw) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, Mapping):
        raise ValueError("scoring root phai la mapping")
    scopes = sorted(key for key in raw if key not in {"version", "default"})
    active = raw.get("cam_nang:vi")
    active_meta = active.get("meta") if isinstance(active, Mapping) else None
    calibrated = active_meta.get("calibrated") if isinstance(active_meta, Mapping) else None
    return (
        ("Định dạng", "YAML"),
        ("Phiên bản", _display(raw.get("version"))),
        ("Scope cấu hình", _display(scopes)),
        ("Scope hiện hành đã calibrate", _display(calibrated)),
    )


def _compliance_metadata(raw) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, Mapping):
        raise ValueError("compliance rules root phai la mapping")
    phrases = raw.get("phrases")
    scopes = raw.get("pham_vi")
    return (
        ("Định dạng", "JSON"),
        ("Phiên bản", _display(raw.get("version"))),
        ("Số mẫu phrase", _display(len(phrases) if isinstance(phrases, list) else 0)),
        ("Số cụm phạm vi", _display(len(scopes) if isinstance(scopes, list) else 0)),
    )


def _brand_metadata(raw) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, Mapping):
        raise ValueError("brand rules root phai la mapping")
    corpus = raw.get("corpus")
    terms = raw.get("terms")
    models = raw.get("model_names")
    return (
        ("Định dạng", "JSON"),
        ("Phiên bản", _display(raw.get("version"))),
        ("Sinh lúc", _display(raw.get("generated_at"))),
        ("Số tài liệu corpus", _display(corpus.get("n_docs") if isinstance(corpus, Mapping) else None)),
        ("Số model", _display(len(models) if isinstance(models, list) else 0)),
        ("Số thuật ngữ", _display(len(terms) if isinstance(terms, list) else 0)),
    )


def _specs_metadata(raw) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, list):
        raise ValueError("fact-check specs root phai la list")
    entries = [entry for entry in raw if isinstance(entry, Mapping)]
    content_types = sorted({str(entry.get("content_type")) for entry in entries if entry.get("content_type")})
    languages = sorted({str(entry.get("langcode")) for entry in entries if entry.get("langcode")})
    verified = sum(entry.get("verified") is True for entry in entries)
    return (
        ("Định dạng", "JSON"),
        ("Phiên bản", "Chưa version hóa"),
        ("Số mục", _display(len(entries))),
        ("Đã xác minh", _display(verified)),
        ("Content type", _display(content_types)),
        ("Ngôn ngữ", _display(languages)),
    )


_METADATA_READERS = {
    "scoring": _scoring_metadata,
    "compliance": _compliance_metadata,
    "brand": _brand_metadata,
    "specs": _specs_metadata,
}


def load_policy_files() -> tuple[PolicyFileView, ...]:
    """Doc dung bon file co dinh va chi tra metadata da allowlist."""
    result = []
    for source in POLICY_SOURCES:
        content = b""
        hash_content = content
        modified_at = datetime.fromtimestamp(0, tz=timezone.utc)
        try:
            path = _resolve_allowed_path(source.relative_path)
            content = path.read_bytes()
            hash_content = content
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            text = content.decode("utf-8")
            hash_content = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
            raw = yaml.safe_load(text) if source.kind == "scoring" else json.loads(text)
            metadata = _METADATA_READERS[source.kind](raw)
            error = None
        except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as exc:
            metadata = (("Trạng thái", "Không đọc được metadata"),)
            error = sanitization.sanitize_text(exc, 300)
        result.append(
            PolicyFileView(
                label=source.label,
                relative_path=source.relative_path,
                sha256=hashlib.sha256(hash_content).hexdigest(),
                modified_at=modified_at,
                metadata=metadata,
                error=error,
            )
        )
    return tuple(result)


def _safe_policy_metadata(value) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Mapping):
        return (("Trạng thái", "Policy snapshot không hợp lệ"),)
    return tuple(
        (label, _display(value.get(key)))
        for key, label in _POLICY_SNAPSHOT_KEYS
    )


def load_profile_assignments(conn) -> tuple[ProfileAssignmentView, ...]:
    """Doc site/profile assignment ma khong SELECT base_url hay secret_ref."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.slug,s.name,s.connector_type,s.active,s.intake_paused,"
            "p.code,p.market_code,p.language_code,p.content_type,p.status,"
            "p.policy_version,p.policy_snapshot "
            "FROM site_profile_assignment a "
            "JOIN site s ON s.id=a.site_id "
            "JOIN review_profile p ON p.id=a.profile_id "
            "WHERE a.active=true ORDER BY s.slug,p.code"
        )
        rows = cur.fetchall()
    return tuple(
        ProfileAssignmentView(
            site_slug=sanitization.sanitize_text(row[0], 100),
            site_name=sanitization.sanitize_text(row[1], 200),
            connector_type=sanitization.sanitize_text(row[2], 50),
            site_active=bool(row[3]),
            intake_paused=bool(row[4]),
            profile_code=sanitization.sanitize_text(row[5], 100),
            market_code=sanitization.sanitize_text(row[6], 10),
            language_code=sanitization.sanitize_text(row[7], 20),
            content_type=sanitization.sanitize_text(row[8], 100),
            profile_status=sanitization.sanitize_text(row[9], 30),
            policy_version=sanitization.sanitize_text(row[10], 100),
            policy_metadata=_safe_policy_metadata(row[11]),
        )
        for row in rows
    )


_KB_SUMMARY_SQL = (
    "SELECT collection,content_type,langcode,count(*)::bigint,"
    "jsonb_strip_nulls(jsonb_build_object("
    "'model',min(nullif(meta->>'model','')),'verified',"
    "min(nullif(meta->>'verified','')),'sample_id',"
    "min(nullif(meta->>'sample_id','')),'topic_group',"
    "min(nullif(meta->>'topic_group','')),'source_url',"
    "min(nullif(meta->>'source_url','')),'embedding_model',"
    "min(nullif(meta->>'embedding_model','')),'embedding_dimension',"
    "min(nullif(meta->>'embedding_dimension','')))) "
    "FROM kb_chunk GROUP BY collection,content_type,langcode "
    "ORDER BY collection,content_type,langcode"
)


def _positive_dimension(value) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def load_kb_summary(conn) -> tuple[KBSummaryView, ...]:
    """Aggregate KB; tuyet doi khong doc cot document hoac vector."""
    with conn.cursor() as cur:
        cur.execute(_KB_SUMMARY_SQL)
        rows = cur.fetchall()
    result = []
    for row in rows:
        raw_meta = row[4] if isinstance(row[4], Mapping) else {}
        allowlisted = {key: raw_meta[key] for key in _KB_META_KEYS if key in raw_meta}
        safe_meta = sanitization.sanitize_mapping(
            allowlisted,
            max_depth=2,
            max_items=len(_KB_META_KEYS),
            max_text_length=200,
        )
        excerpt = sanitization.sanitize_text(
            json.dumps(safe_meta, ensure_ascii=False, sort_keys=True),
            500,
        )
        model = raw_meta.get("embedding_model")
        result.append(
            KBSummaryView(
                collection=sanitization.sanitize_text(row[0], 100),
                content_type=sanitization.sanitize_text(row[1], 100),
                langcode=sanitization.sanitize_text(row[2], 20),
                chunk_count=max(0, int(row[3])),
                metadata_excerpt=excerpt,
                embedding_model=(
                    sanitization.sanitize_text(model, 100)
                    if isinstance(model, str) and model.strip()
                    else None
                ),
                embedding_dimension=_positive_dimension(raw_meta.get("embedding_dimension")),
            )
        )
    return tuple(result)
