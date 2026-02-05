from django.apps import AppConfig


class BadmintokConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'badmintok'
    verbose_name = '배드민톡'

    def ready(self):
        """앱 초기화 시 admin 커스터마이징"""
        # Unfold 사용으로 커스텀 AdminSite 제거
        # 통계 URL은 admin.py에서 admin.site.get_urls를 오버라이드하여 추가
        pass
