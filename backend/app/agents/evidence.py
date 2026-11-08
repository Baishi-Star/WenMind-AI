"""原文证据后端核验：不允许把模型返回的引用直接视为已验证事实。"""
from app.schemas.agent import AgentResult, EvidenceItem


def verify_evidence_item(evidence: EvidenceItem, essay_content: str) -> EvidenceItem:
    quote = evidence.quote.strip()
    if not quote:
        evidence.verified_status = "unverified"
        evidence.match_type = "empty_quote"
        return evidence
    if (
        evidence.start_char is not None
        and evidence.end_char is not None
        and 0 <= evidence.start_char < evidence.end_char <= len(essay_content)
        and essay_content[evidence.start_char : evidence.end_char] == quote
    ):
        evidence.verified_status = "verified"
        evidence.match_type = "exact_position"
        return evidence

    positions: list[int] = []
    start = 0
    while True:
        position = essay_content.find(quote, start)
        if position < 0:
            break
        positions.append(position)
        start = position + 1
    if len(positions) == 1:
        evidence.start_char = positions[0]
        evidence.end_char = positions[0] + len(quote)
        evidence.verified_status = "verified"
        evidence.match_type = "corrected_unique_match"
    elif len(positions) > 1:
        evidence.verified_status = "unverified"
        evidence.match_type = "multiple_matches"
    else:
        evidence.verified_status = "unverified"
        evidence.match_type = "not_found"
    return evidence


def verify_agent_evidence(result: AgentResult, essay_content: str) -> AgentResult:
    result.evidence = [verify_evidence_item(item, essay_content) for item in result.evidence]
    return result


def evidence_verification_status(result: AgentResult) -> str:
    if not result.evidence:
        return "pending"
    if all(item.verified_status == "verified" for item in result.evidence):
        return "verified"
    if any(item.verified_status == "unverified" for item in result.evidence):
        return "unverified"
    return "pending"