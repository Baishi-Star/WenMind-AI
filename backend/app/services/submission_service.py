"""作文提交业务：文字/在线输入提交闭环，逐题生成 essays 并复用多 Agent 评价。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.base import EssayStatus, UserRole, utc_now
from app.models.essay import Essay, EssayPrompt
from app.models.evaluation import Evaluation
from app.models.submission import Submission, SubmissionAnswer, SubmissionStatus
from app.models.user import User
from app.models.writing_task import TaskStatus, WritingTask
from app.schemas.writing_task import AnswerInput, SubmissionAnswerResponse, SubmissionResponse
from app.services import writing_task_service
from app.services.evaluation_service import create_evaluation


def _serialize_submission(db: Session, submission: Submission) -> SubmissionResponse:
    task = db.get(WritingTask, submission.task_id)
    student = db.get(User, submission.student_id)
    from app.models.writing_task import TaskQuestion

    answers = []
    for answer in submission.answers:
        question = db.get(TaskQuestion, answer.question_id)
        evaluation = None
        if answer.essay_id:
            evaluation = db.scalar(
                select(Evaluation)
                .where(Evaluation.essay_id == answer.essay_id)
                .order_by(Evaluation.id.desc())
                .limit(1)
            )
        answers.append(
            SubmissionAnswerResponse(
                id=answer.id,
                question_id=answer.question_id,
                question_label=question.label if question else f"问题 {answer.question_id}",
                essay_id=answer.essay_id,
                evaluation_id=evaluation.id if evaluation else None,
                evaluation_status=evaluation.status if evaluation else None,
                confirmed_text=answer.confirmed_text,
                char_count=answer.char_count,
                is_confirmed=answer.is_confirmed,
            )
        )
    return SubmissionResponse(
        id=submission.id,
        task_id=submission.task_id,
        task_title=task.title if task else "",
        student_id=submission.student_id,
        student_name=student.display_name if student else "",
        attempt_no=submission.attempt_no,
        input_mode=submission.input_mode,
        status=submission.status,
        extraction_mode=submission.extraction_mode,
        extraction_note=submission.extraction_note,
        submitted_at=submission.submitted_at,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
        answers=answers,
        file_count=len(submission.files),
    )


def _upsert_answer_essay(
    db: Session,
    submission: Submission,
    task: WritingTask,
    question_id: int,
    content: str,
    is_demo: bool,
) -> tuple[SubmissionAnswer, Essay]:
    """为逐题作答创建或更新一条 essays 记录，复用现有评价链路。"""
    answer = db.scalar(
        select(SubmissionAnswer).where(
            SubmissionAnswer.submission_id == submission.id,
            SubmissionAnswer.question_id == question_id,
        )
    )
    prompt = db.scalar(select(EssayPrompt).where(EssayPrompt.title == task.title).limit(1))
    if prompt is None:
        prompt = EssayPrompt(
            title=task.title,
            requirements=task.requirements or task.prompt_text,
            rubric_version_id=task.rubric_version_id,
            is_demo=is_demo,
            created_by=task.created_by,
        )
        db.add(prompt)
        db.flush()
    if answer is None:
        answer = SubmissionAnswer(
            submission_id=submission.id,
            question_id=question_id,
            raw_text=content,
            confirmed_text=content,
            char_count=len(content),
            is_confirmed=True,
        )
        db.add(answer)
        db.flush()

    if answer.essay_id:
        essay = db.get(Essay, answer.essay_id)
        if essay.content != content:
            essay.content_version += 1
        essay.content = content
        essay.char_count = len(content)
        essay.status = EssayStatus.EVALUATING
    else:
        essay = Essay(
            student_id=submission.student_id,
            prompt_id=prompt.id,
            content=content,
            content_version=1,
            char_count=len(content),
            status=EssayStatus.EVALUATING,
            is_demo=is_demo,
        )
        db.add(essay)
        db.flush()
        answer.essay_id = essay.id
    answer.confirmed_text = content
    answer.char_count = len(content)
    return answer, essay


def create_image_submission(db: Session, student: User, task_id: int) -> SubmissionResponse:
    """图片提交流程：先创建 draft 提交用于上传图片，此时不触发评价。

    图片需上传、识别、学生确认后才调用 submit_image_submission 进入评价队列。
    """
    if student.role != UserRole.STUDENT:
        raise PermissionDeniedError("只有学生可以提交作文")
    context = writing_task_service.get_student_task(db, student, task_id)
    task: WritingTask = context["task"]
    writing_task_service.assert_can_submit(db, student, task)
    if not task.questions:
        raise AppError("该任务未配置子问题，无法提交")

    attempt_no = (
        db.scalar(
            select(func.max(Submission.attempt_no)).where(
                Submission.task_id == task.id, Submission.student_id == student.id
            )
        )
        or 0
    ) + 1
    submission = Submission(
        task_id=task.id,
        student_id=student.id,
        attempt_no=attempt_no,
        input_mode="image",
        status=SubmissionStatus.DRAFT,
        is_demo=student.is_demo,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return _serialize_submission(db, submission)


def submit_image_submission(db: Session, student: User, submission_id: int) -> SubmissionResponse:
    """学生确认识别文本后提交图片作文，进入多 Agent 评价队列。

    仅当提交处于 ready（识别文本已确认）时允许；逐题作答复用 essays/evaluations 链路。
    """
    if student.role != UserRole.STUDENT:
        raise PermissionDeniedError("只有学生可以提交作文")
    submission = db.get(Submission, submission_id)
    if submission is None or submission.student_id != student.id:
        raise NotFoundError("提交记录不存在")
    if submission.status != SubmissionStatus.READY:
        raise ConflictError("请先完成图片识别并确认文本后再提交")
    task = db.get(WritingTask, submission.task_id)
    writing_task_service.assert_can_submit(db, student, task)
    if not task.questions:
        raise AppError("该任务未配置子问题，无法提交")

    answer = db.scalar(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id))
    if answer is None or not answer.confirmed_text.strip():
        raise ConflictError("尚未确认作答文本，无法提交")

    for question in task.questions:
        length = len(answer.confirmed_text)
        if task.word_min and length < task.word_min:
            raise AppError(f"{question.label} 字数不足：当前 {length} 字，要求不少于 {task.word_min} 字")
        if task.word_max and length > task.word_max:
            raise AppError(f"{question.label} 字数超限：当前 {length} 字，要求不超过 {task.word_max} 字")
        if length > settings.essay_max_chars:
            raise AppError(f"{question.label} 超过系统上限 {settings.essay_max_chars} 字")

    created: list[int] = []
    for question in task.questions:
        _answer, essay = _upsert_answer_essay(
            db, submission, task, question.id, answer.confirmed_text, student.is_demo
        )
        try:
            evaluation = create_evaluation(db, student, essay.id)
            created.append(evaluation.id)
        except ConflictError:
            existing = db.scalar(
                select(Evaluation).where(Evaluation.essay_id == essay.id).order_by(Evaluation.id.desc()).limit(1)
            )
            if existing is not None:
                created.append(existing.id)
    submission.status = SubmissionStatus.EVALUATING
    submission.submitted_at = utc_now()
    db.commit()
    db.refresh(submission)
    return _serialize_submission(db, submission)


def create_text_submission(db: Session, student: User, task_id: int, answers: list[AnswerInput]) -> SubmissionResponse:
    """文字/在线输入提交：逐题校验 → 落库 → 触发多 Agent 评价。"""
    if student.role != UserRole.STUDENT:
        raise PermissionDeniedError("只有学生可以提交作文")
    context = writing_task_service.get_student_task(db, student, task_id)
    task: WritingTask = context["task"]
    writing_task_service.assert_can_submit(db, student, task)

    question_ids = [question.id for question in task.questions]
    if not question_ids:
        raise AppError("该任务未配置子问题，无法提交")
    submitted_ids = [item.question_id for item in answers]
    if len(set(submitted_ids)) != len(submitted_ids):
        raise AppError("同一子问题不能重复提交作答")
    unknown = set(submitted_ids) - set(question_ids)
    if unknown:
        raise AppError(f"存在不属于该任务的子问题：{sorted(unknown)}")
    missing = [question for question in task.questions if question.id not in submitted_ids]
    if missing:
        raise ConflictError(f"仍有子问题未作答：{missing[0].label}")

    question_map = {question.id: question for question in task.questions}
    for item in answers:
        question = question_map[item.question_id]
        length = len(item.content)
        if task.word_min and length < task.word_min:
            raise AppError(f"{question.label} 字数不足：当前 {length} 字，要求不少于 {task.word_min} 字")
        if task.word_max and length > task.word_max:
            raise AppError(f"{question.label} 字数超限：当前 {length} 字，要求不超过 {task.word_max} 字")
        if length > settings.essay_max_chars:
            raise AppError(f"{question.label} 超过系统上限 {settings.essay_max_chars} 字")

    attempt_no = (
        db.scalar(
            select(func.max(Submission.attempt_no)).where(
                Submission.task_id == task.id, Submission.student_id == student.id
            )
        )
        or 0
    ) + 1
    submission = Submission(
        task_id=task.id,
        student_id=student.id,
        attempt_no=attempt_no,
        input_mode="text",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=utc_now(),
        is_demo=student.is_demo,
    )
    db.add(submission)
    db.flush()

    created_evaluations = []
    for item in answers:
        _answer, essay = _upsert_answer_essay(db, submission, task, item.question_id, item.content, student.is_demo)
        try:
            evaluation = create_evaluation(db, student, essay.id)
            created_evaluations.append(evaluation.id)
        except ConflictError:
            existing = db.scalar(
                select(Evaluation).where(Evaluation.essay_id == essay.id).order_by(Evaluation.id.desc()).limit(1)
            )
            if existing is not None:
                created_evaluations.append(existing.id)
    submission.status = SubmissionStatus.EVALUATING
    db.commit()
    db.refresh(submission)
    return _serialize_submission(db, submission)


def list_student_submissions(db: Session, student: User) -> list[SubmissionResponse]:
    if student.role != UserRole.STUDENT:
        raise PermissionDeniedError("只有学生可以查看本人提交")
    submissions = db.scalars(
        select(Submission)
        .where(Submission.student_id == student.id)
        .order_by(Submission.created_at.desc(), Submission.id.desc())
    ).all()
    return [_serialize_submission(db, item) for item in submissions]


def get_submission_detail(db: Session, user: User, submission_id: int) -> SubmissionResponse:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise NotFoundError("提交记录不存在")
    if user.role == UserRole.STUDENT and submission.student_id != user.id:
        raise PermissionDeniedError("无权访问该提交记录")
    if user.role == UserRole.TEACHER:
        task = db.get(WritingTask, submission.task_id)
        if task is None or task.created_by != user.id:
            raise PermissionDeniedError("无权访问该提交记录")
        if not writing_task_service.is_overdue(task) and task.status == TaskStatus.DRAFT:
            raise PermissionDeniedError("草稿任务的提交不可见")
    return _serialize_submission(db, submission)


def refresh_submission_status(db: Session, submission: Submission) -> None:
    """根据逐题评价结果刷新提交状态，供查询时调用。"""
    statuses = []
    for answer in submission.answers:
        if not answer.essay_id:
            continue
        evaluation = db.scalar(
            select(Evaluation).where(Evaluation.essay_id == answer.essay_id).order_by(Evaluation.id.desc()).limit(1)
        )
        if evaluation is not None:
            statuses.append(evaluation.status)
    if not statuses:
        return
    if all(status == "completed" for status in statuses):
        new_status = SubmissionStatus.EVALUATED
    elif any(status == "failed" for status in statuses):
        new_status = SubmissionStatus.FAILED
    elif any(status in ("pending", "processing") for status in statuses):
        new_status = SubmissionStatus.EVALUATING
    else:
        new_status = submission.status
    if new_status != submission.status:
        submission.status = new_status
        db.commit()