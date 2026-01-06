from django.apps import AppConfig


class BadmintokConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'badmintok'
    verbose_name = '배드민톡'

    def ready(self):
        """앱 초기화 시 커스텀 admin 사이트 설정"""
        from django.contrib import admin
        from .admin import BadmintokAdminSite

        # 기본 admin 사이트를 커스텀 사이트로 교체
        admin.site.__class__ = BadmintokAdminSite
