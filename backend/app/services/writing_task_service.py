"""写作任务业务：教师布置任务、学生自主任务、范围校验与状态流转。"""
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.base import UserRole, utc_now
from app.models.rubric import RubricVersion
from app.models.submission import Submission
from app.models.user import ClassRoom, Enrollment, User
from app.models.writing_task import TaskQuestion, TaskSource, TaskStatus, TaskTarget, TargetType, WritingTask
from app.schemas.writing_task import (
    TaskCreate,
    TaskQuestionResponse,
    TaskResponse,
    TaskTargetResponse,
    TaskUpdate,
)
from app.services.access_service import accessible_student_ids, assert_class_access, assert_student_access


def _loads_targets(db: Session, task: WritingTask) -> tuple[list[TaskTargetResponse], list[str]]:
    targets = []
    class_names = []
    for target in task.targets:
        name = ""
        if target.target_type == TargetType.CLASS:
            classroom = db.get(ClassRoom, target.target_id)
            name = classroom.name if classroom else "已删除班级"
            class_names.append(name)
        else:
            student = db.get(User, target.target_id)
            name = student.display_name if student else "已删除学生"
        targets.append(
            TaskTargetResponse(
                id=target.id,
                target_type=target.target_type,
                target_id=target.target_id,
                target_name=name,
            )
        )
    return targets, class_names


def serialize_task(db: Session, task: WritingTask) -> TaskResponse:
    targets, class_names = _loads_targets(db, task)
    return TaskResponse(
        id=task.id,
        title=task.title,
        source_type=task.source_type,
        prompt_text=task.prompt_text,
        requirements=task.requirements,
        rubric_version_id=task.rubric_version_id,
        word_min=task.word_min,
        word_max=task.word_max,
        allow_resubmit=task.allow_resubmit,
        status=task.status,
        start_at=task.start_at,
        due_at=task.due_at,
        published_at=task.published_at,
        is_demo=task.is_demo,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        targets=targets,
        questions=[TaskQuestionResponse.model_validate(item) for item in task.questions],
        target_class_names=class_names,
        question_count=len(task.questions),
    )


def _validate_time_range(start_at: datetime | None, due_at: datetime | None) -> None:
    if due_at is None:
        return
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    if due_at <= datetime.now(timezone.utc):
        raise AppError("截止时间必须晚于当前时间")
    if start_at is not None:
        normalized_start = start_at if start_at.tzinfo else start_at.replace(tzinfo=timezone.utc)
        if normalized_start >= due_at:
            raise AppError("截止时间必须晚于开始时间")


def _validate_word_range(word_min: int, word_max: int) -> None:
    if word_max and word_min and word_max < word_min:
        raise AppError("字数上限不能小于下限")


def _validate_rubric(db: Session, rubric_version_id: int | None) -> None:
    if rubric_version_id is None:
        return
    rubric = db.get(RubricVersion, rubric_version_id)
    if rubric is None:
        raise NotFoundError("评分量规版本不存在")
    if rubric.status != "published":
        raise AppError("只能绑定已发布的评分量规版本")


def _require_teacher(user: User) -> None:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以管理写作任务")


def _replace_targets(db: Session, task: WritingTask, user: User, targets) -> None:
    for existing in list(task.targets):
        db.delete(existing)
    db.flush()
    seen = set()
    for item in targets:
        key = (item.target_type, item.target_id)
        if key in seen:
            continue
        seen.add(key)
        if item.target_type == TargetType.CLASS:
            classroom = db.get(ClassRoom, item.target_id)
            if classroom is None:
                raise NotFoundError(f"班级 {item.target_id} 不存在")
            assert_class_access(db, user, classroom)
        else:
            student = db.get(User, item.target_id)
            if student is None or student.role != UserRole.STUDENT:
                raise NotFoundError(f"学生 {item.target_id} 不存在")
            assert_student_access(db, user, student.id)
        db.add(TaskTarget(task_id=task.id, target_type=item.target_type, target_id=item.target_id))


def _replace_questions(db: Session, task: WritingTask, questions) -> None:
    if len(questions) > settings.task_max_questions:
        raise AppError(f"单个任务最多支持 {settings.task_max_questions} 道子问题")
    for existing in list(task.questions):
        db.delete(existing)
    db.flush()
    for index, item in enumerate(questions, start=1):
        db.add(
            TaskQuestion(
                task_id=task.id,
                order_no=index,
                label=item.label.strip(),
                question_text=item.question_text.strip(),
                requirements=(item.requirements or "").strip(),
                answer_type=item.answer_type,
                max_score=item.max_score,
            )
        )


def list_tasks(db: Session, user: User, status: str | None = None) -> list[TaskResponse]:
    _require_teacher(user)
    statement = select(WritingTask)
    if user.role == UserRole.TEACHER:
        statement = statement.where(WritingTask.created_by == user.id)
    if status:
        statement = statement.where(WritingTask.status == status)
    tasks = db.scalars(statement.order_by(WritingTask.created_at.desc(), WritingTask.id.desc())).all()
    return [serialize_task(db, task) for task in tasks]


def get_task_entity(db: Session, user: User, task_id: int) -> WritingTask:
    task = db.get(WritingTask, task_id)
    if task is None:
        raise NotFoundError("写作任务不存在")
    if user.role == UserRole.TEACHER and task.created_by != user.id:
        raise PermissionDeniedError("无权访问该写作任务")
    if user.role == UserRole.STUDENT and task.source_type == TaskSource.TEACHER:
        raise PermissionDeniedError("学生请使用学生端任务接口")
    return task


def get_task_detail(db: Session, user: User, task_id: int) -> TaskResponse:
    return serialize_task(db, get_task_entity(db, user, task_id))


def create_task(db: Session, user: User, payload: TaskCreate) -> TaskResponse:
    _require_teacher(user)
    if user.role == UserRole.TEACHER and not payload.targets:
        raise AppError("教师布置任务时至少需要指定一个班级或学生")
    _validate_time_range(payload.start_at, payload.due_at)
    _validate_word_range(payload.word_min, payload.word_max)
    _validate_rubric(db, payload.rubric_version_id)
    task = WritingTask(
        title=payload.title.strip(),
        source_type=TaskSource.TEACHER,
        prompt_text=payload.prompt_text.strip(),
        requirements=payload.requirements.strip(),
        rubric_version_id=payload.rubric_version_id,
        word_min=payload.word_min,
        word_max=payload.word_max,
        allow_resubmit=payload.allow_resubmit,
        status=TaskStatus.DRAFT,
        start_at=payload.start_at,
        due_at=payload.due_at,
        is_demo=user.is_demo,
        created_by=user.id,
    )
    db.add(task)
    db.flush()
    _replace_targets(db, task, user, payload.targets)
    _replace_questions(db, task, payload.questions)
    db.commit()
    db.refresh(task)
    return serialize_task(db, task)


def update_task(db: Session, user: User, task_id: int, payload: TaskUpdate) -> TaskResponse:
    _require_teacher(user)
    task = get_task_entity(db, user, task_id)
    if task.status in (TaskStatus.CLOSED, TaskStatus.ARCHIVED):
        raise ConflictError("已关闭或归档的任务不能修改")
    submissions = db.scalar(select(func.count(Submission.id)).where(Submission.task_id == task.id)) or 0
    if submissions and payload.questions is not None:
        raise ConflictError("已有学生提交，不能再修改子问题结构")
    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.prompt_text is not None:
        task.prompt_text = payload.prompt_text.strip()
    if payload.requirements is not None:
        task.requirements = payload.requirements.strip()
    if payload.rubric_version_id is not None:
        _validate_rubric(db, payload.rubric_version_id)
        task.rubric_version_id = payload.rubric_version_id
    if payload.word_min is not None:
        task.word_min = payload.word_min
    if payload.word_max is not None:
        task.word_max = payload.word_max
    if payload.allow_resubmit is not None:
        task.allow_resubmit = payload.allow_resubmit
    if payload.start_at is not None:
        task.start_at = payload.start_at
    if payload.due_at is not None:
        task.due_at = payload.due_at
    _validate_time_range(task.start_at, task.due_at)
    _validate_word_range(task.word_min, task.word_max)
    if payload.targets is not None:
        _replace_targets(db, task, user, payload.targets)
    if payload.questions is not None:
        _replace_questions(db, task, payload.questions)
    db.commit()
    db.refresh(task)
    return serialize_task(db, task)


def publish_task(db: Session, user: User, task_id: int) -> TaskResponse:
    _require_teacher(user)
    task = get_task_entity(db, user, task_id)
    if task.status != TaskStatus.DRAFT:
        raise ConflictError("只有草稿状态的任务可以发布")
    if not task.targets:
        raise AppError("发布前必须至少指定一个班级或学生")
    _validate_rubric(db, task.rubric_version_id)
    _validate_time_range(task.start_at, task.due_at)
    task.status = TaskStatus.PUBLISHED
    task.published_at = utc_now()
    db.commit()
    db.refresh(task)
    return serialize_task(db, task)


def close_task(db: Session, user: User, task_id: int) -> TaskResponse:
    _require_teacher(user)
    task = get_task_entity(db, user, task_id)
    if task.status != TaskStatus.PUBLISHED:
        raise ConflictError("只有已发布的任务可以关闭")
    task.status = TaskStatus.CLOSED
    db.commit()
    db.refresh(task)
    return serialize_task(db, task)


def student_task_ids(db: Session, student: User) -> list[int]:
    """学生可见任务：被直接点名，或任务下发到本人所在班级。"""
    class_ids = list(db.scalars(select(Enrollment.class_id).where(Enrollment.student_id == student.id)).all())
    conditions = [(TaskTarget.target_type == TargetType.STUDENT) & (TaskTarget.target_id == student.id)]
    if class_ids:
        conditions.append((TaskTarget.target_type == TargetType.CLASS) & (TaskTarget.target_id.in_(class_ids)))
    task_ids = db.scalars(select(TaskTarget.task_id).where(or_(*conditions)).distinct()).all()
    return list(task_ids)


def is_overdue(task: WritingTask) -> bool:
    if task.due_at is None:
        return False
    due = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
    return due < datetime.now(timezone.utc)


def list_student_tasks(db: Session, student: User, status: str | None = None) -> list[dict]:
    """学生可见的已发布任务，含本人提交与评价状态。"""
    if student.role != UserRole.STUDENT:
        raise PermissionDeniedError("只有学生可以查看本人写作任务")
    task_ids = student_task_ids(db, student)
    if not task_ids:
        return []
    statement = select(WritingTask).where(
        WritingTask.id.in_(task_ids),
        WritingTask.status.in_((TaskStatus.PUBLISHED, TaskStatus.CLOSED)),
    )
    if status:
        statement = statement.where(WritingTask.status == status)
    tasks = db.scalars(statement.order_by(WritingTask.due_at.is_(None), WritingTask.due_at, WritingTask.id.desc())).all()
    submissions = db.scalars(
        select(Submission).where(
            Submission.student_id == student.id,
            Submission.task_id.in_([task.id for task in tasks] or [-1]),
        )
    ).all()
    submission_map: dict[int, Submission] = {}
    for submission in submissions:
        current = submission_map.get(submission.task_id)
        if current is None or submission.attempt_no > current.attempt_no:
            submission_map[submission.task_id] = submission
    result = []
    for task in tasks:
        teacher = db.get(User, task.created_by)
        _, class_names = _loads_targets(db, task)
        submission = submission_map.get(task.id)
        result.append(
            {
                "task": task,
                "teacher_name": teacher.display_name if teacher else None,
                "class_names": class_names,
                "submission": submission,
            }
        )
    return result


def get_student_task(db: Session, student: User, task_id: int) -> dict:
    if student.role != UserRole.STUDENT:
        raise PermissionDeniedError("只有学生可以查看本人写作任务")
    if task_id not in student_task_ids(db, student):
        raise PermissionDeniedError("无权访问该写作任务")
    task = db.get(WritingTask, task_id)
    if task is None or task.status not in (TaskStatus.PUBLISHED, TaskStatus.CLOSED):
        raise NotFoundError("写作任务不存在或未发布")
    teacher = db.get(User, task.created_by)
    _, class_names = _loads_targets(db, task)
    submission = db.scalar(
        select(Submission)
        .where(Submission.task_id == task.id, Submission.student_id == student.id)
        .order_by(Submission.attempt_no.desc())
        .limit(1)
    )
    return {
        "task": task,
        "teacher_name": teacher.display_name if teacher else None,
        "class_names": class_names,
        "submission": submission,
    }


def assert_can_submit(db: Session, student: User, task: WritingTask) -> None:
    """提交资格校验：范围、状态、截止时间和重交策略。"""
    if task.status != TaskStatus.PUBLISHED:
        raise ConflictError("任务已关闭，不能再提交")
    if is_overdue(task):
        raise ConflictError("任务已超过截止时间，不能再提交")
    if task.start_at is not None:
        start = task.start_at if task.start_at.tzinfo else task.start_at.replace(tzinfo=timezone.utc)
        if start > datetime.now(timezone.utc):
            raise ConflictError("任务尚未开始，暂不能提交")
    existing = db.scalar(
        select(func.count(Submission.id)).where(
            Submission.task_id == task.id,
            Submission.student_id == student.id,
            Submission.status.in_(
                (
                    "submitted",
                    "evaluating",
                    "evaluated",
                    "uploaded",
                    "needs_confirmation",
                    "ready",
                )
            ),
        )
    ) or 0
    if existing and not task.allow_resubmit:
        raise ConflictError("该任务不允许重复提交，如需修改请联系教师")