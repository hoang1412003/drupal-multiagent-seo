"""Kieu du lieu va loai loi chung cho moi connector CMS.

Loi duoc phan loai theo CACH XU LY chu khong theo ma HTTP: worker can biet
"thu lai co ich khong", khong can biet 502 khac 503 cho nao. Bon nhom:

- ConnectorAuthError      : sai quyen. Thu lai 3 lan cung sai 3 lan.
- ConnectorRevisionNotFound: revision da bien mat. Job nay vo nghia, dung.
- ConnectorPayloadError   : response sai hop dong. Retry mu chi lap lai loi.
- ConnectorTransientError : mang/tai. Thu lai co ich - va CHI nhom nay.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID


class ConnectorError(RuntimeError):
    """Goc cua moi loi connector; mang ma an toan de luu vao last_error."""

    ma = "internal"


class ConnectorSecretError(ConnectorError):
    ma = "connector_auth"


class ConnectorAuthError(ConnectorError):
    ma = "connector_auth"


class ConnectorRevisionNotFound(ConnectorError):
    ma = "connector_revision_missing"


class ConnectorPayloadError(ConnectorError):
    ma = "connector_payload"


class ConnectorTransientError(ConnectorError):
    ma = "llm_transient"

    def __init__(self, message: str, *, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class ContentDocument:
    fields: dict
    raw_content: dict
    source_url: str | None
    external_revision_id: str | None
    content_type: str
    langcode: str


@dataclass(frozen=True)
class PendingContent:
    external_content_id: str
    external_revision_id: str | None
    content_hash: str
    content_type: str
    langcode: str
    source_url: str | None
    content_hash_version: int = 2


@dataclass(frozen=True)
class PendingPage:
    items: tuple = field(default=())
    next_after_revision_id: int | None = None


@dataclass(frozen=True)
class ConnectorHealth:
    ok: bool
    status_code: int | None
    checked_at: datetime
    error_code: str | None


@dataclass(frozen=True)
class WriteBackRequest:
    run_id: UUID
    external_content_id: str
    expected_revision_id: str | None
    content_hash: str
    content_hash_version: int
    status: str
    score: float | None
    suggestions: str
    report_json: dict


@dataclass(frozen=True)
class WriteBackResult:
    outcome: Literal["applied", "already_applied", "content_superseded"]
    applied_revision_id: str | None = None


class Connector(Protocol):
    def fetch_content(
        self,
        external_content_id: str,
        *,
        external_revision_id: str | None = None,
        working_copy: bool = False,
    ) -> ContentDocument: ...

    def write_back(self, request: WriteBackRequest) -> WriteBackResult: ...

    def list_pending(
        self, *, after_revision_id: int = 0, limit: int = 50
    ) -> PendingPage: ...

    def health(self) -> ConnectorHealth: ...
