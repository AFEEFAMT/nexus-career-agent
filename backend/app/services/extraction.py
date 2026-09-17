import re
from datetime import datetime, time, timezone
from time import sleep

from google import genai
from google.genai import errors, types
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ExtractionCache, Job
from app.schemas.job import JobExtraction
from app.utils.deduplication import make_content_hash


class ExtractionError(Exception):
    pass


class ExtractionRateLimitError(ExtractionError):
    def __init__(
        self,
        message: str,
        retry_after_seconds: int | None = None,
    ):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class JobExtractionService:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        models = [
            settings.GEMINI_MODEL,
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
        ]

        self.models = list(
            dict.fromkeys(models)
        )

    @staticmethod
    def _build_prompt(
        raw_text: str,
    ) -> str:
        return f"""
Extract structured information from the job listing below.

Rules:
- Use only information explicitly present in the listing.
- Do not guess missing information.
- Preserve the company name exactly as stated.
- Preserve the job location as stated.
- Extract explicitly listed required skills.
- Preserve the stated experience requirement.
- Keep compensation exactly as stated.
- Set remote_ok to true only if remote work is explicitly allowed.
- Set remote_ok to false only if on-site work is explicitly required.
- Otherwise set remote_ok to null.
- Return the deadline only when explicitly stated.
- Use null for missing scalar fields.
- Use an empty list if no required skills are stated.

JOB LISTING:

{raw_text}
""".strip()

    @staticmethod
    def _get_retry_seconds(
        message: str,
    ) -> int | None:
        match = re.search(
            r"retry in\s+([\d.]+)s",
            message,
            re.IGNORECASE,
        )

        if match is None:
            return None

        return int(
            float(match.group(1))
        ) + 1

    @staticmethod
    def _status_code(
        exc: Exception,
    ):
        return (
            getattr(
                exc,
                "code",
                None,
            )
            or getattr(
                exc,
                "status_code",
                None,
            )
        )

    @classmethod
    def _is_rate_limit_error(
        cls,
        exc: Exception,
    ) -> bool:
        message = str(exc).lower()

        code = cls._status_code(
            exc
        )

        return (
            code == 429
            or "429" in message
            or "too_many_requests" in message
            or "quota exceeded" in message
            or "rate limit" in message
        )

    @classmethod
    def _is_temporary_error(
        cls,
        exc: Exception,
    ) -> bool:
        message = str(exc).lower()

        code = cls._status_code(
            exc
        )

        return (
            code == 503
            or "503" in message
            or "unavailable" in message
            or "high demand" in message
            or "temporarily unavailable" in message
            or "timeout" in message
            or "timed out" in message
        )

    @classmethod
    def _is_model_error(
        cls,
        exc: Exception,
    ) -> bool:
        message = str(exc).lower()

        code = cls._status_code(
            exc
        )

        return (
            code == 404
            or "model not found" in message
            or "model_not_found" in message
        )

    def _call_single_model(
        self,
        model: str,
        raw_text: str,
    ) -> JobExtraction:
        response = (
            self.client.models.generate_content(
                model=model,
                contents=self._build_prompt(
                    raw_text
                ),
                config=types.GenerateContentConfig(
                    response_mime_type=(
                        "application/json"
                    ),
                    response_schema=(
                        JobExtraction
                    ),
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )
        )

        parsed = getattr(
            response,
            "parsed",
            None,
        )

        if parsed is not None:
            if isinstance(
                parsed,
                JobExtraction,
            ):
                return parsed

            return (
                JobExtraction
                .model_validate(parsed)
            )

        output = (
            response.text
            or ""
        ).strip()

        if not output:
            raise ExtractionError(
                "Gemini returned an empty response."
            )

        return (
            JobExtraction
            .model_validate_json(
                output
            )
        )

    def _call_model(
        self,
        raw_text: str,
    ) -> tuple[
        JobExtraction,
        str,
    ]:
        last_error = None

        rate_limit_count = 0
        retry_after_seconds = None

        for model in self.models:
            try:
                print(
                    f"Trying extraction model: {model}"
                )

                result = (
                    self._call_single_model(
                        model=model,
                        raw_text=raw_text,
                    )
                )

                print(
                    f"Extraction succeeded with: {model}"
                )

                return (
                    result,
                    model,
                )

            except Exception as exc:
                last_error = exc

                if self._is_rate_limit_error(
                    exc
                ):
                    rate_limit_count += 1

                    retry_seconds = (
                        self._get_retry_seconds(
                            str(exc)
                        )
                    )

                    if retry_seconds is not None:
                        retry_after_seconds = (
                            retry_seconds
                        )

                    print(
                        f"{model} rate limited. "
                        "Trying fallback..."
                    )

                    continue

                if self._is_temporary_error(
                    exc
                ):
                    print(
                        f"{model} unavailable. "
                        "Trying fallback..."
                    )

                    continue

                if self._is_model_error(
                    exc
                ):
                    print(
                        f"{model} not available. "
                        "Trying fallback..."
                    )

                    continue

                if isinstance(
                    exc,
                    ValidationError,
                ):
                    print(
                        f"{model} returned invalid "
                        "structured output. "
                        "Trying fallback..."
                    )

                    continue

                if isinstance(
                    exc,
                    ValueError,
                ):
                    print(
                        f"{model} returned malformed "
                        "output. Trying fallback..."
                    )

                    continue

                if isinstance(
                    exc,
                    ExtractionError,
                ):
                    print(
                        f"{model} extraction failed: "
                        f"{exc}. Trying fallback..."
                    )

                    continue

                if isinstance(
                    exc,
                    errors.APIError,
                ):
                    print(
                        f"{model} API error. "
                        "Trying fallback..."
                    )

                    continue

                print(
                    f"{model} unexpected failure: "
                    f"{exc}. Trying fallback..."
                )

        if (
            rate_limit_count
            == len(self.models)
        ):
            raise ExtractionRateLimitError(
                "All Gemini extraction models "
                "are currently rate limited.",
                retry_after_seconds=(
                    retry_after_seconds
                ),
            )

        raise ExtractionError(
            "All Gemini extraction models failed. "
            f"Last error: {last_error}"
        )

    def extract(
        self,
        db: Session,
        raw_text: str,
        max_attempts: int = 2,
    ) -> tuple[
        JobExtraction,
        bool,
    ]:
        raw_hash = make_content_hash(
            raw_text
        )

        cached = db.scalar(
            select(
                ExtractionCache
            ).where(
                ExtractionCache.raw_hash
                == raw_hash
            )
        )

        if cached is not None:
            try:
                result = (
                    JobExtraction
                    .model_validate(
                        cached.extracted_json
                    )
                )

                return (
                    result,
                    True,
                )

            except ValidationError:
                db.delete(
                    cached
                )

                db.commit()

        last_error = None

        for attempt in range(
            1,
            max_attempts + 1,
        ):
            try:
                (
                    result,
                    model_used,
                ) = self._call_model(
                    raw_text
                )

                cache_entry = (
                    ExtractionCache(
                        raw_hash=raw_hash,
                        extracted_json=(
                            result.model_dump(
                                mode="json"
                            )
                        ),
                        model_name=(
                            model_used
                        ),
                    )
                )

                db.add(
                    cache_entry
                )

                db.commit()

                return (
                    result,
                    False,
                )

            except ExtractionRateLimitError:
                raise

            except (
                ValidationError,
                ExtractionError,
                ValueError,
            ) as exc:
                last_error = exc

                if (
                    attempt
                    < max_attempts
                ):
                    sleep(2)

        raise ExtractionError(
            "Job extraction failed after "
            f"{max_attempts} attempts: "
            f"{last_error}"
        )

    def enrich_job(
        self,
        db: Session,
        job: Job,
    ) -> tuple[
        JobExtraction,
        bool,
    ]:
        (
            result,
            from_cache,
        ) = self.extract(
            db=db,
            raw_text=job.raw_text,
        )

        job.title = result.title
        job.company = result.company
        job.location = result.location
        job.remote_ok = (
            result.remote_ok
        )
        job.stipend = result.stipend
        job.required_skills = (
            result.required_skills
            or []
        )
        job.experience_level = (
            result.experience_level
        )

        if result.deadline is None:
            job.deadline = None

        else:
            job.deadline = (
                datetime.combine(
                    result.deadline,
                    time.min,
                    tzinfo=timezone.utc,
                )
            )

        db.commit()
        db.refresh(job)

        return (
            result,
            from_cache,
        )