"""60 分制总分口径的唯一事实来源，供评价编排、量规说明与教师复核复用。

口径（2026-11-18 v1.0.0）：三维原始分之和减去字数不足扣分得到 raw_total，
再按基准锚点线性校准到 [36.0, 58.0]，保留 1 位小数。
校准只改变总分落点，不改动任何维度原始分；raw_total 与校准参数随报告公开。
"""
SCORED_DIMENSIONS = ("content", "expression", "development")
TOTAL_MAX_SCORE = 60
ANCHOR_RAW = 36
ANCHOR_SCORE = 50.0
SLOPE = 0.5
CALIBRATED_MIN = 36.0
CALIBRATED_MAX = 58.0
CALIBRATION_VERSION = "v1.0-2026-11-18"
WORD_COUNT_FLOOR = 800
WORDS_PER_DEDUCTION = 100
DEDUCTION_MAX = 4


def compute_deduction(word_count: int) -> int:
    """字数不足扣分：每少 100 字扣 1 分，最多扣 4 分。"""
    return min(DEDUCTION_MAX, max(0, WORD_COUNT_FLOOR - word_count) // WORDS_PER_DEDUCTION)


def calibrate_total(raw_total: float) -> float:
    """按基准锚点把 raw 总分校准到 [36.0, 58.0]，保留 1 位小数。"""
    calibrated = ANCHOR_SCORE + (raw_total - ANCHOR_RAW) * SLOPE
    return round(max(CALIBRATED_MIN, min(CALIBRATED_MAX, calibrated)), 1)


def calibration_meta(deduction: int) -> dict:
    """公开的校准参数快照，随报告归档以便回溯。"""
    return {
        "anchor_raw": ANCHOR_RAW,
        "anchor_score": ANCHOR_SCORE,
        "slope": SLOPE,
        "min": CALIBRATED_MIN,
        "max": CALIBRATED_MAX,
        "deduction": deduction,
        "calibration_version": CALIBRATION_VERSION,
    }


def compose_total_score(dimension_scores: dict[str, float], word_count: int) -> tuple[float, dict]:
    """三维之和减去字数扣分得到 raw_total，再按基准锚点校准为 60 分制总分。"""
    base_total = sum(dimension_scores.get(dimension, 0) for dimension in SCORED_DIMENSIONS)
    deduction = compute_deduction(word_count)
    raw_total = base_total - deduction
    return calibrate_total(raw_total), {"raw_total": raw_total, "scoring_calibration": calibration_meta(deduction)}


def rubric_synthesis_text() -> str:
    """量规 synthesis 文案，与代码常量保持同一来源。"""
    return (
        "总分按量规基准校准合成，非三维简单相加："
        f"raw = 内容 + 表达 + 发展 - 字数扣分（每少 {WORDS_PER_DEDUCTION} 字扣 1 分、最多 {DEDUCTION_MAX} 分），"
        f"总分 = {ANCHOR_SCORE:g} + (raw - {ANCHOR_RAW}) × {SLOPE:g}，"
        f"限制在 {CALIBRATED_MIN:g}-{CALIBRATED_MAX:g} 并保留 1 位小数；校准前分数 raw_total 随报告公开。"
    )


def rubric_calibration_json() -> dict:
    return {
        "anchor_raw": ANCHOR_RAW,
        "anchor_score": ANCHOR_SCORE,
        "slope": SLOPE,
        "min": CALIBRATED_MIN,
        "max": CALIBRATED_MAX,
        "version": CALIBRATION_VERSION,
    }


def rubric_deductions_json() -> dict:
    return {
        "no_title": 2,
        "typo_per_char": 1,
        "typo_max": 5,
        "short_essay_per_100_chars": 1,
        "short_essay_deduction_max": DEDUCTION_MAX,
        "word_floor": WORD_COUNT_FLOOR,
    }