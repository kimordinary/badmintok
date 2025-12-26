"""
동호인톡 글쓰기 페이지의 카테고리 계층 구조 확인
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Category, Tab

# 동호인톡 활성 탭의 카테고리만 포함
community_tabs = Tab.objects.filter(
    source=Tab.Source.COMMUNITY,
    is_active=True
).select_related('category')

# 탭에서 사용하는 카테고리 slug 목록 생성
allowed_category_slugs = set()
for tab in community_tabs:
    print(f"처리 중인 탭: {tab.name} (slug: {tab.slug})")
    if tab.category:
        print(f"  카테고리: {tab.category.name} (slug: {tab.category.slug})")
        allowed_category_slugs.add(tab.category.slug)
        # 하위 카테고리도 포함
        child_categories = Category.objects.filter(parent=tab.category, is_active=True)
        print(f"  하위 카테고리 수: {child_categories.count()}")
        for child in child_categories:
            print(f"    - {child.name} (slug: {child.slug})")
        allowed_category_slugs.update(child_categories.values_list('slug', flat=True))
    else:
        print(f"  카테고리 없음")
    print()

print("=== 허용된 카테고리 slug 목록 ===")
print(sorted(allowed_category_slugs))
print()

# allowed_category_slugs가 비어있으면 모든 카테고리 허용
if allowed_category_slugs:
    all_categories = list(Category.objects.filter(
        slug__in=allowed_category_slugs,
        is_active=True
    ).exclude(
        slug='hot'
    ).select_related('parent').order_by("display_order", "name"))
else:
    all_categories = list(Category.objects.filter(
        is_active=True
    ).exclude(
        slug='hot'
    ).select_related('parent').order_by("display_order", "name"))

print(f"=== 조회된 카테고리 수: {len(all_categories)} ===")
for cat in all_categories:
    parent_str = f" (parent: {cat.parent.name})" if cat.parent else " (최상위)"
    print(f"  {cat.name} (slug: {cat.slug}){parent_str}")
print()

def build_hierarchy():
    """계층 구조 리스트 생성"""
    hierarchy = []
    parents = [c for c in all_categories if c.parent is None]
    print(f"최상위 카테고리 수: {len(parents)}")
    for p in parents:
        print(f"  - {p.name} (slug: {p.slug})")

    for parent in parents:
        # 해당 parent의 children 찾기
        children = [c for c in all_categories if c.parent_id == parent.id]

        if children:
            # children이 있으면 parent를 상위 카테고리로 표시
            parent.has_children = True
            hierarchy.append(parent)
            for child in children:
                child.has_children = False
            hierarchy.extend(children)
        else:
            # children이 없으면 선택 가능한 일반 카테고리로 표시
            parent.has_children = False
            hierarchy.append(parent)

    return hierarchy

categories = build_hierarchy()

print("\n=== 동호인톡 글쓰기 카테고리 계층 구조 ===\n")

if categories:
    for cat in categories:
        indent = '  ' if hasattr(cat, 'parent') and cat.parent else ''
        has_children_str = ' [상위 카테고리 - 선택 불가]' if hasattr(cat, 'has_children') and cat.has_children else ''
        parent_info = f' (parent: {cat.parent.name})' if hasattr(cat, 'parent') and cat.parent else ''
        print(f'{indent}{cat.name} (id: {cat.id}, slug: {cat.slug}){parent_info}{has_children_str}')
else:
    print("카테고리가 없습니다.")
