from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job, JobChange, ScrapeRun
from app.utils.deduplication import (
    make_content_hash,
    make_dedup_key,
)


def validate_scraped_job(
    item: dict,
    expected_source: str,
) -> None:
    required_fields = [
        "source_url",
        "title",
        "raw_text",
    ]

    for field in required_fields:
        value = item.get(field)

        if value is None or not str(value).strip():
            raise ValueError(
                f"Scraped job is missing {field}"
            )

    source = str(
        item.get("source", expected_source)
    ).strip().lower()

    if source != expected_source.strip().lower():
        raise ValueError(
            f"Unexpected source '{source}'"
        )

    title = str(
        item["title"]
    ).strip()

    raw_text = str(
        item["raw_text"]
    ).strip()

    if len(title) < 2:
        raise ValueError(
            "Scraped job title is too short"
        )

    if len(raw_text) < 300:
        raise ValueError(
            "Scraped job content is too short"
        )

    suspicious_phrases = [
        "access denied",
        "verify you are human",
        "captcha",
        "cloudflare ray id",
        "temporarily unavailable",
    ]

    lowered_text = raw_text.lower()

    for phrase in suspicious_phrases:
        if phrase in lowered_text:
            raise ValueError(
                f"Scraped page looks invalid: {phrase}"
            )


def ingest_jobs(
    db: Session,
    source_name: str,
    scraped_jobs: list[dict],
) -> dict:
    run = ScrapeRun(
        source=source_name,
        status="running",
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        now = datetime.now(timezone.utc)

        prepared_jobs = {}

        for item in scraped_jobs:
            validate_scraped_job(
                item=item,
                expected_source=source_name,
            )

            dedup_key = make_dedup_key(
                source=source_name,
                source_url=item["source_url"],
                external_id=item.get(
                    "external_id"
                ),
            )

            content_hash = make_content_hash(
                item["raw_text"]
            )

            prepared_jobs[dedup_key] = {
                **item,
                "source": source_name,
                "dedup_key": dedup_key,
                "content_hash": content_hash,
            }

        existing_jobs = {}

        if prepared_jobs:
            statement = select(
                Job
            ).where(
                Job.dedup_key.in_(
                    list(
                        prepared_jobs.keys()
                    )
                )
            )

            existing_jobs = {
                job.dedup_key: job
                for job in db.scalars(
                    statement
                ).all()
            }

        new_count = 0
        updated_count = 0
        unchanged_count = 0

        for dedup_key, item in prepared_jobs.items():
            existing_job = existing_jobs.get(
                dedup_key
            )

            scraped_at = item.get(
                "scraped_at",
                now,
            )

            if existing_job is None:
                db.add(
                    Job(
                        source=source_name,
                        external_id=item.get(
                            "external_id"
                        ),
                        source_url=item[
                            "source_url"
                        ],
                        dedup_key=dedup_key,
                        title=item["title"],
                        raw_text=item["raw_text"],
                        content_hash=item[
                            "content_hash"
                        ],
                        scraped_at=scraped_at,
                        last_seen_at=now,
                        is_active=True,
                    )
                )

                new_count += 1
                continue

            existing_job.last_seen_at = now
            existing_job.scraped_at = scraped_at
            existing_job.is_active = True

            if (
                existing_job.content_hash
                == item["content_hash"]
            ):
                unchanged_count += 1
                continue

            db.add(
                JobChange(
                    job_id=existing_job.id,
                    field_name="content_hash",
                    old_value=existing_job.content_hash,
                    new_value=item["content_hash"],
                )
            )

            existing_job.title = item["title"]
            existing_job.source_url = item[
                "source_url"
            ]
            existing_job.raw_text = item[
                "raw_text"
            ]
            existing_job.content_hash = item[
                "content_hash"
            ]
            existing_job.embedding = None

            updated_count += 1

        run.found_count = len(
            prepared_jobs
        )
        run.new_count = new_count
        run.updated_count = updated_count
        run.status = "success"
        run.completed_at = now

        db.commit()

        return {
            "found_count": len(
                prepared_jobs
            ),
            "new_count": new_count,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
        }

    except Exception as exc:
        db.rollback()

        failed_run = db.get(
            ScrapeRun,
            run.id,
        )

        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.error = str(exc)
            failed_run.completed_at = (
                datetime.now(
                    timezone.utc
                )
            )

            db.commit()

        raise