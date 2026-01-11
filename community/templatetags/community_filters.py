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


@register.filter
def add_nofollow_external(value):
    """외부 링크에만 rel="nofollow noopener noreferrer" 추가 (내부 링크는 유지)"""
    from django.utils.safestring import mark_safe

    if not value:
        return ""

    content_str = str(value)

    # <a> 태그를 찾아서 처리
    def process_link(match):
        full_tag = match.group(0)
        href = match.group(1)

        # 내부 링크 판단 (상대 경로 또는 badmintok.com 포함)
        is_internal = (
            not href.startswith('http') or  # 상대 경로
            'badmintok.com' in href or      # badmintok.com 도메인
            'localhost' in href or           # localhost (개발 환경)
            '127.0.0.1' in href              # 로컬 IP
        )

        # 내부 링크는 그대로 반환
        if is_internal:
            return full_tag

        # 외부 링크: rel 속성이 이미 있는지 확인
        if 'rel=' in full_tag:
            # rel 속성이 있으면 nofollow 추가/확인
            if 'nofollow' not in full_tag:
                # rel 속성에 nofollow 추가
                full_tag = re.sub(
                    r'rel=["\']([^"\']*)["\']',
                    r'rel="\1 nofollow noopener noreferrer"',
                    full_tag
                )
        else:
            # rel 속성이 없으면 추가
            # <a href="..." 다음에 rel 추가
            full_tag = re.sub(
                r'(<a\s+[^>]*href=["\'][^"\']*["\'])([^>]*>)',
                r'\1 rel="nofollow noopener noreferrer"\2',
                full_tag
            )

        # target="_blank"가 없으면 추가
        if 'target=' not in full_tag:
            full_tag = re.sub(
                r'(<a\s+[^>]*)>',
                r'\1 target="_blank">',
                full_tag
            )

        return full_tag

    # 모든 <a> 태그 처리
    pattern = r'<a\s+[^>]*href=["\']([^"\']*)["\'][^>]*>'
    result = re.sub(pattern, process_link, content_str)

    return mark_safe(result)
