from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ShortlistResponse(BaseModel):
    shortlist_id: UUID
    job_id: UUID

    title: str
    company: str | None
    location: str | None
    remote_ok: bool | None
    stipend: str | None
    required_skills: list[str]

    source: str
    source_url: str

    match_score: float | None
    created_at: datetime