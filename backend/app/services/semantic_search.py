from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job
from app.services.embedding import create_embedding


def semantic_search_jobs(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[tuple[Job, float]]:
    query = query.strip()

    if not query:
        return []

    limit = max(
        1,
        min(limit, 20),
    )

    query_embedding = create_embedding(
        query
    )

    distance = (
        Job.embedding.cosine_distance(
            query_embedding
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
        .order_by(distance)
        .limit(limit)
    ).all()

    results = []

    for job, cosine_distance in rows:
        similarity = (
            1.0
            - float(
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

        results.append(
            (
                job,
                round(
                    similarity * 100,
                    2,
                ),
            )
        )

    return results