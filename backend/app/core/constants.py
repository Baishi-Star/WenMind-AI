"""争议归因标签与维度到 Agent 的追溯映射。"""

ISSUE_TAGS = {
    "factual_error": "事实性错误（引用不存在的原文）",
    "scoring_bias": "评分偏差（评分与评价标准不一致）",
    "expression_misjudgment": "表达误判（有意表达被判定为错误）",
    "evaluation_omission": "评价遗漏（遗漏重要优点或问题）",
    "unreasonable_suggestion": "建议不合理（建议不符合上下文）",
    "other": "其他问题",
}

DIMENSION_AGENT = {
    "content": "content_agent",
    "organization": "structure_agent",
    "language": "language_agent",
    "topic": "topic_agent",
    "overall": "feedback_agent",
}

REASON_TAG_MAP = {
    "evidence_mismatch": "factual_error",
    "score_low": "scoring_bias",
    "rubric_disagreement": "scoring_bias",
    "creative_expression_misjudged": "expression_misjudgment",
    "intent_misunderstood": "expression_misjudgment",
    "missed_strength": "evaluation_omission",
    "other": "other",
}