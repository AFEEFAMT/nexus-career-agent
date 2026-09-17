from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
)
from app.db.database import get_db
from app.db.models import (
    Job,
    Match,
    Resume,
    User,
)
from app.schemas.match import (
    JobMatchResponse,
    MatchGenerationResponse,
)
from app.services.extraction import (
    ExtractionError,
    ExtractionRateLimitError,
)
from app.services.matching import (
    MatchingError,
    generate_matches,
    generate_match_justifications,
)

router = APIRouter(
    prefix="/matches",
    tags=["Matches"],
)


def build_match_response(
    match: Match,
    job: Job,
) -> JobMatchResponse:
    return JobMatchResponse(
        match_id=match.id,
        job_id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        remote_ok=job.remote_ok,
        stipend=job.stipend,
        required_skills=(
            job.required_skills or []
        ),
        score=round(
            float(match.score),
            2,
        ),
        justification=match.justification,
        source=job.source,
        source_url=job.source_url,
    )


@router.post(
    "/{resume_id}/generate",
    response_model=MatchGenerationResponse,
)
def create_matches(
    resume_id: UUID,
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> MatchGenerationResponse:
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id
            == current_user.id,
        )
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    try:
        matches, embedded_count = (
            generate_matches(
                db=db,
                user_id=current_user.id,
                resume=resume,
                limit=limit,
            )
        )

    except MatchingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    job_ids = [
        match.job_id
        for match in matches
    ]

    jobs = db.scalars(
        select(Job).where(
            Job.id.in_(
                job_ids
            )
        )
    ).all()

    jobs_by_id = {
        job.id: job
        for job in jobs
    }

    results = [
        build_match_response(
            match,
            jobs_by_id[
                match.job_id
            ],
        )
        for match in matches
        if match.job_id in jobs_by_id
    ]

    return MatchGenerationResponse(
        resume_id=resume.id,
        total_matches=len(
            results
        ),
        jobs_embedded=embedded_count,
        matches=results,
    )


@router.get(
    "/{resume_id}",
    response_model=list[JobMatchResponse],
)
def get_matches(
    resume_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> list[JobMatchResponse]:
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id
            == current_user.id,
        )
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

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
            == current_user.id,
            Match.resume_id
            == resume.id,
        )
        .order_by(
            Match.score.desc()
        )
    ).all()

    return [
        build_match_response(
            match,
            job,
        )
        for match, job in rows
    ]
@router.post(
    "/{resume_id}/justify",
    response_model=list[JobMatchResponse],
)
def justify_matches(
    resume_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> list[JobMatchResponse]:
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id
            == current_user.id,
        )
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    matches = db.scalars(
        select(Match)
        .where(
            Match.user_id
            == current_user.id,
            Match.resume_id
            == resume.id,
        )
        .order_by(
            Match.score.desc()
        )
    ).all()

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Generate matches before "
                "creating justifications."
            ),
        )

    try:
        generate_match_justifications(
            db=db,
            resume=resume,
            matches=matches,
        )

    except ExtractionRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

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
            == current_user.id,
            Match.resume_id
            == resume.id,
        )
        .order_by(
            Match.score.desc()
        )
    ).all()

    return [
        build_match_response(
            match,
            job,
        )
        for match, job in rows
    ]