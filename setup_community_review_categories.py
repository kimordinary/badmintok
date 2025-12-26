"""
동호인톡 리뷰 카테고리 및 하위 카테고리 생성 스크립트
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Category, Tab

print("=== 동호인톡 리뷰 카테고리 생성 ===\n")

# 상위 카테고리: 동호인톡 리뷰
parent_category, created = Category.objects.get_or_create(
    slug='community-reviews',
    defaults={
        'name': '동호인 리뷰',
        'display_order': 100,
        'is_active': True
    }
)

if created:
    print(f"[+] 상위 카테고리 생성: {parent_category.name} (slug: {parent_category.slug})")
else:
    parent_category.name = '동호인 리뷰'
    parent_category.display_order = 100
    parent_category.is_active = True
    parent_category.parent = None
    parent_category.save()
    print(f"[*] 상위 카테고리 업데이트: {parent_category.name} (slug: {parent_category.slug})")

# 하위 카테고리 생성 (배드민톡 리뷰와 동일한 구조, 이름에 prefix 추가)
sub_categories = [
    {'name': '동호인 라켓', 'slug': 'community-racket', 'display_order': 1},
    {'name': '동호인 신발/가방', 'slug': 'community-shoes', 'display_order': 2},
    {'name': '동호인 의류', 'slug': 'community-apparel', 'display_order': 3},
    {'name': '동호인 셔틀콕', 'slug': 'community-shuttlecock', 'display_order': 4},
    {'name': '동호인 보호대', 'slug': 'community-protective', 'display_order': 5},
    {'name': '동호인 기타/용품', 'slug': 'community-accessories', 'display_order': 6},
]

for sub_cat_data in sub_categories:
    sub_cat, created = Category.objects.get_or_create(
        slug=sub_cat_data['slug'],
        defaults={
            'name': sub_cat_data['name'],
            'parent': parent_category,
            'display_order': sub_cat_data['display_order'],
            'is_active': True
        }
    )

    if created:
        print(f"  [+] 하위 카테고리 생성: {sub_cat.name} (slug: {sub_cat.slug})")
    else:
        sub_cat.name = sub_cat_data['name']
        sub_cat.parent = parent_category
        sub_cat.display_order = sub_cat_data['display_order']
        sub_cat.is_active = True
        sub_cat.save()
        print(f"  [*] 하위 카테고리 업데이트: {sub_cat.name} (slug: {sub_cat.slug})")

print("\n=== 동호인톡 리뷰 탭 설정 ===")

# 기존 reviews 탭을 활성화하고 새 카테고리 연결
try:
    tab = Tab.objects.get(slug='reviews', source='community')
    tab.is_active = True
    tab.name = '리뷰'
    tab.category = parent_category
    tab.display_order = 2  # 인기글(1) 다음
    tab.save()
    print(f"[*] 리뷰 탭 활성화 및 업데이트: {tab.name} -> {tab.category.name}")
except Tab.DoesNotExist:
    tab = Tab.objects.create(
        slug='reviews',
        source='community',
        name='리뷰',
        category=parent_category,
        display_order=2,
        is_active=True
    )
    print(f"[+] 리뷰 탭 생성: {tab.name} -> {tab.category.name}")

print("\n=== 설정 완료 ===")
print("카테고리 계층 구조:")
print(f"\n{parent_category.name} (slug: {parent_category.slug})")
children = Category.objects.filter(parent=parent_category, is_active=True).order_by('display_order')
for child in children:
    print(f"  -> {child.name} (slug: {child.slug})")
