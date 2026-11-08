"""规则建议生成、教师审批、回归测试与版本发布业务。"""
import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import DIMENSION_AGENT, ISSUE_TAGS
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.appeal import Appeal
from app.models.base import UserRole, utc_now
from app.models.essay import Essay
from app.models.evaluation import Evaluation
from app.models.rule_governance import RuleProposalDetail, RubricVersionGovernance
from app.models.rubric import RubricVersion, RuleProposal
from app.models.teacher_review import ReviewIssueTag
from app.models.user import User
from app.schemas.teacher import (
    RegressionResponse,
    RubricVersionView,
    RuleProposalDecision,
    RuleProposalListItem,
)
from app.services.access_service import accessible_student_ids

OPEN_PROPOSAL_STATUSES = ("proposed", "reviewing", "approved", "testing")


def _loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _require_teacher(user: User) -> None:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise PermissionDeniedError("只有教师或管理员可以管理评价规则")


def _latest_published(db: Session) -> RubricVersion | None:
    return db.scalar(
        select(RubricVersion).where(RubricVersion.status == "published").order_by(RubricVersion.id.desc()).limit(1)
    )


def _proposal_item(db: Session, proposal: RuleProposal) -> RuleProposalListItem:
    detail = db.scalar(select(RuleProposalDetail).where(RuleProposalDetail.proposal_id == proposal.id))
    governance = db.scalar(select(RubricVersionGovernance).where(RubricVersionGovernance.proposal_id == proposal.id))
    return RuleProposalListItem(
        id=proposal.id,
        title=proposal.title,
        source_tag=detail.source_tag if detail else "other",
        dimension=proposal.dimension,
        agent_name=proposal.agent_name,
        problem_description=proposal.problem_description,
        current_rule=detail.current_rule if detail else "",
        typical_cases=_loads(detail.typical_cases_json, []) if detail else [],
        suggestion=proposal.suggestion,
        expected_effect=detail.expected_effect if detail else "",
        status=proposal.status,
        related_appeal_ids=_loads(proposal.related_appeals_json, []),
        created_at=proposal.created_at,
        approver_id=detail.approver_id if detail else None,
        decided_at=detail.decided_at if detail else None,
        decision_note=detail.decision_note if detail else None,
        result_version_id=governance.rubric_version_id if governance else None,
    )


def list_proposals(db: Session, user: User, status: str | None = None) -> list[RuleProposalListItem]:
    _require_teacher(user)
    statement = select(RuleProposal)
    if status:
        statement = statement.where(RuleProposal.status == status)
    proposals = db.scalars(statement.order_by(RuleProposal.created_at.desc(), RuleProposal.id.desc())).all()
    return [_proposal_item(db, proposal) for proposal in proposals]


def generate_proposals(db: Session, user: User, window_days: int = 30) -> list[int]:
    _require_teacher(user)
    student_ids = accessible_student_ids(db, user)
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    conditions = [Appeal.submitted_at >= cutoff]
    if student_ids is not None:
        conditions.append(Appeal.student_id.in_(student_ids or [-1]))
    appeals = db.scalars(select(Appeal).where(*conditions)).all()
    appeal_ids = [appeal.id for appeal in appeals]
    tags = db.scalars(select(ReviewIssueTag).where(ReviewIssueTag.appeal_id.in_(appeal_ids or [-1]))).all()
    grouped: dict[str, list[ReviewIssueTag]] = {}
    for tag in tags:
        grouped.setdefault(tag.tag_code, []).append(tag)
    latest = _latest_published(db)
    created_ids = []
    for tag_code, tag_records in grouped.items():
        distinct_appeal_ids = sorted({tag.appeal_id for tag in tag_records})
        if len(distinct_appeal_ids) < settings.rule_proposal_min_cases:
            continue
        existing = db.scalars(
            select(RuleProposal)
            .join(RuleProposalDetail, RuleProposalDetail.proposal_id == RuleProposal.id)
            .where(
                RuleProposalDetail.source_tag == tag_code,
                RuleProposal.status.in_(OPEN_PROPOSAL_STATUSES),
            )
        ).all()
        if existing:
            continue
        related_appeals = [appeal for appeal in appeals if appeal.id in distinct_appeal_ids]
        dimensions = [appeal.dimension for appeal in related_appeals]
        dominant_dimension = max(set(dimensions), key=dimensions.count) if dimensions else "overall"
        label = ISSUE_TAGS.get(tag_code, tag_code)
        proposal = RuleProposal(
            title=f"{label}重复争议需要核查",
            problem_description=(
                f"近 {window_days} 天有 {len(distinct_appeal_ids)} 条教师已确认的「{label}」争议，"
                f"涉及申诉 {'、'.join(f'#{item}' for item in distinct_appeal_ids)}。"
                "该数量仅代表复核确认的问题记录，不等同于模型错误率。"
            ),
            dimension=dominant_dimension,
            agent_name=DIMENSION_AGENT.get(dominant_dimension),
            status="proposed",
            related_appeals_json=json.dumps(distinct_appeal_ids, ensure_ascii=False),
            suggestion=(
                f"建议教师核查当前量规中与「{label}」相关的维度表述和示例，先形成修改草案。"
                "系统不会自动修改正式评分规则。"
            ),
            created_by=user.id,
        )
        db.add(proposal)
        db.flush()
        current_rule = latest.dimensions_json if latest else "{}"
        cases = [
            {
                "appeal_id": appeal.id,
                "evaluation_id": appeal.evaluation_id,
                "dimension": appeal.dimension,
                "reason_type": appeal.reason_type,
                "description": appeal.description[:240],
            }
            for appeal in related_appeals
        ]
        db.add(
            RuleProposalDetail(
                proposal_id=proposal.id,
                source_tag=tag_code,
                current_rule=current_rule,
                expected_effect=(
                    "预期减少同类复核争议并提升评价依据的一致性；"
                    "这是方向性目标，必须在发布后以新的真实复核记录持续验证。"
                ),
                typical_cases_json=json.dumps(cases, ensure_ascii=False),
            )
        )
        created_ids.append(proposal.id)
    db.commit()
    return created_ids


def _next_version(latest: RubricVersion, db: Session) -> str:
    match = re.search(r"(\d+)\.(\d+)", latest.version)
    if not match:
        return f"{latest.version}.1"
    major, minor = int(match.group(1)), int(match.group(2)) + 1
    version = f"v{major}.{minor}"
    while db.scalar(select(RubricVersion.id).where(RubricVersion.name == latest.name, RubricVersion.version == version)):
        minor += 1
        version = f"v{major}.{minor}"
    return version


def approve_proposal(db: Session, user: User, proposal_id: int, payload: RuleProposalDecision) -> RubricVersionView:
    _require_teacher(user)
    proposal = db.get(RuleProposal, proposal_id)
    if proposal is None:
        raise NotFoundError("规则建议不存在")
    if proposal.status not in ("proposed", "reviewing"):
        raise ConflictError("该规则建议已经处理，不能重复审批")
    latest = _latest_published(db)
    if latest is None:
        raise AppError("当前没有已发布量规，无法生成新版本")
    if payload.title:
        proposal.title = payload.title.strip()
    if payload.problem_description:
        proposal.problem_description = payload.problem_description.strip()
    if payload.suggestion:
        proposal.suggestion = payload.suggestion.strip()
    details = db.scalar(select(RuleProposalDetail).where(RuleProposalDetail.proposal_id == proposal.id))
    if details and payload.expected_effect:
        details.expected_effect = payload.expected_effect.strip()
    dimensions = _loads(latest.dimensions_json, {})
    if not isinstance(dimensions, dict):
        dimensions = {"content": dimensions}
    dimensions["clarification"] = payload.rule_content.strip()
    dimensions["source_proposal_id"] = proposal.id
    dimensions["clarification_note"] = "教师确认的文字澄清；未修改评分权重或正式分数区间"
    version = RubricVersion(
        name=latest.name,
        version=_next_version(latest, db),
        dimensions_json=json.dumps(dimensions, ensure_ascii=False),
        status="testing",
        change_reason=payload.change_reason.strip(),
        is_demo=latest.is_demo,
        created_by=user.id,
    )
    db.add(version)
    db.flush()
    db.add(
        RubricVersionGovernance(
            rubric_version_id=version.id,
            proposal_id=proposal.id,
            parent_version_id=latest.id,
            approver_id=user.id,
            approved_at=utc_now(),
        )
    )
    proposal.status = "approved"
    if details:
        details.approver_id = user.id
        details.decision_note = payload.decision_note
        details.decided_at = utc_now()
    db.commit()
    return _version_view(db, version)


def reject_proposal(db: Session, user: User, proposal_id: int, note: str) -> RuleProposalListItem:
    _require_teacher(user)
    proposal = db.get(RuleProposal, proposal_id)
    if proposal is None:
        raise NotFoundError("规则建议不存在")
    if proposal.status not in ("proposed", "reviewing"):
        raise ConflictError("该规则建议已经处理")
    proposal.status = "rejected"
    detail = db.scalar(select(RuleProposalDetail).where(RuleProposalDetail.proposal_id == proposal.id))
    if detail:
        detail.approver_id = user.id
        detail.decision_note = note
        detail.decided_at = utc_now()
    db.commit()
    return _proposal_item(db, proposal)


def _version_view(db: Session, version: RubricVersion) -> RubricVersionView:
    governance = db.scalar(
        select(RubricVersionGovernance).where(RubricVersionGovernance.rubric_version_id == version.id)
    )
    return RubricVersionView(
        id=version.id,
        name=version.name,
        version=version.version,
        status=version.status,
        change_reason=version.change_reason,
        created_by=version.created_by,
        created_at=version.created_at,
        approver_id=governance.approver_id if governance else None,
        approved_at=governance.approved_at if governance else None,
        effective_at=governance.effective_at if governance else None,
        parent_version_id=governance.parent_version_id if governance else None,
        proposal_id=governance.proposal_id if governance else None,
        regression_result=_loads(governance.regression_result_json, {}) if governance else {},
    )


def list_versions(db: Session, user: User) -> list[RubricVersionView]:
    _require_teacher(user)
    versions = db.scalars(select(RubricVersion).order_by(RubricVersion.id.desc())).all()
    return [_version_view(db, version) for version in versions]


def run_regression_test(db: Session, user: User, version_id: int) -> RegressionResponse:
    _require_teacher(user)
    version = db.get(RubricVersion, version_id)
    if version is None:
        raise NotFoundError("规则版本不存在")
    if version.status not in ("testing", "draft"):
        raise ConflictError("只有测试中的规则版本可以运行回归测试")
    governance = db.scalar(
        select(RubricVersionGovernance).where(RubricVersionGovernance.rubric_version_id == version.id)
    )
    if governance is None:
        raise NotFoundError("该版本缺少治理记录")
    dimensions = _loads(version.dimensions_json, {})
    dimension_list = dimensions.get("dimensions", []) if isinstance(dimensions, dict) else []
    checks = []
    present = {item.get("dimension") for item in dimension_list if isinstance(item, dict)}
    checks.append(
        {
            "name": "三维度结构完整",
            "passed": {"content", "organization", "language"}.issubset(present),
            "detail": f"实际维度：{', '.join(sorted(present))}",
        }
    )
    valid_scores = all(
        isinstance(item, dict) and isinstance(item.get("max_score"), (int, float)) and item["max_score"] > 0
        for item in dimension_list
    )
    checks.append({"name": "维度上限有效", "passed": valid_scores, "detail": "沿用现有诊断量表，不新增权重"})
    sample_count = len(
        db.scalars(select(Evaluation.id).where(Evaluation.status == "completed")).all()
    )
    checks.append(
        {
            "name": "存在历史评价样本",
            "passed": sample_count > 0,
            "detail": f"历史 completed 评价 {sample_count} 条",
        }
    )
    status = "passed" if all(item["passed"] for item in checks) else "failed"
    result = {
        "status": status,
        "sample_count": sample_count,
        "checks": checks,
        "mode": "structure_and_history_only",
        "message": "仅验证规则结构、维度上限和历史样本存在性；未调用模型重新评分，不代表语义回归通过。",
        "tested_at": utc_now().isoformat(),
    }
    governance.regression_result_json = json.dumps(result, ensure_ascii=False)
    db.commit()
    return RegressionResponse(
        rubric_version_id=version.id,
        status=status,
        sample_count=sample_count,
        checks=checks,
        mode=result["mode"],
        message=result["message"],
    )


def publish_version(db: Session, user: User, version_id: int) -> RubricVersionView:
    _require_teacher(user)
    version = db.get(RubricVersion, version_id)
    if version is None:
        raise NotFoundError("规则版本不存在")
    if version.status != "testing":
        raise ConflictError("只有 testing 状态的版本可以发布")
    governance = db.scalar(
        select(RubricVersionGovernance).where(RubricVersionGovernance.rubric_version_id == version.id)
    )
    result = _loads(governance.regression_result_json, {}) if governance else {}
    if result.get("status") != "passed":
        raise ConflictError("新版本必须通过回归测试后才能启用")
    previous = db.scalars(
        select(RubricVersion).where(
            RubricVersion.name == version.name,
            RubricVersion.status == "published",
            RubricVersion.id != version.id,
        )
    ).all()
    for item in previous:
        item.status = "archived"
    version.status = "published"
    if governance:
        governance.effective_at = utc_now()
        governance.published_by = user.id
    if governance and governance.proposal_id:
        proposal = db.get(RuleProposal, governance.proposal_id)
        if proposal:
            proposal.status = "published"
    db.commit()
    return _version_view(db, version)