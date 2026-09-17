from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
)
from app.db.database import get_db
from app.db.models import User
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
)
from app.services.agent import (
    AgentError,
    AgentRateLimitError,
    AgentUnavailableError,
    NexusAgent,
)


router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.post(
    "/chat",
    response_model=AgentChatResponse,
)
def chat_with_agent(
    data: AgentChatRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
) -> AgentChatResponse:
    agent = NexusAgent()

    try:
        answer, tools_used = agent.ask(
            db=db,
            user_id=current_user.id,
            message=data.message,
        )

    except AgentRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except AgentUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except AgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return AgentChatResponse(
        answer=answer,
        tools_used=tools_used,
    )