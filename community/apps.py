from django.apps import AppConfig


class CommunityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'community'
    verbose_name = '동호인톡'

    def ready(self):
        """앱 초기화 시 signal 등록"""
        import community.models  # signal이 등록되도록 models 모듈 import
