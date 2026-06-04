"""특정 날짜 트래픽을 IP/UA/페이지/시간대/유입으로 분해해 진위(실유입 vs 위장봇/공격)를 진단.

referer가 google.com 인데 폭증한 경우, 진짜 검색 유입인지 referer 위조 봇인지 가린다.

사용 예:
    python manage.py diagnose_traffic                       # 어제 전체
    python manage.py diagnose_traffic --date 2026-06-03
    python manage.py diagnose_traffic --date 2026-06-03 --referer google
    python manage.py diagnose_traffic --referer google --top 20
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from badmintok.models import VisitorLog


class Command(BaseCommand):
    help = "특정 날짜 트래픽을 IP/UA/페이지/시간대로 분해해 진위를 진단"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default="", help="YYYY-MM-DD (기본: 어제)")
        parser.add_argument("--referer", type=str, default="", help="referer_domain 부분일치 필터 (예: google)")
        parser.add_argument("--top", type=int, default=15, help="각 항목 상위 N개")

    def handle(self, *args, **opts):
        top = opts["top"]
        now = timezone.localtime()
        if opts["date"]:
            day = datetime.strptime(opts["date"], "%Y-%m-%d").date()
        else:
            day = (now - timedelta(days=1)).date()

        start = timezone.make_aware(datetime(day.year, day.month, day.day))
        end = start + timedelta(days=1)

        qs = VisitorLog.objects.filter(visited_at__gte=start, visited_at__lt=end)
        if opts["referer"]:
            qs = qs.filter(referer_domain__icontains=opts["referer"])

        total = qs.count()
        uniq_ip = qs.values("ip_address").distinct().count()
        uniq_ua = qs.values("user_agent").distinct().count()
        uniq_sess = qs.values("session_key").distinct().count()

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== 트래픽 진단: {day} {'(referer~' + opts['referer'] + ')' if opts['referer'] else '(전체)'} ==="
        ))
        self.stdout.write(f"총 요청: {total:,}")
        self.stdout.write(f"고유 IP: {uniq_ip:,} / 고유 UA: {uniq_ua:,} / 고유 세션: {uniq_sess:,}")
        if total:
            self.stdout.write(
                f"→ 요청/고유IP = {total/max(uniq_ip,1):.1f}  (낮을수록 다양=실유입, 높을수록 소수IP집중=의심)"
            )

        def section(title, field, n=top):
            self.stdout.write(self.style.HTTP_INFO(f"\n[{title}] 상위 {n}"))
            rows = qs.values(field).annotate(c=Count("id")).order_by("-c")[:n]
            for r in rows:
                val = r[field]
                val = (str(val)[:70]) if val else "(없음)"
                pct = (r["c"] / total * 100) if total else 0
                self.stdout.write(f"  {r['c']:>7,} ({pct:4.1f}%)  {val}")

        section("device_type", "device_type")
        section("top IP", "ip_address")
        section("top User-Agent", "user_agent")
        section("top 랜딩 페이지", "url_path")
        section("referer_domain", "referer_domain")

        # 시간대별
        self.stdout.write(self.style.HTTP_INFO("\n[시간대별 분포 (KST)]"))
        by_hour = {}
        for v in qs.values_list("visited_at", flat=True):
            h = timezone.localtime(v).hour
            by_hour[h] = by_hour.get(h, 0) + 1
        for h in range(24):
            c = by_hour.get(h, 0)
            bar = "█" * int(c / max(max(by_hour.values(), default=1), 1) * 40)
            self.stdout.write(f"  {h:02d}시 {c:>6,} {bar}")

        self.stdout.write(self.style.WARNING(
            "\n판별: 소수 IP·소수 UA에 집중 + 특정 시각 폭증 = 위장봇/공격 의심. "
            "IP·UA·랜딩이 다양하고 시간대 자연스러우면 실유입.\n"
        ))
