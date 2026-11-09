"""教师端写作任务管理接口。"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.writing_task import TaskCreate, TaskResponse, TaskUpdate
from app.services import writing_task_service

router = APIRouter(prefix="/teacher", tags=["teacher-tasks"])
teacher_only = require_roles(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/tasks", response_model=ApiResponse[list[TaskResponse]])
def get_tasks(
    task_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[list[TaskResponse]]:
    return success(writing_task_service.list_tasks(db, current_user, task_status))


@router.post("/tasks", response_model=ApiResponse[TaskResponse], status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[TaskResponse]:
    return success(writing_task_service.create_task(db, current_user, payload), message="任务草稿已创建")


@router.get("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[TaskResponse]:
    return success(writing_task_service.get_task_detail(db, current_user, task_id))


@router.put("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[TaskResponse]:
    return success(writing_task_service.update_task(db, current_user, task_id, payload), message="任务已更新")


@router.post("/tasks/{task_id}/publish", response_model=ApiResponse[TaskResponse])
def publish_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[TaskResponse]:
    return success(writing_task_service.publish_task(db, current_user, task_id), message="任务已发布")


@router.post("/tasks/{task_id}/close", response_model=ApiResponse[TaskResponse])
def close_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[TaskResponse]:
    return success(writing_task_service.close_task(db, current_user, task_id), message="任务已关闭")