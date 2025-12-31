"""Tab 데이터를 Category source로 마이그레이션"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Category, Tab

print("=" * 70)
print("MIGRATING TAB DATA TO CATEGORY SOURCE")
print("=" * 70)

# 1. Tab과 연결된 Category들의 source 업데이트
tabs = Tab.objects.filter(category__isnull=False)

print(f"\nFound {tabs.count()} tabs with categories")

for tab in tabs:
    category = tab.category

    # 부모 카테고리의 source 업데이트
    if category.source != tab.source:
        old_source = category.source
        category.source = tab.source
        category.save()
        print(f"Updated {category.name}: {old_source} -> {tab.source}")

    # 자식 카테고리들도 같은 source로 업데이트
    children = Category.objects.filter(parent=category)
    for child in children:
        if child.source != tab.source:
            old_source = child.source
            child.source = tab.source
            child.save()
            print(f"  Updated child {child.name}: {old_source} -> {tab.source}")

print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

# 검증
badmintok_count = Category.objects.filter(source='badmintok').count()
community_count = Category.objects.filter(source='community').count()

print(f"\nBadmintok categories: {badmintok_count}")
print(f"Community categories: {community_count}")

print("\nBadmintok top-level categories:")
for cat in Category.objects.filter(source='badmintok', parent__isnull=True).order_by('display_order'):
    print(f"  - {cat.name}")
    children = Category.objects.filter(parent=cat)
    for child in children:
        print(f"      - {child.name}")

print("\nCommunity top-level categories:")
for cat in Category.objects.filter(source='community', parent__isnull=True).order_by('display_order'):
    print(f"  - {cat.name}")
    children = Category.objects.filter(parent=cat)
    for child in children:
        print(f"      - {child.name}")

print("\n" + "=" * 70)
print("DONE!")
print("=" * 70)
