import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


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
