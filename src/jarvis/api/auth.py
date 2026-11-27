"""Authentication routes: login, token, user info."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.auth import (
    authenticate_user,
    create_tokens_for_user,
    get_current_user,
    require_superuser,
)
from jarvis.core.exceptions import AuthenticationError
from jarvis.core.logging import get_logger
from jarvis.db import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    user_pwd: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_superuser: bool


@router.post("/login", response_model=LoginResponse, summary="Authenticate and obtain tokens")
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> LoginResponse:
    """Authenticate a user and return access/refresh tokens.

    Valid credentials return a bearer token pair. Invalid credentials
    return 401 without revealing whether the username exists.
    """
    try:
        user = await authenticate_user(
            session, request.username, request.user_pwd
        )
    except AuthenticationError:
        # Return generic failure to avoid user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    tokens = create_tokens_for_user(user)
    logger.info("User authenticated", extra={"user_id": str(user.id)})
    return LoginResponse(**tokens)


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    user = await get_current_user(session, authorization)
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )


@router.post(
    "/superuser-check",
    summary="Verify superuser access (admin only)",
)
async def superuser_check(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    authorization: str | None = None,
) -> dict[str, str]:
    """Require superuser access. Returns success if authorized."""
    user = await get_current_user(session, authorization)
    require_superuser(user)
    return {"status": "authorized", "user_id": str(user.id)}
