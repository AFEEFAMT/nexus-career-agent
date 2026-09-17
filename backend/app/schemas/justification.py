from pydantic import BaseModel, Field


class MatchJustification(BaseModel):
    job_id: str
    justification: str = Field(
        description=(
            "One concise sentence explaining why "
            "the candidate matches this job"
        )
    )


class MatchJustificationBatch(BaseModel):
    matches: list[MatchJustification]