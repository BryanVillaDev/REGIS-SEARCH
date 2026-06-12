from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models.schemas import LoginRequest, LoginResponse, UserPublic
from app.services.users import UserRecord, get_user_by_username

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    token = create_access_token(
        subject=user.username,
        extra={"uid": str(user.id), "role": user.role},
    )
    return LoginResponse(
        access_token=token,
        user=UserPublic.from_record(user),
    )


@router.get("/me", response_model=UserPublic)
def me(user: UserRecord = Depends(get_current_user)) -> UserPublic:
    return UserPublic.from_record(user)
