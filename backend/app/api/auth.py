"""用户注册、登录与当前用户信息接口。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.schemas.common import ApiResponse, success
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> ApiResponse[UserResponse]:
    user = register_user(db, payload)
    return success(UserResponse.model_validate(user), message="注册成功")


@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> ApiResponse[LoginResponse]:
    user, token, expires_in = authenticate_user(db, payload)
    data = LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )
    return success(data, message="登录成功")


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(current_user: User = Depends(get_current_user)) -> ApiResponse[UserResponse]:
    return success(UserResponse.model_validate(current_user))