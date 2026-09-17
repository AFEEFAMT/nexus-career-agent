from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BriefingResponse(BaseModel):
    id: UUID
    briefing_type: str
    script: str | None
    provider: str | None
    status: str
    media_url: str | None
    error_message: str | None
    created_at: datetime