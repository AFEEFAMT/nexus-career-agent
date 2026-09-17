from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobSearchResult(BaseModel):
    job_id: UUID
    title: str
    company: str | None
    location: str | None
    remote_ok: bool | None
    stipend: str | None
    required_skills: list[str]
    experience_level: str | None
    deadline: datetime | None
    source: str
    source_url: str
    semantic_score: float


class MetadataRefreshResponse(BaseModel):
    attempted: int
    enriched: int
    skipped: int
    rate_limited: bool
    errors: list[str] = Field(
        default_factory=list
    )