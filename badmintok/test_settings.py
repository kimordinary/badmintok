"""로컬 테스트 전용 설정: 운영 MySQL 대신 인메모리 SQLite 사용.

사용: python manage.py test <app> --settings=badmintok.test_settings
"""
from badmintok.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# 테스트 속도/단순화
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
