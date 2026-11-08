"""API 路由聚合：后续业务模块在此注册，统一挂载 /api/v1 前缀。"""
from fastapi import APIRouter

from app.api import auth, classes, essays, evaluations, health, knowledge

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(essays.router)
api_router.include_router(classes.router)
api_router.include_router(evaluations.router)
api_router.include_router(knowledge.router)