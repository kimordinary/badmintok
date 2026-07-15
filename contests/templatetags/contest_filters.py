import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

# 대회 요강 본문에서 h3(섹션 제목)로 판정할 키워드
AI_SUMMARY_HEADING_KEYWORDS = (
    "개요", "참가비", "접수", "경기 일정", "종목", "급수 기준",
    "참가 자격", "경기 방식", "순위 결정", "환불 규정", "이의신청",
    "현장 안내", "참가 전 체크포인트",
)


def _is_ai_summary_heading(line):
    """단독 짧은 줄(10~60자)이면서 섹션 키워드를 포함하면 heading으로 판정."""
    length = len(line)
    if length < 10 or length > 60:
        return False
    # 문장(마침표 등으로 끝남)은 제목으로 보지 않음 → 오탐 방지
    if line[-1] in ".!?…。":
        return False
    return any(kw in line for kw in AI_SUMMARY_HEADING_KEYWORDS)


@register.filter
def short_weekday(value):
    """날짜에서 한 글자 요일 반환 (예: 토, 일)"""
    if hasattr(value, 'weekday'):
        return DAY_NAMES[value.weekday()]
    return ""


@register.filter
def bold_region(value):
    """
    장소 정보에서 [지역명] 부분만 볼드 처리
    예: "[부산] 부산 배드민턴 센터" -> "<strong>[부산]</strong> 부산 배드민턴 센터"
    """
    if not value:
        return value
    
    # [ ] 안의 내용을 찾아서 볼드 처리 및 브랜드 컬러 적용
    pattern = r'(\[[^\]]+\])'
    result = re.sub(pattern, r'<strong style="color: var(--brand);">\1</strong>', str(value))
    return mark_safe(result)


@register.filter
def ai_summary_html(value):
    """대회 요강 plain text를 SEO 본문 구조(h3/p)로 안전하게 렌더링.

    - 빈 줄 기준으로 문단을 분리하고, 문단 내 줄바꿈은 <br>로 보존
    - 단독 짧은 줄(10~60자)에 섹션 키워드가 있으면 <h3>, 나머지는 <p>
    - 입력에 HTML 태그가 있어도 escape 처리하여 그대로 렌더링하지 않음
    - 섹션 제목이 없으면 자연스럽게 일반 문단(<p>)만 생성되어 fallback 처리됨
    """
    if not value:
        return ""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    # 빈 줄(공백만 있는 줄 포함) 기준으로 블록 분리
    blocks = re.split(r"\n[ \t]*\n", text)

    html_parts = []
    for block in blocks:
        # 블록 앞뒤 빈 줄 제거
        lines = block.split("\n")
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            continue

        first = lines[0].strip()
        # 블록의 첫 줄이 섹션 제목이면 h3, 나머지 줄은 문단(p)으로 분리
        if _is_ai_summary_heading(first):
            html_parts.append("<h3>%s</h3>" % escape(first))
            rest = lines[1:]
            while rest and not rest[0].strip():
                rest.pop(0)
            if rest:
                html_parts.append("<p>%s</p>" % "<br>".join(escape(ln) for ln in rest))
        else:
            html_parts.append("<p>%s</p>" % "<br>".join(escape(ln) for ln in lines))

    return mark_safe("\n".join(html_parts))
