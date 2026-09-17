from google import genai

from app.core.config import settings
from app.schemas.justification import (
    MatchJustificationBatch,
)
from app.services.extraction import (
    ExtractionError,
    ExtractionRateLimitError,
)


class MatchJustificationService:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        self.model = settings.GEMINI_MODEL

    @staticmethod
    def _is_rate_limit_error(
        exc: Exception,
    ) -> bool:
        message = str(exc).lower()

        return (
            getattr(exc, "code", None) == 429
            or getattr(exc, "status_code", None) == 429
            or "error code: 429" in message
            or "too_many_requests" in message
            or "quota exceeded" in message
            or "rate limit" in message
        )

    def generate(
        self,
        resume_text: str,
        jobs: list,
    ) -> MatchJustificationBatch:
        job_sections = []

        for job in jobs:
            job_sections.append(
                f"""
JOB ID: {job.id}
TITLE: {job.title}
DESCRIPTION:
{job.raw_text[:6000]}
""".strip()
            )

        jobs_text = "\n\n---\n\n".join(
            job_sections
        )

        prompt = f"""
You are explaining semantic job matches.

For every job below, write exactly one short,
specific sentence explaining why the candidate
could match that job.

Rules:
- Use only evidence from the resume and job listing.
- Do not invent skills or experience.
- Mention concrete overlapping skills or experience.
- Do not exaggerate the candidate's suitability.
- Return one result for every supplied JOB ID.

RESUME:
{resume_text}

JOBS:
{jobs_text}
""".strip()

        try:
            interaction = (
                self.client.interactions.create(
                    model=self.model,
                    input=prompt,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": (
                            MatchJustificationBatch
                            .model_json_schema()
                        ),
                    },
                )
            )

        except Exception as exc:
            if self._is_rate_limit_error(
                exc
            ):
                raise ExtractionRateLimitError(
                    "Gemini rate limit reached."
                ) from exc

            raise ExtractionError(
                f"Could not generate match "
                f"justifications: {exc}"
            ) from exc

        if not interaction.output_text:
            raise ExtractionError(
                "Gemini returned an empty justification response."
            )

        return (
            MatchJustificationBatch
            .model_validate_json(
                interaction.output_text
            )
        )