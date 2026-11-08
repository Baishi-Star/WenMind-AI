"""统一导出所有模型，确保建表前完整注册到 Base.metadata。"""
from app.models.agent_evaluation import EvaluationReport, RetrievalLog
from app.models.appeal import Appeal, ReviewRecord
from app.models.base import Base, Dimension, EssayStatus, EvaluationStatus, TimestampMixin, UserRole, utc_now
from app.models.essay import Essay, EssayPrompt
from app.models.evaluation import AgentRun, DimensionScore, Evaluation, FeedbackItem
from app.models.growth import GrowthProfile, GrowthSnapshot, TrainingTask, TrainingTaskDetail
from app.models.knowledge import KbChunk, KbDocument
from app.models.rule_governance import RuleProposalDetail, RubricVersionGovernance
from app.models.rubric import RubricVersion, RuleProposal
from app.models.student_interaction import AppealItem, EvaluationQuestion
from app.models.teacher_review import FeedbackReviewChange, ReviewIssueTag, TeacherFeedbackItem
from app.models.user import ClassRoom, Enrollment, User

__all__ = [
    "AgentRun",
    "Appeal",
    "AppealItem",
    "Base",
    "ClassRoom",
    "Dimension",
    "DimensionScore",
    "Enrollment",
    "Essay",
    "EssayPrompt",
    "EssayStatus",
    "Evaluation",
    "EvaluationQuestion",
    "EvaluationReport",
    "EvaluationStatus",
    "FeedbackItem",
    "FeedbackReviewChange",
    "GrowthProfile",
    "GrowthSnapshot",
    "KbChunk",
    "KbDocument",
    "RetrievalLog",
    "ReviewIssueTag",
    "ReviewRecord",
    "RubricVersion",
    "RubricVersionGovernance",
    "RuleProposal",
    "RuleProposalDetail",
    "TeacherFeedbackItem",
    "TimestampMixin",
    "TrainingTask",
    "TrainingTaskDetail",
    "User",
    "UserRole",
    "utc_now",
]