import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


def generate_password(length=24):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "업로더용 service account(bot)를 생성/갱신합니다."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="봇 계정 이메일")
        parser.add_argument("--name", default="uploader-bot", help="활동명")
        parser.add_argument("--password", help="직접 비밀번호 지정(미지정 시 자동 생성)")
        parser.add_argument("--reset-password", action="store_true", help="기존 계정 비밀번호 재설정")

    def handle(self, *args, **opts):
        User = get_user_model()
        email = opts["email"]
        name = opts["name"]
        password = opts["password"] or generate_password()

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "activity_name": name,
                "is_staff": True,
                "is_active": True,
            },
        )
        if not created:
            if not user.is_staff:
                user.is_staff = True
            if not user.is_active:
                user.is_active = True
            if opts["reset_password"] or opts["password"]:
                user.set_password(password)
            user.save()
            action = "업데이트"
        else:
            user.set_password(password)
            user.save()
            action = "생성"

        self.stdout.write(self.style.SUCCESS(f"Service account {action} 완료"))
        self.stdout.write(f"  email    : {user.email}")
        self.stdout.write(f"  name     : {user.activity_name}")
        self.stdout.write(f"  is_staff : {user.is_staff}")
        if created or opts["reset_password"] or opts["password"]:
            self.stdout.write(self.style.WARNING(f"  password : {password}"))
            self.stdout.write(self.style.WARNING("  ↑ 안전한 곳에 즉시 저장하세요. 다시 조회할 수 없습니다."))
