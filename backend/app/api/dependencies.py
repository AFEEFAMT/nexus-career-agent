from uuid import UUID

import jwt
from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.core.security import (
    decode_access_token,
)
from app.db.database import get_db
from app.db.models import User


bearer_scheme = HTTPBearer(
    auto_error=False
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(
        get_db
    ),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token.",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    if credentials is None:
        raise unauthorized

    try:
        user_id = UUID(
            decode_access_token(
                credentials.credentials
            )
        )

    except (
        jwt.InvalidTokenError,
        ValueError,
    ):
        raise unauthorized

    user = db.get(
        User,
        user_id,
    )

    if user is None:
        raise unauthorized

    return user