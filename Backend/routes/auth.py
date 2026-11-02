
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from core import auth, config

logger = logging.getLogger("safezone.routes.auth")

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(max_length=200)
    password: str = Field(max_length=400)


def require_admin(request: Request) -> str:
    email = auth.read_session(request.cookies.get(auth.SESSION_COOKIE))
    if email is None:
        raise HTTPException(status_code=401, detail="Sign in to view this.")
    return email


@router.post("/api/auth/login")
def login(body: LoginRequest, request: Request, response: Response) -> Dict[str, Any]:
    try:
        email = auth.authenticate(body.email, body.password)
    except auth.AuthError as exc:
        logger.warning("Rejected a sign-in attempt: %s", exc)
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    token, max_age = auth.issue_session(email)

    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )

    logger.info("Signed in")
    return {"email": email, "expires_in": max_age}


@router.post("/api/auth/logout")
def logout(response: Response) -> Dict[str, Any]:
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"signed_out": True}


@router.get("/api/auth/me")
def me(request: Request) -> Dict[str, Any]:
    email = auth.read_session(request.cookies.get(auth.SESSION_COOKIE))
    return {
        "authenticated": email is not None,
        "email": email,
        "configured": auth.is_configured(),
    }


__all__ = ["router", "require_admin", "LoginRequest"]
