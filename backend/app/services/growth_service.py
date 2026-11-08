"""成长画像与训练业务：基于真实评价、优先采用教师复核结果。"""
import json
from datetime import timedelta, timezone
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.appeal import Appeal, ReviewRecord
from app.models.base import UserRole, utc_now
from app.models.essay import Essay, EssayPrompt
from app.models.evaluation import DimensionScore, Evaluation
from app.models.growth import GrowthProfile, GrowthSnapshot, TrainingTask, TrainingTaskDetail
from app.models.user import User
from app.schemas.growth import (
    CapabilityItem,
    GrowthHistoryResponse,
    GrowthPoint,
    GrowthProfileResponse,
    TrainingTaskListResponse,
    TrainingTaskResponse,
)
from app.services.access_service import assert_student_access

SCORED_DIMENSIONS = ("content", "organization", "language")
DIMENSION_LABELS = {"content": "内容能力", "organization": "结构能力", "language": "语言能力"}
DIMENSION_SOURCE = {
    "content": "content 维度有效诊断",
    "organization": "organization 维度有效诊断",
    "language": "language 维度有效诊断",
}

TRAINING_LIBRARY = {
    "content": {
        "task_type": "argument_deepening",
        "ability": "content",
        "objective": "提升论据选择与论证深度",
        "content": "选择最近一篇作文的核心观点，补充至少两条不同类型的论据，并写出“论据 → 分析 → 观点”的完整解释链，避免只罗列事例。",
    },
    "organization": {
        "task_type": "paragraph_organization",
        "ability": "organization",
        "objective": "提升段落功能与结构衔接",
        "content": "重写一篇旧作文的提纲：为开头、主体、结尾标注功能，并检查每个段落是否承担明确任务、段间是否存在可说明的推进关系。",
    },
    "language": {
        "task_type": "sentence_variation",
        "ability": "language",
        "objective": "提升句式变化与表达准确性",
        "content": "选取最近作文中的一段，保留原意和表达风格，分别改写为长短句结合、由因到果两种版本，并比较指代、衔接和语气的差异。",
    },
    "advanced": {
        "task_type": "advanced_expression",
        "ability": "overall",
        "objective": "在稳定能力上完成更高阶表达挑战",
        "content": "选择同一主题的两篇不同风格材料，提炼共同问题并形成自己的判断，写一段有明确观点、证据和让步分析的议论段落。",
    },
}


def _loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def resolve_student(db: Session, user: User, student_id: int | None = None) -> User:
    target_id = student_id or user.id
    if user.role == UserRole.STUDENT and target_id != user.id:
        raise PermissionDeniedError("学生只能查看本人的成长数据")
    student = db.get(User, target_id)
    if student is None or student.role != UserRole.STUDENT:
        raise NotFoundError("学生不存在")
    if user.role != UserRole.STUDENT:
        assert_student_access(db, user, student.id)
    return student


def _review_map(db: Session, evaluation_ids: list[int]) -> dict[int, ReviewRecord]:
    if not evaluation_ids:
        return {}
    rows = db.execute(
        select(ReviewRecord, Appeal.evaluation_id)
        .join(Appeal, ReviewRecord.appeal_id == Appeal.id)
        .where(Appeal.evaluation_id.in_(evaluation_ids))
        .order_by(ReviewRecord.reviewed_at, ReviewRecord.id)
    ).all()
    return {evaluation_id: record for record, evaluation_id in rows}


def collect_points(db: Session, student_id: int) -> list[GrowthPoint]:
    rows = db.execute(
        select(Evaluation, Essay, EssayPrompt.title)
        .join(Essay, Evaluation.essay_id == Essay.id)
        .outerjoin(EssayPrompt, Essay.prompt_id == EssayPrompt.id)
        .where(Essay.student_id == student_id, Evaluation.status == "completed")
        .order_by(Evaluation.created_at, Evaluation.id)
    ).all()
    evaluation_ids = [row[0].id for row in rows]
    reviews = _review_map(db, evaluation_ids)
    dimension_rows = db.scalars(
        select(DimensionScore).where(DimensionScore.evaluation_id.in_(evaluation_ids or [-1]))
    ).all()
    dimension_map: dict[int, dict[str, DimensionScore]] = {}
    for item in dimension_rows:
        dimension_map.setdefault(item.evaluation_id, {})[item.dimension] = item

    points: list[GrowthPoint] = []
    for evaluation, essay, prompt_title in rows:
        scores: dict[str, float] = {}
        review = reviews.get(evaluation.id)
        revised = _loads(review.revised_score_json, {}) if review else {}
        for dimension in SCORED_DIMENSIONS:
            item = dimension_map.get(evaluation.id, {}).get(dimension)
            if item is None:
                continue
            value = None
            if review is not None:
                value = revised.get(dimension)
                if value is None:
                    value = item.final_score if item.final_score is not None else item.original_score
            else:
                value = item.final_score if item.final_score is not None else item.original_score
            if value is not None:
                scores[dimension] = float(value)
        if not scores:
            continue
        review_status = "teacher_confirmed" if review is not None or any(
            dimension_map.get(evaluation.id, {}).get(dimension) is not None
            and dimension_map[evaluation.id][dimension].final_score is not None
            for dimension in SCORED_DIMENSIONS
        ) else "ai_unreviewed"
        points.append(
            GrowthPoint(
                evaluation_id=evaluation.id,
                essay_id=essay.id,
                essay_title=prompt_title or "自由作文",
                created_at=evaluation.created_at,
                rubric_version_id=evaluation.rubric_version_id,
                review_status=review_status,
                review_decision=review.decision if review else None,
                reviewed_at=review.reviewed_at if review else None,
                scores=scores,
                unweighted_average=round(mean(scores.values()), 2),
            )
        )
    return points


def _training_counts(db: Session, student_id: int) -> tuple[int, int]:
    pending = db.scalar(
        select(func.count(TrainingTask.id)).where(TrainingTask.student_id == student_id, TrainingTask.status == "pending")
    ) or 0
    completed = db.scalar(
        select(func.count(TrainingTask.id)).where(TrainingTask.student_id == student_id, TrainingTask.status == "completed")
    ) or 0
    return pending, completed


def _compose_profile(db: Session, student: User, points: list[GrowthPoint]) -> GrowthProfileResponse:
    sample_count = len(points)
    averages = {
        dimension: round(mean(point.scores[dimension] for point in points if dimension in point.scores), 2)
        for dimension in SCORED_DIMENSIONS
        if any(dimension in point.scores for point in points)
    }
    reviewed_count = sum(1 for point in points if point.review_status == "teacher_confirmed")
    rubric_versions = sorted({point.rubric_version_id for point in points if point.rubric_version_id})
    insufficient = sample_count < settings.growth_min_samples
    version_mixed = len(rubric_versions) > 1
    if sample_count == 0:
        trend_status = "no_data"
        notice = "暂无已完成的真实作文评价，暂不生成成长趋势。"
    elif insufficient:
        trend_status = "data_accumulating"
        notice = f"当前仅有 {sample_count} 篇有效评价，少于 {settings.growth_min_samples} 篇，趋势只作数据积累展示，不代表长期变化。"
    else:
        trend_status = "available"
        notice = f"基于 {sample_count} 篇有效评价生成趋势；教师复核评价 {reviewed_count} 篇。"
    if version_mixed:
        notice += f" 样本跨越量规版本 {rubric_versions}，变化可能包含规则版本差异，不能全部解释为能力提升。"
    capabilities = [
        CapabilityItem(
            key=dimension,
            label=DIMENSION_LABELS[dimension],
            supported=True,
            available=dimension in averages,
            score=averages.get(dimension),
            sample_count=sum(1 for point in points if dimension in point.scores),
            source=DIMENSION_SOURCE[dimension],
            note=(
                "优先采用教师复核后的最终诊断值；未复核评价使用 AI 原始诊断值。"
                if dimension in averages
                else "当前量规支持该维度计分，但尚无已完成评价，暂无可展示数值。"
            ),
        )
        for dimension in SCORED_DIMENSIONS
    ]
    capabilities.extend(
        [
            CapabilityItem(
                key="topic",
                label="审题能力",
                supported=False,
                available=False,
                source="not_scored",
                note="当前量规与审题 Agent 只提供定性审题分析，没有独立分值。为避免编造权重，本画像不生成审题数值趋势。",
            ),
            CapabilityItem(
                key="argumentation",
                label="论证能力",
                supported=False,
                available=False,
                source="not_scored",
                note="当前论证分析包含在内容维度内，未设置独立分值。本画像不拆分内容分伪造论证趋势。",
            ),
        ]
    )
    available_ranked = sorted(averages, key=averages.get, reverse=True)
    strengths = [DIMENSION_LABELS[item] for item in available_ranked if averages[item] >= settings.growth_weak_threshold][:2]
    weaknesses = [
        DIMENSION_LABELS[item]
        for item in sorted(averages, key=averages.get)
        if averages[item] < settings.growth_weak_threshold
    ][:2]
    pending, completed = _training_counts(db, student.id)
    return GrowthProfileResponse(
        student_id=student.id,
        student_name=student.display_name,
        sample_count=sample_count,
        reviewed_count=reviewed_count,
        unreviewed_count=sample_count - reviewed_count,
        insufficient_data=insufficient,
        trend_status=trend_status,
        notice=notice,
        version_mixed=version_mixed,
        rubric_versions=rubric_versions,
        capabilities=capabilities,
        averages=averages,
        strengths=strengths,
        weaknesses=weaknesses,
        training_pending=pending,
        training_completed=completed,
        latest_evaluation_at=points[-1].created_at if points else None,
    )


def _cache_profile(db: Session, profile: GrowthProfileResponse, points: list[GrowthPoint]) -> None:
    record = db.scalar(select(GrowthProfile).where(GrowthProfile.student_id == profile.student_id))
    if record is None:
        record = GrowthProfile(student_id=profile.student_id)
        db.add(record)
    record.profile_json = json.dumps(profile.model_dump(mode="json"), ensure_ascii=False)
    record.sample_count = profile.sample_count
    for point in points:
        snapshot = db.scalar(
            select(GrowthSnapshot).where(
                GrowthSnapshot.student_id == profile.student_id,
                GrowthSnapshot.evaluation_id == point.evaluation_id,
            )
        )
        if snapshot is None:
            snapshot = GrowthSnapshot(student_id=profile.student_id, evaluation_id=point.evaluation_id)
            db.add(snapshot)
        snapshot.dimension_scores_json = json.dumps(
            {
                "scores": point.scores,
                "review_status": point.review_status,
                "rubric_version_id": point.rubric_version_id,
                "unweighted_average": point.unweighted_average,
            },
            ensure_ascii=False,
        )
    db.commit()


def get_profile(db: Session, user: User, student_id: int | None = None) -> GrowthProfileResponse:
    student = resolve_student(db, user, student_id)
    points = collect_points(db, student.id)
    profile = _compose_profile(db, student, points)
    _cache_profile(db, profile, points)
    return profile


def get_history(db: Session, user: User, student_id: int | None = None) -> GrowthHistoryResponse:
    student = resolve_student(db, user, student_id)
    points = collect_points(db, student.id)
    profile = _compose_profile(db, student, points)
    return GrowthHistoryResponse(
        student_id=student.id,
        points=points,
        insufficient_data=profile.insufficient_data,
        notice=profile.notice,
        rubric_versions=profile.rubric_versions,
    )


def _recent_averages(points: list[GrowthPoint]) -> tuple[dict[str, float], list[int]]:
    recent = points[-settings.growth_recent_window :]
    averages = {}
    for dimension in SCORED_DIMENSIONS:
        values = [point.scores[dimension] for point in recent if dimension in point.scores]
        if values:
            averages[dimension] = round(mean(values), 2)
    return averages, [point.evaluation_id for point in recent]


def _task_specs(averages: dict[str, float], sample_count: int) -> list[dict]:
    if not averages:
        return []
    specs = []
    for dimension in SCORED_DIMENSIONS:
        value = averages.get(dimension)
        if value is None or value >= settings.growth_weak_threshold:
            continue
        library = TRAINING_LIBRARY[dimension]
        specs.append(
            {
                **library,
                "reason": (
                    f"最近有效评价的{DIMENSION_LABELS[dimension]}均值为 {value:.2f}/5，"
                    f"低于弱项阈值 {settings.growth_weak_threshold:.1f}（样本 {sample_count} 篇）。"
                    "该判断只基于真实诊断记录，不代表长期能力定论。"
                ),
            }
        )
    if not specs:
        library = TRAINING_LIBRARY["advanced"]
        best_dimension = max(averages, key=averages.get)
        specs.append(
            {
                **library,
                "reason": (
                    f"最近有效评价未发现低于 {settings.growth_weak_threshold:.1f} 的计分维度，"
                    f"{DIMENSION_LABELS[best_dimension]}均值 {averages[best_dimension]:.2f}/5 相对稳定，"
                    f"可进行高阶表达挑战（样本 {sample_count} 篇）。"
                ),
            }
        )
    return specs


def ensure_training_tasks(db: Session, user: User) -> TrainingTaskListResponse:
    student = resolve_student(db, user, None)
    points = collect_points(db, student.id)
    averages, source_ids = _recent_averages(points)
    for spec in _task_specs(averages, len(points)):
        latest = db.scalar(
            select(TrainingTask)
            .where(TrainingTask.student_id == student.id, TrainingTask.task_type == spec["task_type"])
            .order_by(TrainingTask.id.desc())
        )
        if latest is not None:
            if latest.status == "pending":
                continue
            if latest.status == "completed" and latest.completed_at:
                completed_at = latest.completed_at
                if completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                if completed_at > utc_now() - timedelta(days=7):
                    continue
        task = TrainingTask(
            student_id=student.id,
            task_type=spec["task_type"],
            content=spec["content"],
            reason=spec["reason"],
            status="pending",
        )
        db.add(task)
        db.flush()
        db.add(
            TrainingTaskDetail(
                task_id=task.id,
                objective=spec["objective"],
                ability=spec["ability"],
                source_evaluation_ids_json=json.dumps(source_ids, ensure_ascii=False),
            )
        )
    db.commit()
    return list_training_tasks(db, user)


def _serialize_task(task: TrainingTask, detail: TrainingTaskDetail | None) -> TrainingTaskResponse:
    return TrainingTaskResponse(
        id=task.id,
        task_type=task.task_type,
        ability=detail.ability if detail else "overall",
        objective=detail.objective if detail else "提升写作能力",
        reason=task.reason,
        content=task.content,
        status=task.status,
        source_evaluation_ids=_loads(detail.source_evaluation_ids_json, []) if detail else [],
        result_text=detail.result_text if detail else None,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


def list_training_tasks(db: Session, user: User) -> TrainingTaskListResponse:
    student = resolve_student(db, user, None)
    tasks = db.scalars(
        select(TrainingTask)
        .where(TrainingTask.student_id == student.id)
        .order_by(TrainingTask.status, TrainingTask.created_at.desc())
    ).all()
    details = db.scalars(
        select(TrainingTaskDetail).where(TrainingTaskDetail.task_id.in_([task.id for task in tasks] or [-1]))
    ).all()
    detail_map = {detail.task_id: detail for detail in details}
    serialized = [_serialize_task(task, detail_map.get(task.id)) for task in tasks]
    pending = sum(1 for task in serialized if task.status == "pending")
    completed = sum(1 for task in serialized if task.status == "completed")
    notice = "训练建议由真实评价中的近期弱项通过规则生成，不使用随机推荐。" if serialized else "暂无训练任务，需至少一篇有效评价后才能生成建议。"
    return TrainingTaskListResponse(tasks=serialized, pending_count=pending, completed_count=completed, notice=notice)


def complete_training_task(db: Session, user: User, task_id: int, result_text: str) -> TrainingTaskResponse:
    if user.role != UserRole.STUDENT:
        raise PermissionDeniedError("只有学生可以完成本人训练任务")
    task = db.get(TrainingTask, task_id)
    if task is None or task.student_id != user.id:
        raise NotFoundError("训练任务不存在")
    if task.status == "completed":
        raise ConflictError("该训练任务已完成")
    detail = db.scalar(select(TrainingTaskDetail).where(TrainingTaskDetail.task_id == task.id))
    if detail is None:
        detail = TrainingTaskDetail(task_id=task.id, objective="提升写作能力", ability="overall")
        db.add(detail)
    task.status = "completed"
    task.completed_at = utc_now()
    detail.result_text = result_text.strip()
    db.commit()
    return _serialize_task(task, detail)