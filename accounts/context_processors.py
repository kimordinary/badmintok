from django.conf import settings

def social_login_settings(request):
    """소셜 로그인 설정을 모든 템플릿에서 사용 가능하도록"""
    return {
        'KAKAO_CLIENT_ID': settings.KAKAO_CLIENT_ID,
        'KAKAO_REDIRECT_URI': settings.KAKAO_REDIRECT_URI,
        'NAVER_CLIENT_ID': settings.NAVER_CLIENT_ID,
        'NAVER_REDIRECT_URI': settings.NAVER_REDIRECT_URI,
        'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID,
        'GOOGLE_REDIRECT_URI': settings.GOOGLE_REDIRECT_URI,
    }
