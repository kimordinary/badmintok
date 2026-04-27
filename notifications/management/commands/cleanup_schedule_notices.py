"""일정 종료 후 일정 시간 경과한 SCHEDULE_NOTICE 알림을 정리한다.

cron으로 매일 1회 실행:
    python manage.py cleanup_schedule_notices --days=7
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from band.models import BandSchedule
from notifications.models import Notification


class Command(BaseCommand):
    help = "종료된 일정의 SCHEDULE_NOTICE 알림 일괄 삭제"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="일정 종료 후 N일 경과한 알림 삭제 (기본 7)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        cutoff = timezone.now() - timedelta(days=days)

        ended_ids = list(
            BandSchedule.objects.filter(
                Q(end_datetime__lt=cutoff)
                | (Q(end_datetime__isnull=True) & Q(start_datetime__lt=cutoff))
            ).values_list("id", flat=True)
        )

        if not ended_ids:
            self.stdout.write("삭제 대상 일정이 없습니다.")
            return

        deleted, _ = Notification.objects.filter(
            type=Notification.Type.SCHEDULE_NOTICE,
            related_band_schedule_id__in=ended_ids,
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"종료된 일정 {len(ended_ids)}건 → SCHEDULE_NOTICE 알림 {deleted}개 삭제"
            )
        )
