from time import sleep
from uuid import UUID

from google import genai
from google.genai import types
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Job,
    Match,
    Resume,
    Shortlist,
)


class AgentError(Exception):
    pass


class AgentRateLimitError(AgentError):
    pass


class AgentUnavailableError(AgentError):
    pass


class NexusAgent:
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

        code = getattr(
            exc,
            "code",
            None,
        )

        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        return (
            code == 429
            or status_code == 429
            or "error code: 429" in message
            or "too_many_requests" in message
            or "quota exceeded" in message
            or "rate limit" in message
        )

    @staticmethod
    def _is_unavailable_error(
        exc: Exception,
    ) -> bool:
        message = str(exc).lower()

        code = getattr(
            exc,
            "code",
            None,
        )

        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        return (
            code == 503
            or status_code == 503
            or "503 unavailable" in message
            or "high demand" in message
            or "'status': 'unavailable'" in message
            or '"status": "unavailable"' in message
        )

    def ask(
        self,
        db: Session,
        user_id: UUID,
        message: str,
    ) -> tuple[str, list[str]]:
        tools_used = []

        def record_tool(
            tool_name: str,
        ) -> None:
            if tool_name not in tools_used:
                tools_used.append(
                    tool_name
                )

        def get_top_matches(
            limit: int = 5,
        ) -> list[dict]:
            """Get the authenticated user's highest-scoring saved job matches."""

            record_tool(
                "get_top_matches"
            )

            limit = max(
                1,
                min(limit, 10),
            )

            resume = db.scalar(
                select(Resume)
                .where(
                    Resume.user_id
                    == user_id
                )
                .order_by(
                    Resume.created_at.desc()
                )
                .limit(1)
            )

            if resume is None:
                return [
                    {
                        "message": (
                            "The user has not uploaded "
                            "a resume."
                        )
                    }
                ]

            rows = db.execute(
                select(
                    Match,
                    Job,
                )
                .join(
                    Job,
                    Match.job_id == Job.id,
                )
                .where(
                    Match.user_id
                    == user_id,
                    Match.resume_id
                    == resume.id,
                )
                .order_by(
                    Match.score.desc()
                )
                .limit(limit)
            ).all()

            return [
                {
                    "job_id": str(
                        job.id
                    ),
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "score": float(
                        match.score
                    ),
                    "justification": (
                        match.justification
                    ),
                    "source": job.source,
                    "source_url": (
                        job.source_url
                    ),
                }
                for match, job in rows
            ]

        def search_jobs(
            query: str,
            limit: int = 5,
        ) -> list[dict]:
            """Search active saved jobs by title, company, location, or description."""

            record_tool(
                "search_jobs"
            )

            query = query.strip()

            if not query:
                return []

            limit = max(
                1,
                min(limit, 10),
            )

            search_pattern = (
                f"%{query}%"
            )

            jobs = db.scalars(
                select(Job)
                .where(
                    Job.is_active.is_(
                        True
                    ),
                    or_(
                        Job.title.ilike(
                            search_pattern
                        ),
                        Job.company.ilike(
                            search_pattern
                        ),
                        Job.location.ilike(
                            search_pattern
                        ),
                        Job.raw_text.ilike(
                            search_pattern
                        ),
                    ),
                )
                .order_by(
                    Job.created_at.desc()
                )
                .limit(limit)
            ).all()

            return [
                {
                    "job_id": str(
                        job.id
                    ),
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "remote_ok": (
                        job.remote_ok
                    ),
                    "stipend": (
                        job.stipend
                    ),
                    "required_skills": (
                        job.required_skills
                        or []
                    ),
                    "experience_level": (
                        job.experience_level
                    ),
                    "source": job.source,
                    "source_url": (
                        job.source_url
                    ),
                }
                for job in jobs
            ]

        def get_shortlist() -> list[dict]:
            """Get jobs saved in the authenticated user's personal shortlist."""

            record_tool(
                "get_shortlist"
            )

            rows = db.execute(
                select(
                    Shortlist,
                    Job,
                )
                .join(
                    Job,
                    Shortlist.job_id
                    == Job.id,
                )
                .where(
                    Shortlist.user_id
                    == user_id
                )
                .order_by(
                    Shortlist.created_at.desc()
                )
            ).all()

            return [
                {
                    "job_id": str(
                        job.id
                    ),
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "source": job.source,
                    "source_url": (
                        job.source_url
                    ),
                    "saved_at": (
                        shortlist
                        .created_at
                        .isoformat()
                    ),
                }
                for shortlist, job in rows
            ]

        def get_job_details(
            job_id: str,
        ) -> dict:
            """Get detailed information for one saved job using its UUID."""

            record_tool(
                "get_job_details"
            )

            try:
                parsed_id = UUID(
                    job_id
                )

            except ValueError:
                return {
                    "error": "Invalid job ID."
                }

            job = db.get(
                Job,
                parsed_id,
            )

            if job is None:
                return {
                    "error": "Job not found."
                }

            return {
                "job_id": str(
                    job.id
                ),
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "remote_ok": (
                    job.remote_ok
                ),
                "stipend": job.stipend,
                "required_skills": (
                    job.required_skills
                    or []
                ),
                "experience_level": (
                    job.experience_level
                ),
                "deadline": (
                    job.deadline.isoformat()
                    if job.deadline
                    else None
                ),
                "source": job.source,
                "source_url": (
                    job.source_url
                ),
                "description": (
                    job.raw_text[:5000]
                ),
            }

        prompt = f"""
You are Nexus, a career intelligence assistant.

You have access to the authenticated user's saved career data
through database tools.

Rules:
- Use tools whenever the question depends on jobs, matches,
  or the user's shortlist.
- Never invent jobs, scores, skills, salaries, locations,
  deadlines, or saved data.
- If information is unavailable, say so clearly.
- Match scores represent semantic similarity, not hiring probability.
- Do not claim that the user will get a job.
- Use get_job_details when more information about a specific job
  is required.
- Keep answers concise, useful, and based on the tool results.

USER QUESTION:
{message}
""".strip()

        response = None

        for attempt in range(3):
            try:
                response = (
                    self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[
                                get_top_matches,
                                search_jobs,
                                get_shortlist,
                                get_job_details,
                            ],
                            temperature=0.2,
                        ),
                    )
                )

                break

            except Exception as exc:
                if self._is_rate_limit_error(
                    exc
                ):
                    raise AgentRateLimitError(
                        "Gemini rate limit reached. "
                        "Please try again shortly."
                    ) from exc

                if self._is_unavailable_error(
                    exc
                ):
                    if attempt < 2:
                        sleep(
                            2 ** attempt
                        )
                        continue

                    raise AgentUnavailableError(
                        "Gemini is temporarily unavailable "
                        "because of high demand. "
                        "Please try again shortly."
                    ) from exc

                raise AgentError(
                    f"Agent request failed: {exc}"
                ) from exc

        if response is None:
            raise AgentError(
                "Agent did not receive a response."
            )

        try:
            answer = response.text

        except Exception as exc:
            raise AgentError(
                "Could not read the agent response."
            ) from exc

        if not answer:
            raise AgentError(
                "Agent returned an empty response."
            )

        return (
            answer,
            tools_used,
        )