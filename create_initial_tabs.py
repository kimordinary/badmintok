"""
초기 탭 데이터 생성 스크립트
배드민톡과 동호인톡의 기본 탭을 생성합니다.
"""

from community.models import Category, Tab

# 배드민톡 탭 생성
badmintok_tabs = [
    {"name": "뉴스", "slug": "news", "category_slug": "news", "display_order": 1},
    {"name": "리뷰", "slug": "reviews", "category_slug": "reviews", "display_order": 2},
    {"name": "브랜드관", "slug": "brand", "category_slug": "brands", "display_order": 3},
    {"name": "피드", "slug": "feed", "category_slug": "feed", "display_order": 4},
]

badmintok_created = 0
for tab_data in badmintok_tabs:
    try:
        category = Category.objects.get(slug=tab_data["category_slug"], is_active=True)
        tab, created = Tab.objects.get_or_create(
            slug=tab_data["slug"],
            source=Tab.Source.BADMINTOK,
            defaults={
                "name": tab_data["name"],
                "category": category,
                "display_order": tab_data["display_order"],
                "is_active": True,
            }
        )
        if created:
            badmintok_created += 1
    except Category.DoesNotExist:
        pass

# 동호인톡 탭 생성
community_tabs = [
    {"name": "리뷰", "slug": "reviews", "category_slug": "reviews", "display_order": 1},
]

community_created = 0
for tab_data in community_tabs:
    try:
        category = Category.objects.get(slug=tab_data["category_slug"], is_active=True)
        tab, created = Tab.objects.get_or_create(
            slug=tab_data["slug"],
            source=Tab.Source.COMMUNITY,
            defaults={
                "name": tab_data["name"],
                "category": category,
                "display_order": tab_data["display_order"],
                "is_active": True,
            }
        )
        if created:
            community_created += 1
    except Category.DoesNotExist:
        pass

print(f"Created {badmintok_created} badmintok tabs and {community_created} community tabs")
