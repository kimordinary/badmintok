"""Center 모델 데이터를 Band(band_type='center')로 이전한다.

사용법:
    python manage.py migrate_centers_to_bands --dry-run
    python manage.py migrate_centers_to_bands
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from band.models import Band, BandBookmark
from centers.models import Center, CenterBookmark


class Command(BaseCommand):
    help = "Center -> Band(band_type='center') 일괄 이전"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="실제 저장하지 않고 결과만 출력")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        centers = Center.objects.all().order_by("id")
        total = centers.count()

        self.stdout.write(f"=== Center -> Band 이전: {total}건 ({'DRY RUN' if dry else '실제 실행'}) ===")

        migrated = 0
        skipped = 0
        bookmark_migrated = 0

        for c in centers:
            # 동일 이름 + created_by + band_type='center' 가 이미 있으면 스킵 (재실행 안전성)
            existing = Band.objects.filter(
                name=c.name,
                band_type="center",
                created_by=c.created_by,
            ).first()
            if existing:
                self.stdout.write(f"  [SKIP] '{c.name}' 이미 Band(id={existing.id})로 이전됨")
                skipped += 1
                # 북마크 이전만 시도
                if not dry:
                    bookmark_migrated += self._migrate_bookmarks(c, existing)
                continue

            band_kwargs = dict(
                name=c.name,
                description=(c.description or "")[:500],
                detailed_description=c.description or "",
                band_type="center",
                region=c.region,
                categories="center",
                cover_image=c.cover_image or None,
                profile_image=c.profile_image or None,
                is_public=c.is_published,
                join_approval_required=False,
                is_approved=True,
                created_by=c.created_by,
                facility_address=c.address or "",
                facility_address_detail=c.address_detail or "",
                facility_phone=c.phone or "",
                facility_operating_hours=c.operating_hours or "",
                facility_pricing=c.pricing or "",
                facility_court_count=c.court_count or 0,
                facility_amenities=c.amenities or "",
                facility_latitude=c.latitude,
                facility_longitude=c.longitude,
            )

            if dry:
                self.stdout.write(f"  [DRY] '{c.name}' (region={c.region}) 이전 예정")
                migrated += 1
                continue

            with transaction.atomic():
                band = Band.objects.create(**band_kwargs)
                bookmark_migrated += self._migrate_bookmarks(c, band)

            migrated += 1
            self.stdout.write(self.style.SUCCESS(f"  [OK] '{c.name}' -> Band(id={band.id})"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"=== 완료: 이전 {migrated}건, 스킵 {skipped}건, 북마크 이전 {bookmark_migrated}건 ==="
        ))

    def _migrate_bookmarks(self, center, band):
        """CenterBookmark -> BandBookmark."""
        n = 0
        for cb in CenterBookmark.objects.filter(center=center):
            _, created = BandBookmark.objects.get_or_create(band=band, user=cb.user)
            if created:
                n += 1
        return n
