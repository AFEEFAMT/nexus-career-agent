from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
)
from app.db.database import get_db
from app.db.models import User
from app.schemas.job_search import (
    JobSearchResult,
    MetadataRefreshResponse,
)
from app.services.metadata_refresh import (
    refresh_top_match_metadata,
)
from app.services.semantic_search import (
    semantic_search_jobs,
)


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.get(
    "/search",
    response_model=list[
        JobSearchResult
    ],
)
def search_jobs(
    q: str = Query(
        min_length=1,
        max_length=500,
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=20,
    ),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> list[JobSearchResult]:
    results = semantic_search_jobs(
        db=db,
        query=q,
        limit=limit,
    )

    return [
        JobSearchResult(
            job_id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            remote_ok=job.remote_ok,
            stipend=job.stipend,
            required_skills=(
                job.required_skills
                or []
            ),
            experience_level=(
                job.experience_level
            ),
            deadline=job.deadline,
            source=job.source,
            source_url=(
                job.source_url
            ),
            semantic_score=score,
        )
        for job, score in results
    ]


@router.post(
    "/enrich-matches",
    response_model=(
        MetadataRefreshResponse
    ),
)
def enrich_matches(
    limit: int = Query(
        default=10,
        ge=1,
        le=20,
    ),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> MetadataRefreshResponse:
    result = (
        refresh_top_match_metadata(
            db=db,
            user_id=current_user.id,
            limit=limit,
        )
    )

    return MetadataRefreshResponse(
        **result
    )