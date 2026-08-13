"""Context bat bien cua site va policy dung cho mot review run."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SiteContext:
    id: UUID
    slug: str
    connector_type: str
    base_url: str
    secret_ref: str
    active: bool
    intake_paused: bool


@dataclass(frozen=True)
class ReviewProfileContext:
    id: UUID
    code: str
    market_code: str
    language_code: str
    content_type: str
    policy_version: str
    policy_snapshot: dict


@dataclass(frozen=True)
class ReviewContext:
    site: SiteContext
    profile: ReviewProfileContext
