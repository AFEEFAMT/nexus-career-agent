from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Job,
    Match,
    Resume,
)
from app.services.extraction import (
    ExtractionError,
    ExtractionRateLimitError,
    JobExtractionService,
)


def _needs_enrichment(
    job: Job,
) -> bool:
    return (
        not job.company
        or not job.location
        or not job.required_skills
        or not job.experience_level
    )


def refresh_top_match_metadata(
    db: Session,
    user_id: UUID,
    limit: int = 10,
) -> dict:
    limit = max(
        1,
        min(limit, 20),
    )

    latest_resume = db.scalar(
        select(Resume)
        .where(
            Resume.user_id == user_id
        )
        .order_by(
            Resume.created_at.desc()
        )
        .limit(1)
    )

    if latest_resume is None:
        return {
            "attempted": 0,
            "enriched": 0,
            "skipped": 0,
            "rate_limited": False,
            "errors": [
                "No resume found."
            ],
        }

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
            Match.user_id == user_id,
            Match.resume_id
            == latest_resume.id,
        )
        .order_by(
            Match.score.desc()
        )
        .limit(limit)
    ).all()

    extractor = JobExtractionService()

    attempted = 0
    enriched = 0
    skipped = 0
    errors = []

    for _, job in rows:
        if not _needs_enrichment(job):
            skipped += 1
            continue

        attempted += 1

        try:
            extractor.enrich_job(
                db=db,
                job=job,
            )

            db.commit()
            db.refresh(job)

            enriched += 1

            print(
                "\nENRICHED:",
                job.title,
            )

            print(
                "  company:",
                job.company,
            )

            print(
                "  location:",
                job.location,
            )

            print(
                "  skills:",
                job.required_skills,
            )

            print(
                "  experience:",
                job.experience_level,
            )

        except ExtractionRateLimitError as exc:
            db.rollback()

            errors.append(
                str(exc)
            )

            print(
                "Gemini rate limit:",
                exc,
            )

            return {
                "attempted": attempted,
                "enriched": enriched,
                "skipped": skipped,
                "rate_limited": True,
                "errors": errors,
            }

        except ExtractionError as exc:
            db.rollback()

            message = (
                f"{job.title}: {exc}"
            )

            errors.append(
                message
            )

            print(
                "Extraction error:",
                message,
            )

        except Exception as exc:
            db.rollback()

            message = (
                f"{job.title}: {exc}"
            )

            errors.append(
                message
            )

            print(
                "Unexpected enrichment error:",
                message,
            )

    return {
        "attempted": attempted,
        "enriched": enriched,
        "skipped": skipped,
        "rate_limited": False,
        "errors": errors,
    }
