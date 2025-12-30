from django import template
import re

register = template.Library()

@register.filter
def remove_datetime(value):
    """
    제목에서 날짜/시간 패턴을 제거합니다.
    예: "배드민톡 - 2026-01-10 19:00" -> "배드민톡"
    """
    if not value:
        return value

    # " - YYYY-MM-DD HH:MM" 패턴 제거
    pattern = r'\s*-\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}.*$'
    result = re.sub(pattern, '', str(value))

    return result.strip()
