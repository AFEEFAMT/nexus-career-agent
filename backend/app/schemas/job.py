from datetime import date

from pydantic import BaseModel, Field


class JobExtraction(BaseModel):
    title: str = Field(
        description="Exact job title from the listing"
    )

    company: str = Field(
        description="Company offering the job"
    )

    location: str | None = Field(
        default=None,
        description="Job location if explicitly stated"
    )

    remote_ok: bool | None = Field(
        default=None,
        description=(
            "True if remote work is explicitly allowed, "
            "false if the listing explicitly requires on-site work, "
            "otherwise null"
        ),
    )

    stipend: str | None = Field(
        default=None,
        description=(
            "Salary, stipend, or compensation exactly as stated"
        ),
    )

    required_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Skills explicitly required or strongly requested"
        ),
    )

    experience_level: str | None = Field(
        default=None,
        description="Required experience level if explicitly stated"
    )

    deadline: date | None = Field(
        default=None,
        description=(
            "Application deadline if explicitly stated, otherwise null"
        ),
    )