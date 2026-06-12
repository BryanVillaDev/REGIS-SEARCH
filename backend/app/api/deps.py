from fastapi import Depends, Header, HTTPException, Request, status

from app.core.security import decode_access_token
from app.services.users import UserRecord, get_user_by_username


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def get_current_user(authorization: str | None = Header(default=None)) -> UserRecord:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido",
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    user = get_user_by_username(username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o inexistente",
        )
    return user


def require_admin(user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes",
        )
    return user
