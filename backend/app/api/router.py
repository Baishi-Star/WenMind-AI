"""API 路由聚合：后续业务模块在此注册，统一挂载 /api/v1 前缀。"""
from fastapi import APIRouter

from app.api import (
    annotations,
    appeals,
    auth,
    classes,
    essays,
    evaluations,
    files,
    growth,
    health,
    knowledge,
    questions,
    submissions,
    tasks,
    teacher_reviews,
    teacher_rules,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(essays.router)
api_router.include_router(classes.router)
api_router.include_router(evaluations.router)
api_router.include_router(knowledge.router)
api_router.include_router(questions.router)
api_router.include_router(appeals.router)
api_router.include_router(teacher_reviews.router)
api_router.include_router(teacher_rules.router)
api_router.include_router(growth.router)
api_router.include_router(tasks.router)
api_router.include_router(submissions.router)
api_router.include_router(files.router)
api_router.include_router(annotations.router)