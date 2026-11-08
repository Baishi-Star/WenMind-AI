"""评价 Orchestrator：RAG、专业 Agent、综合反馈、质量审核与数据库落盘。"""
import json
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.evidence import evidence_verification_status, verify_agent_evidence
from app.agents.llm_client import AGENT_PROMPT_VERSION, AgentLLMClient
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.agent_evaluation import EvaluationReport, RetrievalLog
from app.models.base import EssayStatus, EvaluationStatus, utc_now
from app.models.essay import Essay, EssayPrompt
from app.models.evaluation import AgentRun, DimensionScore, Evaluation, FeedbackItem
from app.models.rubric import RubricVersion
from app.schemas.agent import AgentResult
from app.services.knowledge_service import search_knowledge

logger = get_logger(__name__)
DIAGNOSTIC_NOTICE = "AI 评价属于教学诊断性参考；1-5 仅为诊断等级，不计算加权总分，不等同于正式考试评分。"
AGENT_SEQUENCE = [
    ("topic_agent", "分析作文审题、核心任务回应和立意", None),
    ("content_agent", "评价内容、论据和论证深度", "content"),
    ("structure_agent", "评价结构、段落和论证逻辑", "organization"),
    ("language_agent", "评价语言规范、准确性和表现力", "language"),
]


def _json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False)


class EvaluationOrchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.client = AgentLLMClient()

    def run(self, evaluation_id: int) -> None:
        evaluation = self.db.get(Evaluation, evaluation_id)
        if evaluation is None:
            logger.error("评价任务不存在 evaluation_id=%s", evaluation_id)
            return
        if evaluation.status not in (EvaluationStatus.PENDING, EvaluationStatus.FAILED):
            return
        essay = self.db.get(Essay, evaluation.essay_id)
        prompt = self.db.get(EssayPrompt, essay.prompt_id) if essay.prompt_id else None
        rubric = self.db.get(RubricVersion, evaluation.rubric_version_id)
        evaluation.status = EvaluationStatus.PROCESSING
        evaluation.error_message = None
        essay.status = EssayStatus.EVALUATING
        report = self.db.scalar(select(EvaluationReport).where(EvaluationReport.evaluation_id == evaluation.id))
        if report is None:
            report = EvaluationReport(evaluation_id=evaluation.id, execution_mode=self.client.execution_mode)
            self.db.add(report)
        report.execution_mode = self.client.execution_mode
        report.started_at = utc_now()
        report.completed_at = None
        report.quality_status = "processing"
        self.db.commit()

        try:
            knowledge = self._retrieve(evaluation, prompt)
            essay_context = {
                "essay_id": essay.id,
                "content_version": essay.content_version,
                "title": prompt.title if prompt else "自由作文",
                "requirements": prompt.requirements if prompt else "未提供额外写作要求",
                "content": essay.content,
                "rubric": json.loads(rubric.dimensions_json) if rubric else None,
                "diagnostic_rule": "仅输出 1-5 诊断等级，不输出正式总分",
            }
            knowledge_context = [item.model_dump() for item in knowledge.results]
            previous: list[AgentResult] = []
            for agent_name, task, _dimension in AGENT_SEQUENCE:
                previous.append(self._execute_agent(evaluation, essay_context, knowledge_context, previous, agent_name, task))

            feedback = self._execute_agent(
                evaluation, essay_context, knowledge_context, previous, "feedback_agent", "综合各维度结果并生成修改与训练建议"
            )
            quality = self._execute_agent(
                evaluation,
                essay_context,
                knowledge_context,
                previous + [feedback],
                "quality_agent",
                "审核证据、评分一致性、重复评价和结构完整性",
            )
            previous.extend([feedback, quality])
            quality = self._apply_backend_quality_checks(previous, quality)
            self._save_results(evaluation, report, previous, feedback, quality)
            evaluation.status = EvaluationStatus.COMPLETED
            evaluation.error_message = None
            essay.status = EssayStatus.COMPLETED
            report.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            logger.info("评价任务完成 evaluation_id=%s mode=%s", evaluation.id, self.client.execution_mode)
        except Exception as exc:
            logger.exception("评价任务失败 evaluation_id=%s", evaluation.id)
            self.db.rollback()
            evaluation = self.db.get(Evaluation, evaluation_id)
            essay = self.db.get(Essay, evaluation.essay_id)
            evaluation.status = EvaluationStatus.FAILED
            evaluation.error_message = str(exc)[:1500]
            essay.status = EssayStatus.FAILED
            report = self.db.scalar(select(EvaluationReport).where(EvaluationReport.evaluation_id == evaluation.id))
            if report is not None:
                report.quality_status = "failed"
                report.completed_at = utc_now()
                report.quality_issues_json = _json_dump([str(exc)[:500]])
            self.db.commit()

    def _retrieve(self, evaluation: Evaluation, prompt: EssayPrompt | None):
        title = prompt.title if prompt else "自由作文"
        query = f"{title} 内容 结构 语言 评价要求 常见问题 修改建议"
        response = search_knowledge(self.db, query=query, top_k=5, evaluation_id=evaluation.id)
        self.db.add(
            RetrievalLog(
                evaluation_id=evaluation.id,
                query=query,
                search_mode=response.search_mode,
                semantic=response.semantic,
                results_json=_json_dump([item.model_dump() for item in response.results]),
            )
        )
        self.db.commit()
        return response

    def _execute_agent(
        self,
        evaluation: Evaluation,
        essay_context: dict,
        knowledge_context: list[dict],
        previous: list[AgentResult],
        agent_name: str,
        task: str,
    ) -> AgentResult:
        started = time.perf_counter()
        input_summary = {
            "task": task,
            "essay_id": essay_context["essay_id"],
            "essay_version": essay_context["content_version"],
            "content_chars": len(essay_context["content"]),
            "knowledge_chunk_ids": [item["chunk_id"] for item in knowledge_context],
            "previous_agents": [item.agent_name for item in previous],
        }
        try:
            result, token_usage = self.client.execute(agent_name, task, essay_context, knowledge_context, previous)
            result = verify_agent_evidence(result, essay_context["content"])
            if not result.knowledge_refs:
                result.knowledge_refs = [str(item["chunk_id"]) for item in knowledge_context]
            latency_ms = round((time.perf_counter() - started) * 1000)
            self.db.add(
                AgentRun(
                    evaluation_id=evaluation.id,
                    agent_name=agent_name,
                    model_name=self.client.model_name,
                    prompt_version=AGENT_PROMPT_VERSION,
                    input_json=_json_dump(input_summary),
                    output_json=result.model_dump_json(),
                    status="completed",
                    latency_ms=latency_ms,
                    token_usage_json=_json_dump(token_usage) if token_usage else None,
                )
            )
            self.db.commit()
            return result
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000)
            self.db.add(
                AgentRun(
                    evaluation_id=evaluation.id,
                    agent_name=agent_name,
                    model_name=self.client.model_name,
                    prompt_version=AGENT_PROMPT_VERSION,
                    input_json=_json_dump(input_summary),
                    output_json="{}",
                    status="failed",
                    latency_ms=latency_ms,
                    error_message=str(exc)[:1000],
                )
            )
            self.db.commit()
            if isinstance(exc, AppError):
                raise
            raise AppError(f"{agent_name} 执行失败：{exc}") from exc

    def _apply_backend_quality_checks(self, results: list[AgentResult], quality: AgentResult) -> AgentResult:
        issues = list(quality.quality_issues)
        for result in results:
            if result.agent_name == "quality_agent":
                continue
            if result.agent_name != "feedback_agent" and not result.evidence:
                issues.append(f"{result.agent_name} 未提供原文证据")
            for evidence in result.evidence:
                if evidence.verified_status != "verified":
                    issues.append(f"{result.agent_name} 存在待核验证据：{evidence.match_type or 'pending'}")
            if result.diagnostic_score is not None:
                if result.diagnostic_score <= 2 and not result.problems:
                    issues.append(f"{result.agent_name} 诊断值较低但缺少问题说明")
                if result.diagnostic_score >= 4 and not result.strengths:
                    issues.append(f"{result.agent_name} 诊断值较高但缺少优点依据")
        if self.client.execution_mode == "mock" and "当前为 Mock 流程演示，未执行真实模型语义审核" not in issues:
            issues.append("当前为 Mock 流程演示，未执行真实模型语义审核")
        quality.quality_issues = list(dict.fromkeys(issues))
        quality.quality_status = "needs_review" if quality.quality_issues else (quality.quality_status or "passed")
        return quality

    def _save_results(
        self,
        evaluation: Evaluation,
        report: EvaluationReport,
        results: list[AgentResult],
        feedback: AgentResult,
        quality: AgentResult,
    ) -> None:
        self.db.query(DimensionScore).filter(DimensionScore.evaluation_id == evaluation.id).delete()
        self.db.query(FeedbackItem).filter(FeedbackItem.evaluation_id == evaluation.id).delete()
        for result in results:
            if result.dimension and result.diagnostic_score is not None:
                self.db.add(
                    DimensionScore(
                        evaluation_id=evaluation.id,
                        dimension=result.dimension,
                        original_score=result.diagnostic_score,
                        final_score=None,
                        max_score=5,
                    )
                )
            if result.agent_name == "quality_agent":
                continue
            dimension = result.dimension or ("overall" if result.agent_name == "feedback_agent" else "topic")
            entries = []
            if result.agent_name == "feedback_agent":
                entries.append(("summary", result.overall_summary or result.analysis))
            entries.extend(("strength", item) for item in result.strengths)
            entries.extend(("problem", item) for item in result.problems)
            if not entries:
                entries.append(("analysis", result.analysis))
            for category, content in entries:
                self.db.add(
                    FeedbackItem(
                        evaluation_id=evaluation.id,
                        dimension=dimension,
                        category=category,
                        content=content,
                        suggestion="；".join(result.suggestions) or None,
                        evidence_json=_json_dump([item.model_dump() for item in result.evidence]),
                        verified_status=evidence_verification_status(result),
                    )
                )
        report.overall_summary = feedback.overall_summary or feedback.analysis
        report.quality_status = quality.quality_status or "needs_review"
        report.quality_issues_json = _json_dump(quality.quality_issues)
        report.training_suggestions_json = _json_dump(feedback.training_suggestions)
        report.report_json = _json_dump(
            {
                "diagnostic_notice": DIAGNOSTIC_NOTICE,
                "execution_mode": self.client.execution_mode,
                "rubric_version_id": evaluation.rubric_version_id,
                "agents": [item.model_dump() for item in results],
                "formal_total_score": None,
            }
        )


def run_evaluation_task(evaluation_id: int) -> None:
    with SessionLocal() as db:
        EvaluationOrchestrator(db).run(evaluation_id)