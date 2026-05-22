"""번개(BandSchedule) 참가비 관련 헬퍼.

description 안에 자유 텍스트로 적힌 "참가비: 8000원" 같은 표기를
cost 필드(IntegerField, 원 단위)로 정규화하기 위한 공통 함수.
"""
import re

# 매칭: "참가비 8000원" / "참가비: 8,000원" / "비용: 5000" 등
COST_PATTERN = re.compile(r"(?:참가비|비용)\s*[:.]?\s*([0-9,]+)\s*원?", re.IGNORECASE)


def extract_cost_from_description(description: str) -> int:
    """description 텍스트에서 참가비 숫자를 추출. 매칭 실패 시 0 반환."""
    if not description:
        return 0
    m = COST_PATTERN.search(description)
    if not m:
        return 0
    raw = m.group(1).replace(",", "").strip()
    try:
        return int(raw)
    except ValueError:
        return 0


def resolve_cost(cost_input, description: str) -> int:
    """schedule 저장 직전 cost 값 결정.

    - cost_input 이 None 또는 0 이면 description에서 추출 시도
    - cost_input 이 양수이면 그대로 사용 (사용자 명시 입력 우선)
    """
    try:
        cost_val = int(cost_input) if cost_input not in (None, "") else 0
    except (TypeError, ValueError):
        cost_val = 0

    if cost_val > 0:
        return cost_val
    return extract_cost_from_description(description or "")
