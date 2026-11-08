"""学生评价多轮追问接口。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.interaction import QuestionCreate, QuestionResponse
from app.services.question_service import create_question, list_questions

router = APIRouter(prefix="/evaluations", tags=["questions"])


@router.get("/{evaluation_id}/questions", response_model=ApiResponse[list[QuestionResponse]])
def get_questions(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[QuestionResponse]]:
    return success(list_questions(db, current_user, evaluation_id))


@router.post("/{evaluation_id}/questions", response_model=ApiResponse[QuestionResponse], status_code=status.HTTP_201_CREATED)
def submit_question(
    evaluation_id: int,
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[QuestionResponse]:
    return success(create_question(db, current_user, evaluation_id, payload), message="追问已回答并保存")