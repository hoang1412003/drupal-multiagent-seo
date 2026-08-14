"""Hop dong request/response cua /api/v1.

`extra="forbid"` la chu y: mot client gui `site_id` phai bi TU CHOI chu khong
duoc bo qua im lang. Bo qua im lang nghia la client tuong no da chon site,
con server thi chon site khac - hai ben cung nghi minh dung.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_content_id: str = Field(min_length=1, max_length=128)
    # Revision ID cua Drupal la so nguyen duong. Ep pattern o day de connector
    # khong bao gio ghep duoc chuoi la vao `?resourceVersion=id:...`.
    external_revision_id: str | None = Field(
        default=None, max_length=64, pattern=r"^[1-9][0-9]*$"
    )
    content_type: str = Field(min_length=1, max_length=64)
    langcode: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash_version: Literal[2]
    source: Literal["event", "manual", "reconcile"] = "event"
    force: bool = False


class JobAccepted(BaseModel):
    job_id: UUID
    status: str
    duplicate: bool
    policy_version: str


class JobStatus(BaseModel):
    job_id: UUID
    status: str
    attempts: int
    last_error: str | None
    external_content_id: str
    external_revision_id: str | None
    content_hash: str
    content_hash_version: int
    policy_version: str
    source: str
    created_at: datetime
    updated_at: datetime
