"""显式 Mock 规则引擎：仅演示流程，不进行或冒充大模型语义推理。"""
import re

from app.schemas.agent import AgentResult, EvidenceItem

MOCK_MODEL_NAME = "mock-rule-based-v1"


def _paragraph_evidence(essay_content: str, paragraph_index: int, reason: str, suggestion: str) -> list[EvidenceItem]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", essay_content) if part.strip()]
    if not paragraphs:
        return []
    paragraph = paragraphs[min(paragraph_index, len(paragraphs) - 1)]
    quote = paragraph[: min(90, len(paragraph))]
    start = essay_content.find(quote)
    return [
        EvidenceItem(
            quote=quote,
            start_char=start if start >= 0 else None,
            end_char=start + len(quote) if start >= 0 else None,
            reason=f"Mock 规则选取的原文位置：{reason}",
            suggestion=suggestion,
        )
    ]


def _score(essay_content: str, dimension: str) -> int:
    paragraphs = [part for part in re.split(r"\n\s*\n", essay_content) if part.strip()]
    connectors = ("因此", "但是", "首先", "其次", "最后", "同时", "然而", "所以")
    if dimension == "content":
        return min(5, 2 + int(len(essay_content) >= 350) + int(any(word in essay_content for word in ("例如", "比如", "案例", "事实"))))
    if dimension == "organization":
        return min(5, 2 + int(len(paragraphs) >= 3) + int(any(word in essay_content for word in connectors)))
    return min(5, 2 + int(len(essay_content) >= 250) + int("，" in essay_content and "。" in essay_content))


def run_mock_agent(
    agent_name: str,
    task: str,
    essay_content: str,
    previous_results: list[AgentResult] | None = None,
) -> AgentResult:
    previous_results = previous_results or []
    paragraphs = len([part for part in re.split(r"\n\s*\n", essay_content) if part.strip()])
    common = {
        "agent_name": agent_name,
        "task": task,
        "status": "completed",
        "confidence": 0.0,
    }
    if agent_name == "topic_agent":
        return AgentResult(
            **common,
            analysis=f"Mock 规则分析（非模型推理）：检测到作文共 {len(essay_content)} 字、{paragraphs} 个段落。Mock 不会判断真实题意或是否偏题，仅提供流程演示输出。",
            evidence=_paragraph_evidence(essay_content, 0, "开头段落供审题流程展示", "真实模式下应结合作文题目核查核心任务回应情况"),
            suggestions=["Mock 建议：请人工核对题目关键词、写作任务与文章中心是否一致"],
        )

    dimension_map = {
        "content_agent": ("content", "内容", 1, "补充具体论据，并解释论据与中心观点之间的关系"),
        "structure_agent": ("organization", "组织", 1, "检查段落功能、论证顺序以及段间衔接"),
        "language_agent": ("language", "语言", 0, "检查长句、搭配、指代和句式变化，避免只堆砌修辞"),
    }
    if agent_name in dimension_map:
        dimension, label, paragraph_index, suggestion = dimension_map[agent_name]
        score = _score(essay_content, dimension)
        return AgentResult(
            **common,
            dimension=dimension,
            diagnostic_score=score,
            grade=f"诊断等级 {score}/5（非正式分数）",
            analysis=f"Mock 规则分析（非模型推理）：{label}维度仅根据字数、段落和连接词等表面特征生成诊断值 {score}/5，不代表对{label}质量的语义判断。",
            evidence=_paragraph_evidence(essay_content, paragraph_index, f"{label}维度流程证据", suggestion),
            suggestions=[f"Mock 建议：{suggestion}"],
            strengths=[f"Mock 可核验特征：作文包含 {paragraphs} 个段落，正文 {len(essay_content)} 字"],
            problems=["Mock 无法识别该维度的深层语义问题，需真实模型或教师进一步诊断"],
        )

    if agent_name == "feedback_agent":
        scores = {item.dimension: item.diagnostic_score for item in previous_results if item.diagnostic_score is not None}
        weakest = min(scores, key=scores.get) if scores else "content"
        return AgentResult(
            **common,
            analysis="Mock 汇总（非模型推理）：已收集审题、内容、结构、语言 Agent 的结构化结果，仅进行字段汇总，不生成虚构综合评价。",
            overall_summary="本次为 Mock 流程演示：系统已完成多 Agent 调度、RAG 记录、结构化结果和证据位置校验；作文的实际质量需由真实模型或教师判断。",
            evidence=[evidence for result in previous_results for evidence in result.evidence][:4],
            strengths=["已形成内容、组织、语言三维度的诊断性记录"],
            problems=["Mock 模式不具备语义理解能力，不能据此判断作文真实水平"],
            suggestions=["切换到真实模型后复核诊断内容，或由教师直接复核"],
            training_suggestions=[f"建议优先人工检查 {weakest} 维度，再确定训练任务；Mock 不自动下结论"],
        )

    if agent_name == "quality_agent":
        return AgentResult(
            **common,
            analysis="Mock 质量检查：仅确认输出字段完整，证据位置由后端独立核验；Mock 不判断观点是否准确，因此结果始终需要人工复核。",
            quality_status="needs_review",
            quality_issues=["当前为 Mock 流程演示，未执行真实模型语义审核"],
            suggestions=["真实模型模式下仍需保留后端证据核验和教师复核"],
        )

    raise ValueError(f"未知 Agent：{agent_name}")