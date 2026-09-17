from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Resume, User
from app.schemas.resume import ResumeResponse
from app.services.pdf_service import (
    MAX_PDF_SIZE,
    PDFExtractionError,
)
from app.services.resume_processing import (
    process_resume,
)


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)


def build_resume_response(
    resume: Resume,
) -> ResumeResponse:
    return ResumeResponse(
        id=resume.id,
        filename=resume.filename,
        created_at=resume.created_at,
        text_length=len(resume.raw_text),
        embedding_dimension=len(
            resume.embedding
        ),
    )


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> ResumeResponse:
    filename = (
        file.filename
        or "resume.pdf"
    )

    if not filename.lower().endswith(
        ".pdf"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resumes are supported.",
        )

    pdf_bytes = await file.read(
        MAX_PDF_SIZE + 1
    )

    await file.close()

    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF must be smaller than 5 MB.",
        )

    try:
        processed = process_resume(
            pdf_bytes
        )

    except PDFExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume processing failed.",
        ) from exc

    resume = Resume(
        user_id=current_user.id,
        filename=filename,
        raw_text=processed.raw_text,
        embedding=processed.embedding,
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return build_resume_response(
        resume
    )


@router.get(
    "",
    response_model=list[ResumeResponse],
)
def list_my_resumes(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> list[ResumeResponse]:
    resumes = db.scalars(
        select(Resume)
        .where(
            Resume.user_id
            == current_user.id
        )
        .order_by(
            Resume.created_at.desc()
        )
    ).all()

    return [
        build_resume_response(
            resume
        )
        for resume in resumes
    ]


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
)
def get_my_resume(
    resume_id: UUID,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> ResumeResponse:
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

    return build_resume_response(
        resume
    )