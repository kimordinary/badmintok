"""기존 BandSchedule의 description에 적힌 '참가비: 8000원' 텍스트를
cost 필드로 일괄 마이그레이션한다. cost == 0 인 schedule만 처리.

사용:
    python manage.py migrate_schedule_costs --dry-run
    python manage.py migrate_schedule_costs
"""
from django.core.management.base import BaseCommand

from band.cost_utils import extract_cost_from_description
from band.models import BandSchedule


class Command(BaseCommand):
    help = "기존 BandSchedule description에서 참가비를 추출해 cost 필드로 이전"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="실제 저장하지 않고 결과만 출력")

    def handle(self, *args, **options):
        dry = options["dry_run"]

        qs = BandSchedule.objects.all().order_by("id")
        total = qs.count()
        zero_cost_qs = qs.filter(cost=0)
        candidates = zero_cost_qs.count()

        self.stdout.write(f"=== 번개 참가비 마이그레이션 ({'DRY RUN' if dry else '실제 실행'}) ===")
        self.stdout.write(f"전체 schedule: {total}건")
        self.stdout.write(f"cost=0 후보:   {candidates}건")
        self.stdout.write("")

        migrated = 0
        no_match_ids = []

        for sched in zero_cost_qs.iterator():
            extracted = extract_cost_from_description(sched.description or "")
            if extracted > 0:
                if not dry:
                    sched.cost = extracted
                    sched.save(update_fields=["cost", "updated_at"])
                migrated += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] id={sched.id} '{sched.title[:30]}' -> cost={extracted:,}원"
                ))
            else:
                # description에 참가비 텍스트도 없고 cost도 0인 경우는 정상 (무료)
                # description에 텍스트가 있는데 추출 실패한 경우만 따로 모음
                desc = sched.description or ""
                if "참가비" in desc or "비용" in desc:
                    no_match_ids.append(sched.id)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"=== 완료: {migrated}건 마이그레이션 ==="))
        if no_match_ids:
            self.stdout.write(self.style.WARNING(
                f"⚠ description에 '참가비'/'비용' 텍스트가 있으나 숫자 매칭 실패: "
                f"{len(no_match_ids)}건 -> {no_match_ids}"
            ))
