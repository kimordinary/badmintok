"""Admin 카테고리 정렬 순서 테스트"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Category, Tab
from django.db.models import Q, Case, When

print("=" * 70)
print("BADMINTOK CATEGORY ADMIN ORDER TEST")
print("=" * 70)

# 배드민톡 탭과 연결된 카테고리들 찾기
badmintok_tab_categories = Tab.objects.filter(
    source='badmintok',
    category__isnull=False
).values_list('category_id', flat=True)

print(f"\nBadmintok tab categories: {list(badmintok_tab_categories)}")

# 해당 카테고리들과 그 자식들
all_categories = Category.objects.filter(
    Q(id__in=badmintok_tab_categories) |
    Q(parent_id__in=badmintok_tab_categories)
)

print(f"\nTotal categories found: {all_categories.count()}")

# 계층 구조로 정렬
ordered_pks = []
parents = all_categories.filter(parent__isnull=True).order_by('display_order', 'name')

print(f"\nParent categories: {parents.count()}")
for parent in parents:
    print(f"  - {parent.name} (pk={parent.pk}, order={parent.display_order})")

print("\n" + "=" * 70)
print("EXPECTED ORDER:")
print("=" * 70)

for parent in parents:
    # 부모 추가
    ordered_pks.append(parent.pk)
    print(f"\n{parent.name} (pk={parent.pk})")

    # 이 부모의 자식들 추가
    children = all_categories.filter(parent=parent).order_by('display_order', 'name')
    for child in children:
        ordered_pks.append(child.pk)
        print(f"  - {child.name} (pk={child.pk}, order={child.display_order})")

print("\n" + "=" * 70)
print("FINAL PK ORDER:")
print(f"{ordered_pks}")
print("=" * 70)

# 실제 queryset 테스트
if ordered_pks:
    preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_pks)])
    final_qs = all_categories.filter(pk__in=ordered_pks).order_by(preserved_order)

    print("\nFINAL QUERYSET ORDER:")
    for idx, cat in enumerate(final_qs):
        indent = "  - " if cat.parent else ""
        print(f"{idx+1}. {indent}{cat.name} (pk={cat.pk}, parent={cat.parent})")
