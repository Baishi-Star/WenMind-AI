"""统一导出所有模型，确保建表前完整注册到 Base.metadata。"""
from app.models.appeal import Appeal, ReviewRecord
from app.models.base import Base, Dimension, EssayStatus, EvaluationStatus, TimestampMixin, UserRole, utc_now
from app.models.essay import Essay, EssayPrompt
from app.models.evaluation import AgentRun, DimensionScore, Evaluation, FeedbackItem
from app.models.growth import GrowthProfile, GrowthSnapshot, TrainingTask
from app.models.knowledge import KbChunk, KbDocument
from app.models.rubric import RubricVersion, RuleProposal
from app.models.user import ClassRoom, Enrollment, User

__all__ = [
    "AgentRun",
    "Appeal",
    "Base",
    "ClassRoom",
    "Dimension",
    "DimensionScore",
    "Enrollment",
    "Essay",
    "EssayPrompt",
    "EssayStatus",
    "Evaluation",
    "EvaluationStatus",
    "FeedbackItem",
    "GrowthProfile",
    "GrowthSnapshot",
    "KbChunk",
    "KbDocument",
    "ReviewRecord",
    "RubricVersion",
    "RuleProposal",
    "TimestampMixin",
    "TrainingTask",
    "User",
    "UserRole",
    "utc_now",
]