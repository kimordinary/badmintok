"""인플레이션이 발생한 과거 VisitorLog 정리.

다음 행을 삭제 대상으로 본다:
    1) url_path가 /api/ 로 시작 (API 호출이 페이지뷰로 잡힌 케이스)
    2) device_type='bot' (자동화/크롤러)
    3) url_path가 명백한 비-콘텐츠 경로 (/sw.js, /manifest.json, /ads.txt, /.well-known/*)

cron이 아닌 일회성 명령. --dry-run 으로 영향 범위 먼저 확인 권장.

사용 예:
    python manage.py cleanup_inflated_visitor_logs --dry-run
    python manage.py cleanup_inflated_visitor_logs           # 실제 삭제
    python manage.py cleanup_inflated_visitor_logs --batch 5000
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from badmintok.models import VisitorLog


NON_CONTENT_PREFIXES = (
    "/api/",
    "/sw.js",
    "/manifest.json",
    "/ads.txt",
    "/.well-known/",
)


class Command(BaseCommand):
    help = "API 호출/봇 트래픽 등 인플레이션을 일으킨 과거 VisitorLog 일괄 정리"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="실제 삭제하지 않고 영향 범위만 출력",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=10000,
            help="한 번에 삭제할 행 수 (기본 10000)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch = options["batch"]

        # 1) /api/ 등 비-콘텐츠 경로
        path_q = Q()
        for prefix in NON_CONTENT_PREFIXES:
            path_q |= Q(url_path__startswith=prefix)

        path_qs = VisitorLog.objects.filter(path_q)
        path_count = path_qs.count()

        # 2) device_type='bot'
        bot_qs = VisitorLog.objects.filter(device_type="bot")
        bot_count = bot_qs.count()

        # 두 조건 합쳤을 때 중복 제거된 총 영향 행 수
        total_qs = VisitorLog.objects.filter(path_q | Q(device_type="bot"))
        total_count = total_qs.count()

        before_total = VisitorLog.objects.count()

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.NOTICE("VisitorLog 인플레이션 정리"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"전체 VisitorLog : {before_total:>10,}건")
        self.stdout.write(f"비-콘텐츠 경로  : {path_count:>10,}건  ({', '.join(NON_CONTENT_PREFIXES)})")
        self.stdout.write(f"봇 트래픽       : {bot_count:>10,}건  (device_type='bot')")
        self.stdout.write(f"삭제 대상(합산) : {total_count:>10,}건  (중복 제외)")
        self.stdout.write(f"남게 될 행 수   : {before_total - total_count:>10,}건")
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(self.style.WARNING("--dry-run: 실제 삭제하지 않았습니다."))
            return

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("삭제할 행이 없습니다."))
            return

        # 배치 단위 삭제 (테이블 큰 경우 락 최소화)
        deleted = 0
        while True:
            ids = list(total_qs.values_list("id", flat=True)[:batch])
            if not ids:
                break
            n, _ = VisitorLog.objects.filter(id__in=ids).delete()
            deleted += n
            self.stdout.write(f"  ... {deleted:,}건 삭제 진행")

        after_total = VisitorLog.objects.count()
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"완료: {deleted:,}건 삭제. {before_total:,} → {after_total:,}"
        ))
