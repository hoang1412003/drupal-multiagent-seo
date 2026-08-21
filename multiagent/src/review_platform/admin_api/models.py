"""Pydantic model cho Console API.

Quy uoc chuyen kieu, ap dung nhat quan o moi model:
- UUID     -> str
- datetime -> chuoi ISO-8601 UTC ket thuc bang "Z" (dung `iso`)
- date     -> chuoi "YYYY-MM-DD"
- Decimal  -> so JSON (dung `to_number`). KHONG khai bao truong la Decimal:
  Pydantic v2 serialize Decimal thanh CHUOI, frontend se nhan "82.5" thay vi
  82.5 va moi phep so sanh so ben React deu sai am tham.
- None     -> null, khong doi thanh chuoi rong.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def to_number(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


class MeResponse(BaseModel):
    # `id` de frontend nhan ra "day la chinh minh" khi khoa hay ha quyen mot
    # tai khoan. So sanh bang username cung chay duoc nhung so sanh danh tinh
    # thi phai dung dinh danh.
    id: str
    username: str
    role: str
    must_change_password: bool
    csrf_token: str


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class ChangePasswordRequest(BaseModel):
    current_password: str = ""
    new_password: str = ""


class PageResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


def page_payload(view, items: list) -> dict:
    """Trai PageView thanh dict chuan. Dung cho MOI endpoint danh sach."""
    return {
        "items": items,
        "page": view.page,
        "page_size": view.page_size,
        "total": view.total,
        "total_pages": view.total_pages,
    }


class CostEstimateModel(BaseModel):
    input_tokens: int
    output_tokens: int
    estimated_usd: float | None
    pricing_version: int
    effective_at: str
    currency: str
    source: str
    unknown_models: list[str]

    @classmethod
    def from_dataclass(cls, value) -> "CostEstimateModel":
        return cls(
            input_tokens=value.input_tokens,
            output_tokens=value.output_tokens,
            estimated_usd=to_number(value.estimated_usd),
            pricing_version=value.pricing_version,
            effective_at=value.effective_at.isoformat(),
            currency=value.currency,
            source=value.source,
            unknown_models=list(value.unknown_models),
        )


class DashboardResponse(BaseModel):
    date_from: str
    date_to: str
    queue_counts: dict[str, int]
    total_reviews: int
    decision_counts: dict[str, int]
    duration_p50_ms: float | None
    duration_p95_ms: float | None
    cost_estimate: CostEstimateModel
    writeback_counts: dict[str, int]
    writeback_success_rate: float | None
    worker_status: str
    connector_status: str
    worker_running: int
    worker_stale: int
    worker_last_seen_at: str | None

    @classmethod
    def from_view(cls, view) -> "DashboardResponse":
        return cls(
            date_from=view.date_from.isoformat(),
            date_to=view.date_to.isoformat(),
            queue_counts=view.queue_counts,
            total_reviews=view.total_reviews,
            decision_counts=view.decision_counts,
            duration_p50_ms=to_number(view.duration_p50_ms),
            duration_p95_ms=to_number(view.duration_p95_ms),
            cost_estimate=CostEstimateModel.from_dataclass(view.cost_estimate),
            writeback_counts=view.writeback_counts,
            writeback_success_rate=to_number(view.writeback_success_rate),
            worker_status=view.worker_status,
            connector_status=view.connector_status,
            worker_running=view.worker_running,
            worker_stale=view.worker_stale,
            worker_last_seen_at=iso(view.worker_last_seen_at),
        )


class JobListItemModel(BaseModel):
    public_id: str
    created_at: str
    site_id: str
    site_slug: str
    external_content_id: str
    status: str
    attempts: int
    source: str
    policy_version: str

    @classmethod
    def from_view(cls, item) -> "JobListItemModel":
        return cls(
            public_id=str(item.public_id),
            created_at=iso(item.created_at),
            site_id=str(item.site_id),
            site_slug=item.site_slug,
            external_content_id=item.external_content_id,
            status=item.status,
            attempts=item.attempts,
            source=item.source,
            policy_version=item.policy_version,
        )


class JobPage(PageResponse):
    items: list[JobListItemModel]


class RetryRequest(BaseModel):
    # Retry chay lai pipeline tuc la GOI API TRA PHI. Mac dinh False de mot
    # request thieu truong nay khong tinh tien cua ai.
    confirm_cost: bool = False
    reason: str | None = None


class JobDetailModel(BaseModel):
    public_id: str
    created_at: str
    updated_at: str
    site_id: str
    site_slug: str
    site_name: str
    profile_id: str
    policy_version: str
    external_content_id: str
    external_revision_id: str | None
    content_type: str
    langcode: str
    status: str
    attempts: int
    source: str
    correlation_id: str
    supersedes_job_public_id: str | None
    last_error: str | None
    run_public_id: str | None
    writeback_status: str | None
    run_scored_at: str | None
    saved_result_available: bool

    @classmethod
    def from_view(cls, job) -> "JobDetailModel":
        return cls(
            public_id=str(job.public_id),
            created_at=iso(job.created_at),
            updated_at=iso(job.updated_at),
            site_id=str(job.site_id),
            site_slug=job.site_slug,
            site_name=job.site_name,
            profile_id=str(job.profile_id),
            policy_version=job.policy_version,
            external_content_id=job.external_content_id,
            external_revision_id=job.external_revision_id,
            content_type=job.content_type,
            langcode=job.langcode,
            status=job.status,
            attempts=job.attempts,
            source=job.source,
            correlation_id=str(job.correlation_id),
            supersedes_job_public_id=(
                None
                if job.supersedes_job_public_id is None
                else str(job.supersedes_job_public_id)
            ),
            last_error=job.last_error,
            run_public_id=(
                None if job.run_public_id is None else str(job.run_public_id)
            ),
            writeback_status=job.writeback_status,
            run_scored_at=iso(job.run_scored_at),
            saved_result_available=job.saved_result_available,
        )


class ReviewListItemModel(BaseModel):
    public_id: str
    scored_at: str
    site_id: str
    site_slug: str
    external_content_id: str
    decision: str | None
    final_score: float | None
    profile_code: str
    policy_version: str
    model: str
    is_fixture: bool

    @classmethod
    def from_view(cls, item) -> "ReviewListItemModel":
        return cls(
            public_id=str(item.public_id),
            scored_at=iso(item.scored_at),
            site_id=str(item.site_id),
            site_slug=item.site_slug,
            external_content_id=item.external_content_id,
            decision=item.decision,
            final_score=to_number(item.final_score),
            profile_code=item.profile_code,
            policy_version=item.policy_version,
            model=item.model,
            is_fixture=item.is_fixture,
        )


class ReviewPage(PageResponse):
    items: list[ReviewListItemModel]


class AgentResultModel(BaseModel):
    name: str
    # score la gia tri tu do da qua sanitize: co the la so, chuoi, hoac null.
    score: float | int | str | bool | None
    criteria: list[dict]
    issues: list[dict]
    evidence: list[dict]

    @classmethod
    def from_view(cls, agent) -> "AgentResultModel":
        return cls(
            name=agent.name,
            score=agent.score,
            criteria=list(agent.criteria),
            issues=list(agent.issues),
            evidence=list(agent.evidence),
        )


class ReviewDetailModel(BaseModel):
    public_id: str
    scored_at: str
    duration_ms: int | None
    decision: str | None
    final_score: float | None
    missing_agents: list[str]
    veto_reason: str | None
    note: str | None
    agents: list[AgentResultModel]
    config_meta: dict | list | str | int | float | bool | None
    cost_estimate: CostEstimateModel
    usage_available: bool
    model: str
    writeback_status: str
    writeback_error: str | None
    site_id: str
    site_slug: str
    site_name: str
    profile_id: str
    profile_code: str
    policy_version: str
    external_content_id: str
    external_revision_id: str | None
    content_type: str
    langcode: str
    correlation_id: str
    is_fixture: bool
    drupal_url: str | None

    @classmethod
    def from_view(cls, review) -> "ReviewDetailModel":
        return cls(
            public_id=str(review.public_id),
            scored_at=iso(review.scored_at),
            duration_ms=review.duration_ms,
            decision=review.decision,
            final_score=to_number(review.final_score),
            missing_agents=list(review.missing_agents),
            veto_reason=review.veto_reason,
            note=review.note,
            agents=[AgentResultModel.from_view(a) for a in review.agents],
            config_meta=review.config_meta,
            cost_estimate=CostEstimateModel.from_dataclass(review.cost_estimate),
            usage_available=review.usage_available,
            model=review.model,
            writeback_status=review.writeback_status,
            writeback_error=review.writeback_error,
            site_id=str(review.site_id),
            site_slug=review.site_slug,
            site_name=review.site_name,
            profile_id=str(review.profile_id),
            profile_code=review.profile_code,
            policy_version=review.policy_version,
            external_content_id=review.external_content_id,
            external_revision_id=review.external_revision_id,
            content_type=review.content_type,
            langcode=review.langcode,
            correlation_id=str(review.correlation_id),
            is_fixture=review.is_fixture,
            drupal_url=review.drupal_url,
        )


class SiteOptionModel(BaseModel):
    slug: str
    name: str
    active: bool


class FiltersResponse(BaseModel):
    """Gia tri hop le cho moi bo loc, lay tu server.

    Ton tai de frontend khong hard-code danh sach nao. Mot brief tung ghi
    trang thai job la `succeeded` trong khi that su la `done`, va khong phep
    kiem nao bat duoc vi gia tri hop le chua bao gio nam trong hop dong.
    """

    sites: list[SiteOptionModel]
    job_sources: list[str]
    job_statuses: list[str]
    roles: list[str]
    review_decisions: list[str]
    writeback_statuses: list[str]
    audit_actions: list[str]
    audit_outcomes: list[str]


class AuditEventModel(BaseModel):
    id: int
    actor_user_id: str | None
    actor_username: str
    action: str
    target_type: str
    target_id: str | None
    outcome: str
    # Da qua sanitization o queries: bi mat hien thanh "[da an]".
    metadata_text: str
    created_at: str

    @classmethod
    def from_view(cls, item) -> "AuditEventModel":
        return cls(
            id=item.id,
            actor_user_id=(
                None if item.actor_user_id is None else str(item.actor_user_id)
            ),
            actor_username=item.actor_username,
            action=item.action,
            target_type=item.target_type,
            target_id=item.target_id,
            outcome=item.outcome,
            metadata_text=item.metadata_text,
            created_at=iso(item.created_at),
        )


class AuditPage(PageResponse):
    items: list[AuditEventModel]


class LabelValueModel(BaseModel):
    """Cap nhan-gia tri co THU TU.

    Nguon la tuple[tuple[str, str], ...] nen thu tu co y nghia. Doi sang dict
    se mat thu tu do va co the nuot khoa trung.
    """

    label: str
    value: str


class PolicyFileModel(BaseModel):
    label: str
    relative_path: str
    sha256: str
    modified_at: str
    metadata: list[LabelValueModel]
    error: str | None

    @classmethod
    def from_view(cls, item) -> "PolicyFileModel":
        return cls(
            label=item.label,
            relative_path=item.relative_path,
            sha256=item.sha256,
            modified_at=iso(item.modified_at),
            metadata=[
                LabelValueModel(label=k, value=v) for k, v in item.metadata
            ],
            error=item.error,
        )


class ProfileAssignmentModel(BaseModel):
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
    policy_metadata: list[LabelValueModel]

    @classmethod
    def from_view(cls, item) -> "ProfileAssignmentModel":
        return cls(
            site_slug=item.site_slug,
            site_name=item.site_name,
            connector_type=item.connector_type,
            site_active=item.site_active,
            intake_paused=item.intake_paused,
            profile_code=item.profile_code,
            market_code=item.market_code,
            language_code=item.language_code,
            content_type=item.content_type,
            profile_status=item.profile_status,
            policy_version=item.policy_version,
            policy_metadata=[
                LabelValueModel(label=k, value=v) for k, v in item.policy_metadata
            ],
        )


class KBSummaryModel(BaseModel):
    collection: str
    content_type: str
    langcode: str
    chunk_count: int
    metadata_excerpt: str
    embedding_model: str | None
    embedding_dimension: int | None

    @classmethod
    def from_view(cls, item) -> "KBSummaryModel":
        return cls(
            collection=item.collection,
            content_type=item.content_type,
            langcode=item.langcode,
            chunk_count=item.chunk_count,
            metadata_excerpt=item.metadata_excerpt,
            embedding_model=item.embedding_model,
            embedding_dimension=item.embedding_dimension,
        )


class ConfigKbResponse(BaseModel):
    policy_files: list[PolicyFileModel]
    profile_assignments: list[ProfileAssignmentModel]
    kb_summary: list[KBSummaryModel]


class ExperimentModel(BaseModel):
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
    has_evidence: bool
    # Loi nhac dung suy dien tu cac truong con thieu. Bo di la mo duong cho
    # nguoi doc ket luan tu du lieu khong day du.
    provenance_warning: str | None

    @classmethod
    def from_view(cls, item) -> "ExperimentModel":
        return cls(
            experiment=item.experiment,
            status=item.status,
            score_path_snapshot=item.score_path_snapshot,
            head_commit=item.head_commit,
            prompt_version=item.prompt_version,
            model=item.model,
            run_at=item.run_at,
            evidence_path=item.evidence_path,
            metadata_complete=item.metadata_complete,
            summary=item.summary,
            has_evidence=item.evidence_file is not None,
            provenance_warning=item.provenance_warning,
        )


class EvaluationResponse(BaseModel):
    experiments: list[ExperimentModel]


# Do dai toi da cua ly do tam dung/mo lai. Admin cu cat cut im lang o 300;
# Console API tu choi han thay vi cat - xem connection_routes.
MAX_REASON = 300


class ConnectionModel(BaseModel):
    slug: str
    name: str
    base_url: str
    # TEN bien moi truong chua credential, khong phai gia tri. Xem
    # connectors/secrets.py: secret_ref la khoa tra os.environ.
    secret_ref: str
    active: bool
    intake_paused: bool
    profile_code: str | None
    policy_version: str | None
    token_prefixes: list[str]
    last_health_status: str | None
    last_health_checked_at: str | None
    last_health_error: str | None

    @classmethod
    def from_view(cls, view) -> "ConnectionModel":
        return cls(
            slug=view.slug,
            name=view.name,
            base_url=view.base_url,
            secret_ref=view.secret_ref,
            active=view.active,
            intake_paused=view.intake_paused,
            profile_code=view.profile_code,
            policy_version=view.policy_version,
            token_prefixes=list(view.token_prefixes),
            last_health_status=view.last_health_status,
            last_health_checked_at=iso(view.last_health_checked_at),
            last_health_error=view.last_health_error,
        )


class ReasonRequest(BaseModel):
    reason: str | None = None


class TestConnectionResponse(BaseModel):
    # `ok` la boolean ro rang thay vi bat frontend so sanh chuoi
    # last_health_status == "ok". So sanh chuoi la dung loai chi tiet ma
    # nguoi viet UI doan sai - da xay ra voi enum trang thai job.
    ok: bool
    error_code: str | None
    connection: ConnectionModel


class UserModel(BaseModel):
    """Mot tai khoan quan tri.

    KHONG co truong nao lien quan toi mat khau. `password_hash` nam ngay canh
    cac cot nay trong bang, nen moi lan them truong phai kiem lai: mot bam
    Argon2 lot ra ngoai la mot muc tieu be khoa ngoai tuyen.
    """

    id: str
    username: str
    role: str
    active: bool
    must_change_password: bool
    last_login_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_view(cls, item) -> "UserModel":
        return cls(
            id=str(item.id),
            username=item.username,
            role=item.role.value,
            active=item.active,
            must_change_password=item.must_change_password,
            last_login_at=iso(item.last_login_at),
            created_at=iso(item.created_at),
            updated_at=iso(item.updated_at),
        )


class UserPage(PageResponse):
    items: list[UserModel]


class CreateUserRequest(BaseModel):
    username: str = ""
    role: str = ""


class ChangeRoleRequest(BaseModel):
    role: str = ""


class TemporaryPasswordResponse(BaseModel):
    """Tra ve DUY NHAT mot lan, ngay sau khi tao hoac dat lai mat khau.

    Endpoint tra kieu nay phai dat Cache-Control: no-store. Mat khau con dung
    duoc ma nam trong bo nho dem cua proxy hay trinh duyet la mot ban sao
    khong ai kiem soat va khong ai thu hoi duoc.
    """

    user: UserModel
    temporary_password: str
