from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Job, Match, Resume
from app.services.embedding import (
    EmbeddingError,
    create_embedding,
)
from app.services.justification import (
    MatchJustificationService,
)


class MatchingError(Exception):
    pass


def ensure_job_embeddings(
    db: Session,
) -> int:
    jobs = db.scalars(
        select(Job).where(
            Job.is_active.is_(True),
            Job.embedding.is_(None),
        )
    ).all()

    embedded_count = 0

    for job in jobs:
        try:
            embedding_text = (
                f"{job.title}\n\n"
                f"{job.raw_text}"
            )

            job.embedding = create_embedding(
                embedding_text
            )

            db.commit()
            embedded_count += 1

        except EmbeddingError:
            db.rollback()

    return embedded_count


def generate_matches(
    db: Session,
    user_id,
    resume: Resume,
    limit: int = 10,
) -> tuple[list[Match], int]:
    if resume.embedding is None:
        raise MatchingError(
            "Resume does not have an embedding."
        )

    embedded_count = ensure_job_embeddings(
        db
    )

    distance = (
        Job.embedding.cosine_distance(
            resume.embedding
        )
        .label("distance")
    )

    rows = db.execute(
        select(
            Job,
            distance,
        )
        .where(
            Job.is_active.is_(True),
            Job.embedding.is_not(None),
        )
        .order_by(
            distance
        )
        .limit(
            limit
        )
    ).all()

    if not rows:
        raise MatchingError(
            "No jobs with embeddings are available."
        )

    db.execute(
        delete(Match).where(
            Match.user_id == user_id,
            Match.resume_id == resume.id,
        )
    )

    matches = []

    for job, cosine_distance in rows:
        similarity = (
            1.0 - float(
                cosine_distance
            )
        )

        similarity = max(
            0.0,
            min(
                1.0,
                similarity,
            ),
        )

        score = round(
            similarity * 100,
            2,
        )

        match = Match(
            user_id=user_id,
            resume_id=resume.id,
            job_id=job.id,
            score=score,
            justification=None,
        )

        db.add(match)
        matches.append(match)

    db.commit()

    for match in matches:
        db.refresh(match)

    return matches, embedded_count
def generate_match_justifications(
    db: Session,
    resume: Resume,
    matches: list[Match],
) -> int:
    if not matches:
        return 0

    job_ids = [
        match.job_id
        for match in matches
    ]

    jobs = db.scalars(
        select(Job).where(
            Job.id.in_(job_ids)
        )
    ).all()

    jobs_by_id = {
        job.id: job
        for job in jobs
    }

    ordered_jobs = [
        jobs_by_id[match.job_id]
        for match in matches
        if match.job_id in jobs_by_id
    ]

    service = (
        MatchJustificationService()
    )

    result = service.generate(
        resume_text=resume.raw_text,
        jobs=ordered_jobs,
    )

    justification_by_job = {
        item.job_id: item.justification
        for item in result.matches
    }

    updated_count = 0

    for match in matches:
        justification = (
            justification_by_job.get(
                str(match.job_id)
            )
        )

        if justification is None:
            continue

        match.justification = justification
        updated_count += 1

    db.commit()

    return updated_count