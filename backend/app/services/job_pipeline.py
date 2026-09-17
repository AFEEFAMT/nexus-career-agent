from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job
from app.services.embedding import (
    EmbeddingError,
    create_embedding,
)
from app.services.extraction import (
    ExtractionError,
    ExtractionRateLimitError,
    JobExtractionService,
)
from app.services.ingestion import ingest_jobs
from app.services.scraper.base import BaseScraper
from app.utils.deduplication import make_dedup_key


def run_job_pipeline(
    db: Session,
    scraper: BaseScraper,
) -> dict:
    scraped_jobs = scraper.scrape()

    ingestion_result = ingest_jobs(
        db=db,
        source_name=scraper.source_name,
        scraped_jobs=scraped_jobs,
    )

    job_keys = {}

    for item in scraped_jobs:
        dedup_key = make_dedup_key(
            source=scraper.source_name,
            source_url=item["source_url"],
            external_id=item.get("external_id"),
        )

        job_keys[dedup_key] = item

    stored_jobs = db.scalars(
        select(Job).where(
            Job.dedup_key.in_(
                list(job_keys.keys())
            )
        )
    ).all()

    jobs_by_key = {
        job.dedup_key: job
        for job in stored_jobs
    }

    embedded_count = 0
    embedding_failed_count = 0
    embedding_errors = []

    for job in stored_jobs:
        if job.embedding is not None:
            continue

        try:
            embedding_text = (
                f"{job.title}\n\n"
                f"{job.raw_text}"
            )

            job.embedding = create_embedding(
                embedding_text
            )

            db.commit()
            db.refresh(job)

            embedded_count += 1

        except EmbeddingError as exc:
            db.rollback()

            embedding_failed_count += 1

            embedding_errors.append(
                {
                    "source_url": job.source_url,
                    "error": str(exc),
                }
            )

    extraction_service = JobExtractionService()

    enriched_count = 0
    cache_hits = 0
    extraction_failed_count = 0
    extraction_errors = []

    for dedup_key, item in job_keys.items():
        job = jobs_by_key.get(
            dedup_key
        )

        if job is None:
            extraction_failed_count += 1

            extraction_errors.append(
                {
                    "source_url": item["source_url"],
                    "error": (
                        "Stored job could not be found "
                        "after ingestion."
                    ),
                }
            )

            continue

        try:
            _, from_cache = (
                extraction_service.enrich_job(
                    db=db,
                    job=job,
                )
            )

            enriched_count += 1

            if from_cache:
                cache_hits += 1

        except ExtractionRateLimitError as exc:
            db.rollback()

            extraction_failed_count += 1

            extraction_errors.append(
                {
                    "source_url": item["source_url"],
                    "error": str(exc),
                }
            )

            return {
                **ingestion_result,
                "embedded_count": embedded_count,
                "embedding_failed_count": (
                    embedding_failed_count
                ),
                "embedding_errors": embedding_errors,
                "enriched_count": enriched_count,
                "cache_hits": cache_hits,
                "extraction_failed_count": (
                    extraction_failed_count
                ),
                "extraction_errors": extraction_errors,
                "rate_limited": True,
                "retry_after_seconds": (
                    exc.retry_after_seconds
                ),
            }

        except ExtractionError as exc:
            db.rollback()

            extraction_failed_count += 1

            extraction_errors.append(
                {
                    "source_url": item["source_url"],
                    "error": str(exc),
                }
            )

    return {
        **ingestion_result,
        "embedded_count": embedded_count,
        "embedding_failed_count": embedding_failed_count,
        "embedding_errors": embedding_errors,
        "enriched_count": enriched_count,
        "cache_hits": cache_hits,
        "extraction_failed_count": (
            extraction_failed_count
        ),
        "extraction_errors": extraction_errors,
        "rate_limited": False,
        "retry_after_seconds": None,
    }