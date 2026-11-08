"""评价多轮追问：关联作文、反馈、证据、历史对话并持久化。"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.evidence import verify_agent_evidence, verify_evidence_item
from app.agents.llm_client import AgentLLMClient
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.agent_evaluation import RetrievalLog
from app.models.base import EvaluationStatus, UserRole, utc_now
from app.models.essay import EssayPrompt
from app.models.evaluation import AgentRun, Evaluation, FeedbackItem
from app.models.student_interaction import EvaluationQuestion
from app.models.user import User
from app.schemas.agent import AgentResult, EvidenceItem
from app.schemas.interaction import QuestionCreate, QuestionResponse
from app.services.essay_service import get_essay_entity


def _loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _serialize_question(question: EvaluationQuestion) -> QuestionResponse:
    return QuestionResponse(
        id=question.id,
        evaluation_id=question.evaluation_id,
        feedback_item_id=question.feedback_item_id,
        question=question.question,
        answer=question.answer,
        evidence=[EvidenceItem.model_validate(item) for item in _loads(question.evidence_json, [])],
        suggestions=_loads(question.suggestions_json, []),
        status=question.status,
        execution_mode=question.execution_mode,
        model_name=question.model_name,
        error_message=question.error_message,
        created_at=question.created_at,
        completed_at=question.completed_at,
    )


def list_questions(db: Session, user: User, evaluation_id: int) -> list[QuestionResponse]:
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise NotFoundError("评价任务不存在")
    get_essay_entity(db, user, evaluation.essay_id)
    questions = db.scalars(
        select(EvaluationQuestion).where(EvaluationQuestion.evaluation_id == evaluation_id).order_by(EvaluationQuestion.id)
    ).all()
    return [_serialize_question(item) for item in questions]


def create_question(db: Session, user: User, evaluation_id: int, payload: QuestionCreate) -> QuestionResponse:
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise NotFoundError("评价任务不存在")
    essay = get_essay_entity(db, user, evaluation.essay_id)
    if user.role != UserRole.STUDENT or essay.student_id != user.id:
        raise PermissionDeniedError("只能对本人的作文评价发起追问")
    if evaluation.status != EvaluationStatus.COMPLETED:
        raise ConflictError("评价完成后才能发起追问")
    feedback = None
    if payload.feedback_item_id is not None:
        feedback = db.get(FeedbackItem, payload.feedback_item_id)
        if feedback is None or feedback.evaluation_id != evaluation.id:
            raise NotFoundError("关联评价项不存在")

    client = AgentLLMClient()
    record = EvaluationQuestion(
        evaluation_id=evaluation.id,
        student_id=user.id,
        feedback_item_id=feedback.id if feedback else None,
        question=payload.question,
        status="processing",
        execution_mode=client.execution_mode,
        model_name=client.model_name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    try:
        history = db.scalars(
            select(EvaluationQuestion)
            .where(EvaluationQuestion.evaluation_id == evaluation.id, EvaluationQuestion.id != record.id)
            .order_by(EvaluationQuestion.id.desc())
            .limit(6)
        ).all()
        prompt = db.get(EssayPrompt, essay.prompt_id) if essay.prompt_id else None
        retrieval = db.scalar(
            select(RetrievalLog).where(RetrievalLog.evaluation_id == evaluation.id).order_by(RetrievalLog.id.desc())
        )
        knowledge_context = _loads(retrieval.results_json, []) if retrieval else []
        previous_results = []
        for run in db.scalars(select(AgentRun).where(AgentRun.evaluation_id == evaluation.id).order_by(AgentRun.id)).all():
            output = _loads(run.output_json, None)
            if output:
                previous_results.append(AgentResult.model_validate(output))
        essay_context = {
            "essay_id": essay.id,
            "content_version": essay.content_version,
            "title": prompt.title if prompt else "自由作文",
            "requirements": prompt.requirements if prompt else "未提供额外写作要求",
            "content": essay.content,
            "current_feedback": {
                "id": feedback.id,
                "dimension": feedback.dimension,
                "category": feedback.category,
                "content": feedback.content,
                "suggestion": feedback.suggestion,
                "evidence": _loads(feedback.evidence_json, []),
            } if feedback else None,
            "conversation_history": [
                {"question": item.question, "answer": item.answer, "status": item.status}
                for item in reversed(history)
            ],
        }
        if client.execution_mode == "mock":
            evidence = [EvidenceItem.model_validate(item) for item in (_loads(feedback.evidence_json, []) if feedback else [])]
            if not evidence:
                for result in previous_results:
                    if result.evidence:
                        evidence = result.evidence[:1]
                        break
            answer = (
                f"Mock 追问演示（非真实模型推理）：你的问题“{payload.question}”已关联评价 #{evaluation.id}、"
                "当前作文和已有原文证据。Mock 不能判断这句话的真实表达效果，也不能生成可信的语义改写。"
            )
            if feedback:
                answer += f"你质疑的评价项为“{feedback.content}”。"
            answer += "如果你强调某种表达是有意设计，应保留其创作意图并交由教师结合语境复核，不能仅因非标准表达就判错。"
            suggestions = [
                "Mock 建议：指出你希望对哪段原文保留何种表达效果，再由真实模型或教师给出针对性修改。",
                "可比较两种处理方式：完全保留原句，或在保留风格的前提下仅调整指代、衔接和必要信息。",
            ]
            result = None
        else:
            result, _token_usage = client.execute(
                "followup_agent", payload.question, essay_context, knowledge_context, previous_results
            )
            result = verify_agent_evidence(result, essay.content)
            answer = result.analysis
            evidence = result.evidence
            suggestions = result.suggestions

        record.answer = answer
        record.evidence_json = json.dumps([item.model_dump() for item in evidence], ensure_ascii=False)
        record.suggestions_json = json.dumps(suggestions, ensure_ascii=False)
        record.status = "completed"
        record.completed_at = utc_now()
        db.commit()
        return _serialize_question(record)
    except Exception as exc:
        record.status = "failed"
        record.error_message = str(exc)[:1000]
        record.completed_at = utc_now()
        db.commit()
        if isinstance(exc, AppError):
            raise
        raise AppError(f"追问处理失败：{exc}") from exc