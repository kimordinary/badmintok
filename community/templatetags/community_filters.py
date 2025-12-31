import re
from django import template

register = template.Library()


@register.filter
def timesince_simple(value):
    """timesince 결과에서 첫 번째 단위만 반환 (예: '4시간, 22분' -> '4시간')"""
    if not value:
        return ""
    
    time_str = str(value)
    if ',' in time_str:
        return time_str.split(',')[0].strip()
    return time_str.strip()


@register.filter
def extract_first_image(value):
    """HTML content에서 첫 번째 이미지 URL 추출"""
    if not value:
        return None
    
    content_str = str(value)
    # <img src="..." 또는 <img src='...' 형식에서 src 값 추출
    pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    match = re.search(pattern, content_str, re.IGNORECASE)
    
    if match:
        return match.group(1)
    return None


@register.filter
def mask_email(value):
    """이메일 주소를 마스킹 (예: now_68@example.com -> now_68***)"""
    if not value:
        return ""

    email_str = str(value)
    if '@' in email_str:
        # @ 앞부분만 추출하고 *** 추가
        local_part = email_str.split('@')[0]
        return f"{local_part}***"
    # @가 없으면 처음 3글자만
    return f"{email_str[:3]}***"


@register.filter
def get_item(dictionary, key):
    """딕셔너리에서 키로 값을 가져오는 필터"""
    if not dictionary:
        return None
    return dictionary.get(key)
