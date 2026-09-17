from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    status,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.staticfiles import (
    StaticFiles,
)
from sqlalchemy import text
from sqlalchemy.exc import (
    SQLAlchemyError,
)

from app.api.routes.agent import (
    router as agent_router,
)
from app.api.routes.auth import (
    router as auth_router,
)
from app.api.routes.briefings import (
    router as briefings_router,
)
from app.api.routes.matches import (
    router as matches_router,
)
from app.api.routes.resumes import (
    router as resumes_router,
)
from app.api.routes.shortlists import (
    router as shortlist_router,
)
from app.api.routes.jobs import (
    router as jobs_router,
)
from app.core.config import settings
from app.db.database import engine


app = FastAPI(
    title="Nexus API",
    description=(
        "Autonomous Career Intelligence Agent"
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


generated_dir = (
    Path(__file__).resolve().parents[1]
    / "generated"
)

generated_dir.mkdir(
    parents=True,
    exist_ok=True,
)


app.mount(
    "/media",
    StaticFiles(
        directory=str(
            generated_dir
        )
    ),
    name="media",
)


app.include_router(
    auth_router
)

app.include_router(
    resumes_router
)

app.include_router(
    matches_router
)

app.include_router(
    shortlist_router
)

app.include_router(
    agent_router
)

app.include_router(
    briefings_router
)

app.include_router(
    jobs_router
)

@app.get("/")
def root():
    return {
        "message": (
            "Nexus API is running"
        )
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        return {
            "status": "ok",
            "database": "connected",
        }

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail="Database unavailable",
        ) from exc