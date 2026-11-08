"""规则建议生成、审批、回归测试与量规版本发布接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.base import UserRole
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.teacher import (
    RegressionResponse,
    RubricVersionView,
    RuleProposalDecision,
    RuleProposalListItem,
    RuleProposalReject,
)
from app.services.rule_service import (
    approve_proposal,
    generate_proposals,
    list_proposals,
    list_versions,
    publish_version,
    reject_proposal,
    run_regression_test,
)

router = APIRouter(prefix="/teacher", tags=["teacher-rules"])
teacher_only = require_roles(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/rule-proposals", response_model=ApiResponse[list[RuleProposalListItem]])
def get_proposals(
    proposal_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[list[RuleProposalListItem]]:
    return success(list_proposals(db, current_user, proposal_status))


@router.post("/rule-proposals/generate", response_model=ApiResponse[list[int]])
def create_proposals(
    window_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[list[int]]:
    created_ids = generate_proposals(db, current_user, window_days)
    return success(created_ids, message=f"已生成 {len(created_ids)} 条待审核规则建议")


@router.post("/rule-proposals/{proposal_id}/approve", response_model=ApiResponse[RubricVersionView])
def approve(
    proposal_id: int,
    payload: RuleProposalDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[RubricVersionView]:
    version = approve_proposal(db, current_user, proposal_id, payload)
    return success(version, message="建议已通过并生成 testing 规则版本，必须先通过回归测试才能发布")


@router.post("/rule-proposals/{proposal_id}/reject", response_model=ApiResponse[RuleProposalListItem])
def reject(
    proposal_id: int,
    payload: RuleProposalReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[RuleProposalListItem]:
    return success(reject_proposal(db, current_user, proposal_id, payload.decision_note), message="规则建议已驳回")


@router.get("/rubric-versions", response_model=ApiResponse[list[RubricVersionView]])
def get_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[list[RubricVersionView]]:
    return success(list_versions(db, current_user))


@router.post("/rubric-versions/{version_id}/regression-test", response_model=ApiResponse[RegressionResponse])
def regression_test(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[RegressionResponse]:
    return success(run_regression_test(db, current_user, version_id), message="回归测试已执行")


@router.post("/rubric-versions/{version_id}/publish", response_model=ApiResponse[RubricVersionView])
def publish(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(teacher_only),
) -> ApiResponse[RubricVersionView]:
    return success(publish_version(db, current_user, version_id), message="规则版本已正式发布，历史版本保留")