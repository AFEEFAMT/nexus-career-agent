from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import (
    and_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
)
from app.db.database import get_db
from app.db.models import (
    Job,
    Match,
    Resume,
    Shortlist,
    User,
)
from app.schemas.shortlist import (
    ShortlistResponse,
)


router = APIRouter(
    prefix="/shortlist",
    tags=["Shortlist"],
)


def build_response(
    shortlist: Shortlist,
    job: Job,
    match_score: float | None = None,
) -> ShortlistResponse:
    return ShortlistResponse(
        shortlist_id=shortlist.id,
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
        source=job.source,
        source_url=job.source_url,
        match_score=(
            round(
                float(match_score),
                2,
            )
            if match_score
            is not None
            else None
        ),
        created_at=(
            shortlist.created_at
        ),
    )


def get_latest_resume_id(
    db: Session,
    user_id: UUID,
) -> UUID | None:
    return db.scalar(
        select(Resume.id)
        .where(
            Resume.user_id
            == user_id
        )
        .order_by(
            Resume.created_at.desc()
        )
        .limit(1)
    )


@router.post(
    "/{job_id}",
    response_model=ShortlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_to_shortlist(
    job_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> ShortlistResponse:
    job = db.get(
        Job,
        job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Job not found.",
        )

    existing = db.scalar(
        select(Shortlist).where(
            Shortlist.user_id
            == current_user.id,
            Shortlist.job_id
            == job_id,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Job is already in "
                "your shortlist."
            ),
        )

    shortlist = Shortlist(
        user_id=current_user.id,
        job_id=job_id,
    )

    try:
        db.add(shortlist)
        db.commit()
        db.refresh(shortlist)

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Job is already in "
                "your shortlist."
            ),
        ) from exc

    latest_resume_id = (
        get_latest_resume_id(
            db=db,
            user_id=current_user.id,
        )
    )

    match_score = None

    if latest_resume_id:
        match_score = db.scalar(
            select(Match.score).where(
                Match.user_id
                == current_user.id,
                Match.resume_id
                == latest_resume_id,
                Match.job_id
                == job_id,
            )
        )

    return build_response(
        shortlist=shortlist,
        job=job,
        match_score=match_score,
    )


@router.get(
    "",
    response_model=list[
        ShortlistResponse
    ],
)
def get_my_shortlist(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> list[ShortlistResponse]:
    latest_resume_id = (
        get_latest_resume_id(
            db=db,
            user_id=current_user.id,
        )
    )

    rows = db.execute(
        select(
            Shortlist,
            Job,
            Match.score,
        )
        .join(
            Job,
            Shortlist.job_id
            == Job.id,
        )
        .outerjoin(
            Match,
            and_(
                Match.job_id
                == Job.id,
                Match.user_id
                == current_user.id,
                Match.resume_id
                == latest_resume_id,
            ),
        )
        .where(
            Shortlist.user_id
            == current_user.id
        )
        .order_by(
            Shortlist.created_at.desc()
        )
    ).all()

    return [
        build_response(
            shortlist=shortlist,
            job=job,
            match_score=match_score,
        )
        for (
            shortlist,
            job,
            match_score,
        ) in rows
    ]


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_from_shortlist(
    job_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> Response:
    shortlist = db.scalar(
        select(Shortlist).where(
            Shortlist.user_id
            == current_user.id,
            Shortlist.job_id
            == job_id,
        )
    )

    if shortlist is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Job is not in "
                "your shortlist."
            ),
        )

    db.delete(shortlist)
    db.commit()

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )