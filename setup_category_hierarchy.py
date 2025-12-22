"""카테고리 계층 구조 설정 스크립트"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'badmintok.settings')
django.setup()

from community.models import Category

# 상위 카테고리 생성 또는 가져오기
news_parent, _ = Category.objects.get_or_create(
    slug='news',
    defaults={
        'name': '뉴스',
        'display_order': 1
    }
)

review_parent, _ = Category.objects.get_or_create(
    slug='reviews',
    defaults={
        'name': '리뷰',
        'display_order': 2
    }
)

brand_parent, _ = Category.objects.get_or_create(
    slug='brands',
    defaults={
        'name': '브랜드',
        'display_order': 3
    }
)

# 뉴스 하위 카테고리 설정
news_children = ['tournament', 'player', 'equipment', 'community']
for slug in news_children:
    try:
        cat = Category.objects.get(slug=slug)
        cat.parent = news_parent
        cat.save()
        print(f"[OK] {cat.name} -> News")
    except Category.DoesNotExist:
        print(f"[SKIP] {slug} category not found")

# 리뷰 하위 카테고리 설정
review_children = ['racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories']
for slug in review_children:
    try:
        cat = Category.objects.get(slug=slug)
        cat.parent = review_parent
        cat.save()
        print(f"[OK] {cat.name} -> Review")
    except Category.DoesNotExist:
        print(f"[SKIP] {slug} category not found")

# 브랜드 하위 카테고리 설정
brand_children = ['yonex', 'lining', 'victor', 'mizuno', 'technist', 'strokus', 'redsun', 'trion', 'tricore', 'apacs']
for slug in brand_children:
    try:
        cat = Category.objects.get(slug=slug)
        cat.parent = brand_parent
        cat.save()
        print(f"[OK] {cat.name} -> Brand")
    except Category.DoesNotExist:
        print(f"[SKIP] {slug} category not found")

print("\n카테고리 계층 구조 설정 완료!")
