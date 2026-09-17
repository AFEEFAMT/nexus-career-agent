from uuid import UUID

from pydantic import BaseModel


class JobMatchResponse(BaseModel):
    match_id: UUID
    job_id: UUID

    title: str
    company: str | None
    location: str | None
    remote_ok: bool | None
    stipend: str | None
    required_skills: list[str]

    score: float
    justification: str | None

    source: str
    source_url: str


class MatchGenerationResponse(BaseModel):
    resume_id: UUID
    total_matches: int
    jobs_embedded: int
    matches: list[JobMatchResponse]