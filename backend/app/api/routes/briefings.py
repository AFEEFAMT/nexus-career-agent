from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import (
    Briefing,
    User,
)
from app.schemas.briefing import BriefingResponse
from app.services.briefing import (
    process_briefing,
    refresh_tavus_status,
)


router = APIRouter(
    prefix="/briefings",
    tags=["Briefings"],
)


def build_briefing_response(
    briefing: Briefing,
) -> BriefingResponse:
    return BriefingResponse(
        id=briefing.id,
        briefing_type=briefing.briefing_type,
        script=briefing.script,
        provider=briefing.provider,
        status=briefing.status,
        media_url=briefing.media_url,
        error_message=briefing.error_message,
        created_at=briefing.created_at,
    )


@router.post(
    "/generate",
    response_model=BriefingResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_briefing(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> BriefingResponse:
    briefing = Briefing(
        user_id=current_user.id,
        briefing_type="video",
        status="queued",
    )

    db.add(briefing)
    db.commit()
    db.refresh(briefing)

    background_tasks.add_task(
        process_briefing,
        briefing.id,
    )

    return build_briefing_response(
        briefing
    )


@router.get(
    "",
    response_model=list[BriefingResponse],
)
def get_my_briefings(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> list[BriefingResponse]:
    briefings = db.scalars(
        select(Briefing)
        .where(
            Briefing.user_id
            == current_user.id
        )
        .order_by(
            Briefing.created_at.desc()
        )
    ).all()

    return [
        build_briefing_response(
            briefing
        )
        for briefing in briefings
    ]


@router.get(
    "/{briefing_id}",
    response_model=BriefingResponse,
)
def get_briefing(
    briefing_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> BriefingResponse:
    briefing = db.scalar(
        select(Briefing).where(
            Briefing.id
            == briefing_id,
            Briefing.user_id
            == current_user.id,
        )
    )

    if briefing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Briefing not found.",
        )

    if (
        briefing.provider == "tavus"
        and briefing.status
        in {
            "queued",
            "processing",
        }
    ):
        try:
            refresh_tavus_status(
                db=db,
                briefing=briefing,
            )

            db.refresh(
                briefing
            )

        except Exception as exc:
            # Do not fail the polling endpoint
            # just because Tavus status lookup
            # temporarily failed.
            briefing.error_message = (
                f"Video status check failed: {exc}"
            )

            db.commit()
            db.refresh(
                briefing
            )

    return build_briefing_response(
        briefing
    )