"""教师班级学情分析：基于真实评价、复核记录、申诉与确认标签。"""
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ISSUE_TAGS
from app.core.exceptions import NotFoundError
from app.models.appeal import Appeal
from app.models.base import UserRole
from app.models.essay import Essay
from app.models.evaluation import Evaluation, FeedbackItem
from app.models.teacher_review import ReviewIssueTag
from app.models.user import ClassRoom, Enrollment, User
from app.schemas.growth import ClassAnalyticsResponse, StudentAnalyticsSummary
from app.services.access_service import assert_class_access
from app.services.growth_service import DIMENSION_LABELS, SCORED_DIMENSIONS, collect_points


def _student_ids_for_class(db: Session, class_id: int) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(Enrollment, Enrollment.student_id == User.id)
            .where(Enrollment.class_id == class_id, User.role == UserRole.STUDENT)
            .order_by(User.display_name)
        ).all()
    )


def _dimension_distribution(values: list[float]) -> dict[str, int]:
    low = sum(1 for value in values if value <= 2)
    basic = sum(1 for value in values if 2 < value < 4)
    good = sum(1 for value in values if value >= 4)
    return {"low": low, "basic": basic, "good": good, "total": len(values)}


def get_class_analytics(db: Session, user: User, class_id: int) -> ClassAnalyticsResponse:
    classroom = db.get(ClassRoom, class_id)
    if classroom is None:
        raise NotFoundError("班级不存在")
    assert_class_access(db, user, classroom)
    students = _student_ids_for_class(db, class_id)
    student_points = {student.id: collect_points(db, student.id) for student in students}
    all_points = [point for points in student_points.values() for point in points]
    dimension_values: dict[str, list[float]] = defaultdict(list)
    for point in all_points:
        for dimension, value in point.scores.items():
            dimension_values[dimension].append(value)
    dimension_averages = {
        dimension: round(sum(values) / len(values), 2)
        for dimension, values in dimension_values.items()
        if values
    }
    distribution = {
        dimension: _dimension_distribution(dimension_values.get(dimension, [])) for dimension in SCORED_DIMENSIONS
    }
    weak_ratios = {}
    for dimension in SCORED_DIMENSIONS:
        values = dimension_values.get(dimension, [])
        weak_ratios[dimension] = (
            round(sum(1 for value in values if value < settings.growth_weak_threshold) / len(values) * 100, 1)
            if values
            else 0.0
        )

    student_summaries = []
    for student in students:
        points = student_points[student.id]
        averages = {
            dimension: round(sum(point.scores[dimension] for point in points if dimension in point.scores) / len([point for point in points if dimension in point.scores]), 2)
            for dimension in SCORED_DIMENSIONS
            if any(dimension in point.scores for point in points)
        }
        weakest = min(averages, key=averages.get) if averages else None
        student_summaries.append(
            StudentAnalyticsSummary(
                student_id=student.id,
                student_name=student.display_name,
                sample_count=len(points),
                reviewed_count=sum(1 for point in points if point.review_status == "teacher_confirmed"),
                averages=averages,
                weakest_dimension=weakest,
                needs_data=len(points) < settings.growth_min_samples,
            )
        )

    student_ids = [student.id for student in students]
    issue_rows = db.execute(
        select(ReviewIssueTag, Appeal)
        .join(Appeal, ReviewIssueTag.appeal_id == Appeal.id)
        .where(Appeal.student_id.in_(student_ids or [-1]))
    ).all()
    issue_aggregate: dict[str, dict] = {}
    for tag, appeal in issue_rows:
        entry = issue_aggregate.setdefault(
            tag.tag_code,
            {"tag_code": tag.tag_code, "label": ISSUE_TAGS.get(tag.tag_code, tag.tag_code), "count": 0, "dimension_counts": defaultdict(int)},
        )
        entry["count"] += 1
        entry["dimension_counts"][appeal.dimension] += 1
    top_confirmed_issues = [
        {
            "tag_code": entry["tag_code"],
            "label": entry["label"],
            "count": entry["count"],
            "dimension_counts": dict(entry["dimension_counts"]),
        }
        for entry in sorted(issue_aggregate.values(), key=lambda item: item["count"], reverse=True)[:5]
    ]

    problem_rows = db.execute(
        select(FeedbackItem.dimension, func.count(FeedbackItem.id))
        .join(Evaluation, FeedbackItem.evaluation_id == Evaluation.id)
        .join(Essay, Evaluation.essay_id == Essay.id)
        .where(Essay.student_id.in_(student_ids or [-1]), Evaluation.status == "completed", FeedbackItem.category == "problem")
        .group_by(FeedbackItem.dimension)
    ).all()
    feedback_problem_counts = {dimension: count for dimension, count in problem_rows}

    appeal_status_rows = db.execute(
        select(Appeal.status, func.count(Appeal.id))
        .where(Appeal.student_id.in_(student_ids or [-1]))
        .group_by(Appeal.status)
    ).all()
    appeal_status_counts = {status: count for status, count in appeal_status_rows}

    evaluation_count = len(all_points)
    student_count = len(students)
    insufficient = evaluation_count < settings.growth_min_samples
    notice = (
        f"基于 {student_count} 名学生、{evaluation_count} 篇有效评价统计；"
        "教师复核结果优先于 AI 原始诊断。"
    )
    if insufficient:
        notice += f" 有效评价少于 {settings.growth_min_samples} 篇，班级统计仅作数据积累展示。"
    rubric_versions = sorted({point.rubric_version_id for point in all_points if point.rubric_version_id})
    if len(rubric_versions) > 1:
        notice += f" 样本跨越量规版本 {rubric_versions}，不能把差异全部解释为能力变化。"

    suggestions = []
    if dimension_averages:
        weakest = min(dimension_averages, key=dimension_averages.get)
        suggestions.append(
            {
                "title": f"优先补强{DIMENSION_LABELS[weakest]}",
                "description": {
                    "content": "围绕论据与观点的解释链开展片段写作训练，减少只罗列素材的写法。",
                    "organization": "用提纲重构训练段落功能与论证顺序，检查段间过渡。",
                    "language": "开展保留原意的改写训练，关注句式变化、指代和衔接。",
                }[weakest],
                "basis": f"班级{DIMENSION_LABELS[weakest]}均值为 {dimension_averages[weakest]:.2f}/5，样本 {len(dimension_values[weakest])} 条。",
                "source": "rule_based",
            }
        )
    if top_confirmed_issues:
        top = top_confirmed_issues[0]
        suggestions.append(
            {
                "title": f"教研讨论：{top['label']}",
                "description": "选取已确认的典型案例，讨论评价依据与量规表述是否需要澄清；不得仅凭申诉数量判定模型错误。",
                "basis": f"教师确认「{top['label']}」{top['count']} 条，涉及维度 {top['dimension_counts']}。",
                "source": "rule_based",
            }
        )
    if insufficient:
        suggestions.append(
            {
                "title": "继续积累真实评价样本",
                "description": "当前样本不足以形成稳定教学结论，建议继续完成作文评价和教师复核后再分析趋势。",
                "basis": f"有效评价 {evaluation_count} 篇，低于 {settings.growth_min_samples} 篇阈值。",
                "source": "rule_based",
            }
        )
    return ClassAnalyticsResponse(
        class_id=classroom.id,
        class_name=classroom.name,
        student_count=student_count,
        essay_count=len({point.essay_id for point in all_points}),
        evaluation_count=evaluation_count,
        reviewed_evaluation_count=sum(1 for point in all_points if point.review_status == "teacher_confirmed"),
        insufficient_data=insufficient,
        notice=notice,
        dimension_averages=dimension_averages,
        dimension_distribution=distribution,
        dimension_weak_ratios=weak_ratios,
        students=student_summaries,
        top_confirmed_issues=top_confirmed_issues,
        feedback_problem_counts=feedback_problem_counts,
        appeal_status_counts=appeal_status_counts,
        teaching_suggestions=suggestions,
        rubric_versions=rubric_versions,
    )