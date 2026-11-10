"""学生端写作任务与作文提交接口。"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_evaluation_task
from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.writing_task import (
    ImageSubmissionCreate,
    StudentTaskResponse,
    SubmissionCreate,
    SubmissionResponse,
    TaskQuestionResponse,
)
from app.services import submission_service, writing_task_service

router = APIRouter(prefix="/student", tags=["student-submissions"])
student_only = require_roles(UserRole.STUDENT)


def _serialize_student_task(db: Session, student: User, context: dict) -> StudentTaskResponse:
    task = context["task"]
    submission = context.get("submission")
    evaluation_statuses = []
    if submission is not None:
        detail = submission_service._serialize_submission(db, submission)
        evaluation_statuses = [
            {
                "question_id": answer.question_id,
                "evaluation_id": answer.evaluation_id,
                "evaluation_status": answer.evaluation_status,
            }
            for answer in detail.answers
        ]
    return StudentTaskResponse(
        id=task.id,
        title=task.title,
        prompt_text=task.prompt_text,
        requirements=task.requirements,
        rubric_version_id=task.rubric_version_id,
        word_min=task.word_min,
        word_max=task.word_max,
        allow_resubmit=task.allow_resubmit,
        status=task.status,
        due_at=task.due_at,
        teacher_name=context.get("teacher_name"),
        class_names=context.get("class_names") or [],
        questions=[TaskQuestionResponse.model_validate(item) for item in task.questions],
        submission_status=submission.status if submission else None,
        submission_id=submission.id if submission else None,
        evaluation_statuses=evaluation_statuses,
        is_overdue=writing_task_service.is_overdue(task),
    )


@router.get("/tasks", response_model=ApiResponse[list[StudentTaskResponse]])
def get_student_tasks(
    task_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[list[StudentTaskResponse]]:
    contexts = writing_task_service.list_student_tasks(db, current_user, task_status)
    return success([_serialize_student_task(db, current_user, context) for context in contexts])


@router.get("/tasks/{task_id}", response_model=ApiResponse[StudentTaskResponse])
def get_student_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[StudentTaskResponse]:
    context = writing_task_service.get_student_task(db, current_user, task_id)
    return success(_serialize_student_task(db, current_user, context))


@router.post("/submissions", response_model=ApiResponse[SubmissionResponse], status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[SubmissionResponse]:
    submission = submission_service.create_text_submission(db, current_user, payload.task_id, payload.answers)
    for item in submission.answers:
        if item.evaluation_id is not None:
            background_tasks.add_task(run_evaluation_task, item.evaluation_id)
    return success(submission, message="作文已提交，AI 评价任务已进入后台队列")


@router.post(
    "/submissions/image",
    response_model=ApiResponse[SubmissionResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_image_submission(
    payload: ImageSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[SubmissionResponse]:
    submission = submission_service.create_image_submission(db, current_user, payload.task_id)
    return success(submission, message="已创建图片提交流程，请上传作文照片；确认后再进入评价队列")


@router.post("/submissions/{submission_id}/submit", response_model=ApiResponse[SubmissionResponse])
def submit_image_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[SubmissionResponse]:
    submission = submission_service.submit_image_submission(db, current_user, submission_id)
    for item in submission.answers:
        if item.evaluation_id is not None:
            background_tasks.add_task(run_evaluation_task, item.evaluation_id)
    return success(submission, message="图片作文已提交，AI 评价任务已进入后台队列")


@router.get("/submissions", response_model=ApiResponse[list[SubmissionResponse]])
def get_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[list[SubmissionResponse]]:
    return success(submission_service.list_student_submissions(db, current_user))


@router.get("/submissions/{submission_id}", response_model=ApiResponse[SubmissionResponse])
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(student_only),
) -> ApiResponse[SubmissionResponse]:
    return success(submission_service.get_submission_detail(db, current_user, submission_id))