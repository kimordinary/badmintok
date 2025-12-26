"""
배드민톡 카테고리 계층 구조 설정 스크립트
상위 카테고리(뉴스, 리뷰, 브랜드, 피드)를 생성하고 기존 카테고리들의 parent 설정
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Category, Tab


def setup_category_hierarchy():
    """카테고리 계층 구조 설정"""

    # 1. 상위 카테고리 생성
    parent_categories = [
        {
            'name': '뉴스',
            'slug': 'news',
            'display_order': 1,
            'children_slugs': ['tournament', 'player', 'community']
        },
        {
            'name': '리뷰',
            'slug': 'reviews',
            'display_order': 2,
            'children_slugs': ['racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories']
        },
        {
            'name': '브랜드',
            'slug': 'brand',
            'display_order': 3,
            'children_slugs': ['yonex', 'lining', 'victor', 'mizuno', 'technist', 'strokus', 'redsun', 'trion', 'tricore', 'apacs']
        },
        {
            'name': '피드',
            'slug': 'feed',
            'display_order': 4,
            'children_slugs': []
        }
    ]

    print("=== 배드민톡 카테고리 계층 구조 설정 ===\n")

    for parent_data in parent_categories:
        # 상위 카테고리 생성 또는 업데이트
        parent, created = Category.objects.get_or_create(
            slug=parent_data['slug'],
            defaults={
                'name': parent_data['name'],
                'display_order': parent_data['display_order'],
                'is_active': True
            }
        )

        if created:
            print(f"[+] 상위 카테고리 생성: {parent.name} ({parent.slug})")
        else:
            # 기존 카테고리가 있으면 업데이트
            parent.name = parent_data['name']
            parent.display_order = parent_data['display_order']
            parent.is_active = True
            parent.parent = None  # 상위 카테고리는 parent가 없음
            parent.save()
            print(f"[*] 상위 카테고리 업데이트: {parent.name} ({parent.slug})")

        # 하위 카테고리들의 parent 설정
        for child_slug in parent_data['children_slugs']:
            try:
                child = Category.objects.get(slug=child_slug)
                child.parent = parent
                child.save()
                print(f"  -> 하위 카테고리 연결: {child.name} ({child.slug})")
            except Category.DoesNotExist:
                print(f"  [!] 하위 카테고리를 찾을 수 없음: {child_slug}")

        print()

    # 2. Tab의 category 필드 업데이트 (상위 카테고리로 변경)
    print("=== Tab의 category 필드 업데이트 ===\n")
    tab_category_mapping = {
        'news': 'news',
        'reviews': 'reviews',
        'brand': 'brand',
        'feed': 'feed'
    }

    for tab_slug, category_slug in tab_category_mapping.items():
        try:
            tab = Tab.objects.get(slug=tab_slug, source=Tab.Source.BADMINTOK)
            category = Category.objects.get(slug=category_slug)
            tab.category = category
            tab.save()
            print(f"[+] Tab '{tab.name}' -> Category '{category.name}' 연결")
        except Tab.DoesNotExist:
            print(f"[!] Tab을 찾을 수 없음: {tab_slug}")
        except Category.DoesNotExist:
            print(f"[!] Category를 찾을 수 없음: {category_slug}")

    print("\n=== 설정 완료 ===")
    print("카테고리 계층 구조:")

    # 결과 확인
    for parent in Category.objects.filter(parent__isnull=True, is_active=True).order_by('display_order'):
        print(f"\n{parent.name} ({parent.slug})")
        children = Category.objects.filter(parent=parent, is_active=True).order_by('display_order', 'name')
        for child in children:
            print(f"  -> {child.name} ({child.slug})")


if __name__ == "__main__":
    setup_category_hierarchy()
