"""教师申诉复核、争议归因与真实统计业务。"""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DIMENSION_AGENT, ISSUE_TAGS, REASON_TAG_MAP
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.appeal import Appeal, ReviewRecord
from app.models.base import UserRole, utc_now
from app.models.essay import Essay, EssayPrompt
from app.models.evaluation import DimensionScore, Evaluation, FeedbackItem
from app.models.student_interaction import AppealItem
from app.models.teacher_review import FeedbackReviewChange, ReviewIssueTag, TeacherFeedbackItem
from app.models.user import ClassRoom, Enrollment, User
from app.schemas.agent import EvidenceItem
from app.schemas.teacher import (
    AppealPatternStats,
    ClassificationSuggestion,
    TeacherAppealDetail,
    TeacherAppealListItem,
    TeacherFeedbackView,
    TeacherReviewRequest,
    TeacherReviewResponse,
)
from app.services.access_service import accessible_student_ids, assert_class_access, assert_student_access
from app.services.evaluation_service import get_evaluation_detail

ACTIVE_APPEAL_STATUSES = ("pending", "reviewing")
STATUS_MAP = {"uphold": "rejected", "adjust": "accepted", "need_more_info": "reviewing"}


def _loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _class_names(db: Session, student_id: int, user: User) -> list[str]:
    statement = (
        select(ClassRoom.name)
        .join(Enrollment, Enrollment.class_id == ClassRoom.id)
        .where(Enrollment.student_id == student_id)
    )
    if user.role == UserRole.TEACHER:
        statement = statement.where(ClassRoom.teacher_id == user.id)
    return list(db.scalars(statement).all())


def _scope_student_ids(db: Session, user: User, class_id: int | None = None) -> list[int] | None:
    ids = accessible_student_ids(db, user)
    if class_id is None:
        return ids
    classroom = db.get(ClassRoom, class_id)
    if classroom is None:
        raise NotFoundError("班级不存在")
    assert_class_access(db, user, classroom)
    class_ids = list(db.scalars(select(Enrollment.student_id).where(Enrollment.class_id == class_id)).all())
    if ids is None:
        return class_ids
    return [item for item in ids if item in class_ids]


def _latest_review(db: Session, appeal_id: int) -> ReviewRecord | None:
    return db.scalar(select(ReviewRecord).where(ReviewRecord.appeal_id == appeal_id).order_by(ReviewRecord.id.desc()))


def list_appeals(
    db: Session,
    user: User,
    class_id: int | None = None,
    status: str | None = None,
    reason_type: str | None = None,
) -> list[TeacherAppealListItem]:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以查看申诉工作台")
    student_ids = _scope_student_ids(db, user, class_id)
    conditions = []
    if student_ids is not None:
        conditions.append(Appeal.student_id.in_(student_ids or [-1]))
    if status:
        conditions.append(Appeal.status == status)
    if reason_type:
        conditions.append(Appeal.reason_type == reason_type)
    appeals = db.scalars(
        select(Appeal).where(*conditions).order_by(Appeal.submitted_at.desc(), Appeal.id.desc())
    ).all()
    result = []
    for appeal in appeals:
        evaluation = db.get(Evaluation, appeal.evaluation_id)
        essay = db.get(Essay, evaluation.essay_id)
        prompt = db.get(EssayPrompt, essay.prompt_id) if essay.prompt_id else None
        student = db.get(User, appeal.student_id)
        review = _latest_review(db, appeal.id)
        result.append(
            TeacherAppealListItem(
                id=appeal.id,
                evaluation_id=evaluation.id,
                essay_id=essay.id,
                student_id=student.id,
                student_name=student.display_name,
                class_names=_class_names(db, student.id, user),
                essay_title=prompt.title if prompt else "自由作文",
                reason_type=appeal.reason_type,
                dimension=appeal.dimension,
                description=appeal.description,
                status=appeal.status,
                submitted_at=appeal.submitted_at,
                reviewed_at=review.reviewed_at if review else None,
                decision=review.decision if review else None,
            )
        )
    return result


def _classification_suggestions(db: Session, appeal: Appeal, evaluation: Evaluation) -> list[ClassificationSuggestion]:
    suggested: dict[str, str] = {}
    evidence_statuses = []
    for item in db.scalars(select(AppealItem).where(AppealItem.appeal_id == appeal.id)).all():
        evidence_statuses.extend(entry.get("verified_status") for entry in _loads(item.evidence_location_json, []))
    feedback_ids = [
        item.feedback_item_id
        for item in db.scalars(select(AppealItem).where(AppealItem.appeal_id == appeal.id)).all()
        if item.feedback_item_id
    ]
    for feedback_id in feedback_ids:
        feedback = db.get(FeedbackItem, feedback_id)
        if feedback:
            evidence_statuses.extend(entry.get("verified_status") for entry in _loads(feedback.evidence_json, []))
    if "unverified" in evidence_statuses or "not_found" in evidence_statuses:
        suggested["factual_error"] = "申诉关联证据中存在未通过原文核验的引用，需优先核对事实性错误。"
    mapped = REASON_TAG_MAP.get(appeal.reason_type)
    if mapped:
        suggested.setdefault(mapped, f"学生申诉原因映射为「{ISSUE_TAGS[mapped]}」。")
    text = appeal.description
    if any(word in text for word in ("建议不合理", "修改建议", "不符合上下文", "改法")):
        suggested.setdefault("unreasonable_suggestion", "学生说明涉及修改建议与上下文不匹配。")
    if not suggested:
        suggested["other"] = "现有信息不足以自动映射，建议教师人工判断。"
    return [
        ClassificationSuggestion(tag_code=code, label=ISSUE_TAGS[code], rationale=rationale)
        for code, rationale in list(suggested.items())[:3]
    ]


def get_appeal_detail(db: Session, user: User, appeal_id: int) -> TeacherAppealDetail:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以查看申诉详情")
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise NotFoundError("申诉记录不存在")
    assert_student_access(db, user, appeal.student_id)
    evaluation = db.get(Evaluation, appeal.evaluation_id)
    essay = db.get(Essay, evaluation.essay_id)
    prompt = db.get(EssayPrompt, essay.prompt_id) if essay.prompt_id else None
    student = db.get(User, appeal.student_id)
    raw_feedback = db.scalars(
        select(FeedbackItem).where(FeedbackItem.evaluation_id == evaluation.id).order_by(FeedbackItem.id)
    ).all()
    changes = db.scalars(
        select(FeedbackReviewChange)
        .where(FeedbackReviewChange.evaluation_id == evaluation.id)
        .order_by(FeedbackReviewChange.id)
    ).all()
    latest_change = {change.feedback_item_id: change for change in changes}
    teacher_feedback = db.scalars(
        select(TeacherFeedbackItem).where(TeacherFeedbackItem.evaluation_id == evaluation.id).order_by(TeacherFeedbackItem.id)
    ).all()
    feedback_views = []
    for item in raw_feedback:
        change = latest_change.get(item.id)
        feedback_views.append(
            TeacherFeedbackView(
                id=item.id,
                dimension=item.dimension,
                category=item.category,
                content=item.content,
                suggestion=item.suggestion,
                evidence=[EvidenceItem.model_validate(entry) for entry in _loads(item.evidence_json, [])],
                verified_status=item.verified_status,
                review_action=change.action if change else "kept",
                teacher_content=change.revised_content if change else None,
                teacher_suggestion=change.revised_suggestion if change else None,
            )
        )
    for item in teacher_feedback:
        if item.category == "teacher_summary":
            continue
        feedback_views.append(
            TeacherFeedbackView(
                id=item.id,
                dimension=item.dimension,
                category=item.category,
                content=item.content,
                suggestion=item.suggestion,
                evidence=[],
                verified_status="teacher_added",
                review_action="added",
                teacher_feedback=True,
            )
        )
    records = db.scalars(select(ReviewRecord).where(ReviewRecord.appeal_id == appeal.id).order_by(ReviewRecord.id)).all()
    tags = db.scalars(select(ReviewIssueTag).where(ReviewIssueTag.appeal_id == appeal.id).order_by(ReviewIssueTag.id)).all()
    return TeacherAppealDetail(
        id=appeal.id,
        evaluation_id=evaluation.id,
        essay_id=essay.id,
        student_id=student.id,
        student_name=student.display_name,
        class_names=_class_names(db, student.id, user),
        essay_title=prompt.title if prompt else "自由作文",
        essay_content=essay.content,
        reason_type=appeal.reason_type,
        dimension=appeal.dimension,
        description=appeal.description,
        status=appeal.status,
        submitted_at=appeal.submitted_at,
        appeal_items=[
            {
                "id": item.id,
                "feedback_item_id": item.feedback_item_id,
                "student_note": item.student_note,
                "evidence": _loads(item.evidence_location_json, []),
            }
            for item in db.scalars(select(AppealItem).where(AppealItem.appeal_id == appeal.id)).all()
        ],
        evaluation=get_evaluation_detail(db, user, evaluation.id),
        feedback_items=feedback_views,
        teacher_feedback_items=[
            {
                "id": item.id,
                "dimension": item.dimension,
                "content": item.content,
                "suggestion": item.suggestion,
                "created_at": item.created_at,
            }
            for item in teacher_feedback
        ],
        review_records=[
            {
                "id": record.id,
                "decision": record.decision,
                "review_comment": record.review_comment,
                "original_scores": _loads(record.original_score_json, {}),
                "revised_scores": _loads(record.revised_score_json, {}),
                "reviewed_at": record.reviewed_at,
            }
            for record in records
        ],
        confirmed_tags=sorted({tag.tag_code for tag in tags}),
        classification_suggestions=_classification_suggestions(db, appeal, evaluation),
    )


def review_appeal(db: Session, user: User, appeal_id: int, payload: TeacherReviewRequest) -> TeacherReviewResponse:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以复核申诉")
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise NotFoundError("申诉记录不存在")
    assert_student_access(db, user, appeal.student_id)
    if appeal.status not in ACTIVE_APPEAL_STATUSES:
        raise ConflictError("该申诉已经完成复核，不能重复提交")
    evaluation = db.get(Evaluation, appeal.evaluation_id)
    dimensions = db.scalars(select(DimensionScore).where(DimensionScore.evaluation_id == evaluation.id)).all()
    dimension_map = {item.dimension: item for item in dimensions}
    if payload.decision == "uphold" and payload.dimension_updates:
        raise AppError("维持 AI 原评价时不能同时修改维度分数")
    for update in payload.dimension_updates:
        if update.dimension not in dimension_map:
            raise NotFoundError(f"评价维度 {update.dimension} 不存在")
    invalid_codes = [code for code in payload.classification_codes if code not in ISSUE_TAGS]
    if invalid_codes:
        raise AppError(f"不支持的争议标签：{', '.join(invalid_codes)}")

    original_scores = {item.dimension: item.original_score for item in dimensions}
    revised_scores = {
        item.dimension: item.final_score if item.final_score is not None else item.original_score for item in dimensions
    }
    for update in payload.dimension_updates:
        revised_scores[update.dimension] = update.final_score
    record = ReviewRecord(
        appeal_id=appeal.id,
        reviewer_id=user.id,
        decision=payload.decision,
        original_score_json=json.dumps(original_scores, ensure_ascii=False),
        revised_score_json=json.dumps(revised_scores, ensure_ascii=False),
        review_comment=payload.change_reason.strip(),
        reviewed_at=utc_now(),
    )
    db.add(record)
    db.flush()
    for update in payload.dimension_updates:
        dimension_map[update.dimension].final_score = update.final_score
    for change in payload.feedback_changes:
        feedback = db.get(FeedbackItem, change.feedback_item_id)
        if feedback is None or feedback.evaluation_id != evaluation.id:
            raise NotFoundError(f"反馈条目 {change.feedback_item_id} 不属于当前评价")
        db.add(
            FeedbackReviewChange(
                evaluation_id=evaluation.id,
                feedback_item_id=feedback.id,
                review_id=record.id,
                action=change.action,
                revised_content=change.content,
                revised_suggestion=change.suggestion,
                teacher_id=user.id,
            )
        )
    for added in payload.added_feedback:
        db.add(
            TeacherFeedbackItem(
                evaluation_id=evaluation.id,
                review_id=record.id,
                teacher_id=user.id,
                dimension=added.dimension,
                category="teacher_added",
                content=added.content,
                suggestion=added.suggestion,
            )
        )
    if payload.revised_summary:
        db.add(
            TeacherFeedbackItem(
                evaluation_id=evaluation.id,
                review_id=record.id,
                teacher_id=user.id,
                dimension="overall",
                category="teacher_summary",
                content=payload.revised_summary,
                suggestion=None,
            )
        )
    for code in dict.fromkeys(payload.classification_codes):
        db.add(
            ReviewIssueTag(
                appeal_id=appeal.id,
                review_id=record.id,
                tag_code=code,
                note=payload.classification_note,
                confirmed_by=user.id,
            )
        )
    appeal.status = STATUS_MAP[payload.decision]
    db.commit()
    db.refresh(record)
    from app.services.rule_service import generate_proposals

    try:
        generate_proposals(db, user, window_days=30)
    except Exception:
        db.rollback()
    return TeacherReviewResponse(
        review_id=record.id,
        appeal_id=appeal.id,
        appeal_status=appeal.status,
        decision=payload.decision,
        reviewed_at=record.reviewed_at,
        final_dimension_scores=[
            {"dimension": item.dimension, "original_score": item.original_score, "final_score": item.final_score}
            for item in db.scalars(select(DimensionScore).where(DimensionScore.evaluation_id == evaluation.id)).all()
        ],
        confirmed_tags=payload.classification_codes,
    )


def appeal_pattern_stats(
    db: Session,
    user: User,
    days: int = 30,
    class_id: int | None = None,
    dimension: str | None = None,
    tag_code: str | None = None,
) -> AppealPatternStats:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以查看争议统计")
    student_ids = _scope_student_ids(db, user, class_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    conditions = [Appeal.submitted_at >= cutoff]
    if student_ids is not None:
        conditions.append(Appeal.student_id.in_(student_ids or [-1]))
    if dimension:
        conditions.append(Appeal.dimension == dimension)
    appeals = db.scalars(select(Appeal).where(*conditions)).all()
    appeal_ids = [item.id for item in appeals]
    tags = db.scalars(
        select(ReviewIssueTag).where(ReviewIssueTag.appeal_id.in_(appeal_ids or [-1]))
    ).all()
    if tag_code:
        tags = [item for item in tags if item.tag_code == tag_code]
        filtered_ids = {item.appeal_id for item in tags}
        appeals = [item for item in appeals if item.id in filtered_ids]
        appeal_ids = [item.id for item in appeals]
    reviewed_ids = set(
        db.scalars(select(ReviewRecord.appeal_id).where(ReviewRecord.appeal_id.in_(appeal_ids or [-1]))).all()
    )
    status_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    dimension_counts: dict[str, int] = {}
    for appeal in appeals:
        status_counts[appeal.status] = status_counts.get(appeal.status, 0) + 1
        reason_counts[appeal.reason_type] = reason_counts.get(appeal.reason_type, 0) + 1
        dimension_counts[appeal.dimension] = dimension_counts.get(appeal.dimension, 0) + 1
    tag_counter: dict[str, int] = {}
    agent_counter: dict[str, int] = {}
    rubric_counter: dict[str, int] = {}
    for tag in tags:
        tag_counter[tag.tag_code] = tag_counter.get(tag.tag_code, 0) + 1
        appeal = next((item for item in appeals if item.id == tag.appeal_id), None)
        if appeal:
            agent = DIMENSION_AGENT.get(appeal.dimension)
            if agent:
                agent_counter[agent] = agent_counter.get(agent, 0) + 1
            evaluation = db.get(Evaluation, appeal.evaluation_id)
            if evaluation and evaluation.rubric_version_id:
                key = str(evaluation.rubric_version_id)
                rubric_counter[key] = rubric_counter.get(key, 0) + 1
    total_tags = sum(tag_counter.values()) or 1
    return AppealPatternStats(
        days=days,
        sample_count=len(appeals),
        reviewed_count=len(reviewed_ids),
        small_sample_warning=len(appeals) < 3,
        status_counts=status_counts,
        reason_counts=reason_counts,
        dimension_counts=dimension_counts,
        tag_counts=[
            {
                "tag_code": code,
                "label": ISSUE_TAGS.get(code, code),
                "count": count,
                "percentage": round(count / total_tags * 100, 1),
            }
            for code, count in sorted(tag_counter.items(), key=lambda item: item[1], reverse=True)
        ],
        agent_counts=[
            {"agent_name": agent, "count": count}
            for agent, count in sorted(agent_counter.items(), key=lambda item: item[1], reverse=True)
        ],
        rubric_version_counts=[
            {"rubric_version_id": int(version_id), "count": count}
            for version_id, count in sorted(rubric_counter.items())
        ],
    )