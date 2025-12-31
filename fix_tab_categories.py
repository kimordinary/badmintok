"""카테고리 계층 구조 확인 스크립트"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Category, Tab

print("=" * 70)
print("CATEGORY HIERARCHY STRUCTURE")
print("=" * 70)

# 모든 카테고리 확인
categories = Category.objects.all().order_by('display_order', 'name')
parent_categories = categories.filter(parent__isnull=True)
child_categories = categories.filter(parent__isnull=False)

print(f"\nTotal categories: {categories.count()}")
print(f"  - Parent categories: {parent_categories.count()}")
print(f"  - Child categories: {child_categories.count()}")

print("\n" + "-" * 70)
print("HIERARCHY TREE")
print("-" * 70 + "\n")

# 계층 구조로 출력
for parent in parent_categories:
    print(f"{parent.name} (slug: {parent.slug}, order: {parent.display_order})")

    # 이 부모의 자식들
    children = categories.filter(parent=parent).order_by('display_order', 'name')
    for child in children:
        print(f"  |- {child.name} (slug: {child.slug}, order: {child.display_order})")

    if not children:
        print("  (no children)")
    print()

print("=" * 70)
