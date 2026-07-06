"""기존 배드민톡 글의 '브랜드 카테고리'를 '태그'로 이동한다.

브랜드(요넥스·리닝 등)는 카테고리가 아니라 태그로 관리하는 구조로 전환:
- categories(M2M)의 브랜드 → tags로 이동 후 제거
- category(메인 FK)가 브랜드면 → 태그로 옮기고, 유형 카테고리가 M2M에 있으면
  그것을 메인으로 교체(없으면 비움)

기본은 dry-run(미적용). 실제 반영은 --apply.
"""
from django.core.management.base import BaseCommand
from community.models import Post, Tag

BRAND_SLUGS = {
    "yonex", "lining", "victor", "mizuno", "apacs",
    "redsun", "strokus", "technist", "trion", "tricore",
}


class Command(BaseCommand):
    help = "배드민톡 글의 브랜드 카테고리를 태그로 이동한다."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="실제 적용 (미지정 시 dry-run)")
        parser.add_argument("--deactivate-empty-brands", action="store_true",
                            help="변환 후 글이 없는 브랜드 카테고리를 비활성화")

    def handle(self, *args, **opts):
        apply = opts["apply"]
        tag_by_slug = {t.slug: t for t in Tag.objects.filter(source="badmintok")}

        posts = Post.objects.filter(
            source=Post.Source.BADMINTOK
        ).select_related("category").prefetch_related("categories")

        moved = 0
        for p in posts:
            m2m_brands = [c for c in p.categories.all() if c.slug in BRAND_SLUGS]
            main_brand = p.category if (p.category and p.category.slug in BRAND_SLUGS) else None
            if not m2m_brands and not main_brand:
                continue

            slugs = {c.slug for c in m2m_brands}
            if main_brand:
                slugs.add(main_brand.slug)

            tags = [tag_by_slug[s] for s in slugs if s in tag_by_slug]
            missing = slugs - set(tag_by_slug)

            if apply:
                for t in tags:
                    p.tags.add(t)
                for c in m2m_brands:
                    p.categories.remove(c)
                if main_brand:
                    # 유형 카테고리(브랜드 아님)가 M2M에 남아있으면 메인으로, 없으면 비움
                    type_cat = next((c for c in p.categories.all()
                                     if c.slug not in BRAND_SLUGS), None)
                    p.category = type_cat
                    p.save(update_fields=["category"])

            warn = f"  ⚠ 태그없음:{missing}" if missing else ""
            self.stdout.write(f"  {p.title[:34]} → 태그 {sorted(slugs)}{warn}")
            moved += 1

        mode = "적용 완료" if apply else "DRY-RUN (미적용, --apply로 실제 반영)"
        self.stdout.write(self.style.SUCCESS(f"\n{mode} — 대상 글 {moved}개"))

        if opts["deactivate_empty_brands"]:
            from django.db.models import Count
            from community.models import Category
            empties = Category.objects.filter(
                source="badmintok", slug__in=BRAND_SLUGS, is_active=True,
            ).annotate(
                n_main=Count("posts", distinct=True),
                n_multi=Count("posts_multi", distinct=True),
            ).filter(n_main=0, n_multi=0)

            self.stdout.write("\n[글 없는 브랜드 카테고리 비활성]")
            n = 0
            empty_slugs = set()
            for c in empties:
                self.stdout.write(f"  {c.slug} 비활성")
                empty_slugs.add(c.slug)
                if apply:
                    c.is_active = False
                    c.save(update_fields=["is_active"])
                n += 1
            tail = "비활성 완료" if apply else "DRY-RUN"
            self.stdout.write(self.style.SUCCESS(f"  {tail} — {n}개"))

            # "브랜드" 탭(부모): 이번에 비활성될 하위 외에 활성 하위가 없으면 탭도 비활성
            brand_tab = Category.objects.filter(
                source="badmintok", slug="brand", parent__isnull=True,
            ).first()
            if brand_tab and brand_tab.is_active:
                active_kids = Category.objects.filter(parent=brand_tab, is_active=True)
                remaining = [c for c in active_kids if c.slug not in empty_slugs]
                if not remaining:
                    self.stdout.write("  → '브랜드' 탭 비활성 (하위 모두 태그 전환됨)")
                    if apply:
                        brand_tab.is_active = False
                        brand_tab.save(update_fields=["is_active"])
