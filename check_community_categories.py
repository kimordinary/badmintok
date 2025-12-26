"""
동호인톡 페이지의 모든 카테고리 확인 스크립트
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Category, Tab, Post

print("=== 1. 동호인톡 탭과 연결된 카테고리 ===\n")
community_tabs = Tab.objects.filter(source='community').order_by('display_order')
for t in community_tabs:
    category_info = t.category.get_full_path() if t.category else "카테고리 없음"
    print(f"{t.name} (slug: {t.slug}, 활성: {t.is_active}) -> {category_info}")

print("\n=== 2. 동호인톡 리뷰 카테고리 계층 구조 ===\n")
review_cat = Category.objects.filter(slug='community-reviews').first()
if review_cat:
    print(f"{review_cat.name} (id: {review_cat.id}, slug: {review_cat.slug}, 활성: {review_cat.is_active})")
    children = Category.objects.filter(parent=review_cat).order_by('display_order')
    for c in children:
        post_count = Post.objects.filter(category=c).count()
        print(f"  -> {c.name} (id: {c.id}, slug: {c.slug}, 활성: {c.is_active}, 게시물: {post_count}개)")
else:
    print("동호인톡 리뷰 카테고리를 찾을 수 없습니다.")

print("\n=== 3. 기타 동호인톡 관련 카테고리 ===\n")
# 동호인톡에서 사용될 수 있는 카테고리 slug들
community_slugs = ['free', 'review', 'match', 'tournament', 'court', 'lesson']
other_cats = Category.objects.filter(slug__in=community_slugs)
for c in other_cats:
    parent_info = c.parent.name if c.parent else "없음"
    post_count = Post.objects.filter(category=c).count()
    print(f"{c.name} (id: {c.id}, slug: {c.slug}, parent: {parent_info}, 활성: {c.is_active}, 게시물: {post_count}개)")

print("\n=== 4. 배드민톡 카테고리 (참고용) ===\n")
# 배드민톡 상위 카테고리
badmintok_parents = Category.objects.filter(slug__in=['news', 'reviews', 'brand', 'feed'], parent__isnull=True)
for p in badmintok_parents:
    print(f"{p.name} (id: {p.id}, slug: {p.slug})")
    children = Category.objects.filter(parent=p).order_by('display_order')
    for c in children:
        post_count = Post.objects.filter(category=c).count()
        print(f"  -> {c.name} (id: {c.id}, slug: {c.slug}, 게시물: {post_count}개)")

print("\n=== 5. 모든 최상위 카테고리 (parent가 없는) ===\n")
root_cats = Category.objects.filter(parent__isnull=True).order_by('display_order', 'name')
for c in root_cats:
    child_count = Category.objects.filter(parent=c).count()
    post_count = Post.objects.filter(category=c).count()
    print(f"{c.name} (id: {c.id}, slug: {c.slug}, 활성: {c.is_active}, 하위 카테고리: {child_count}개, 게시물: {post_count}개)")

print("\n=== 6. 사용되지 않는 카테고리 (게시물 0개 + 탭 연결 안됨) ===\n")
all_categories = Category.objects.all()
used_category_ids = set()

# 탭에 연결된 카테고리
for tab in Tab.objects.all():
    if tab.category:
        used_category_ids.add(tab.category.id)
        # 하위 카테고리도 포함
        children = Category.objects.filter(parent=tab.category)
        used_category_ids.update(children.values_list('id', flat=True))

# 게시물이 있는 카테고리
categories_with_posts = Post.objects.values_list('category_id', flat=True).distinct()
used_category_ids.update(categories_with_posts)

unused_categories = []
for cat in all_categories:
    if cat.id not in used_category_ids:
        unused_categories.append(cat)

if unused_categories:
    for c in unused_categories:
        parent_info = c.parent.name if c.parent else "없음"
        print(f"{c.name} (id: {c.id}, slug: {c.slug}, parent: {parent_info}, 활성: {c.is_active})")
else:
    print("사용되지 않는 카테고리가 없습니다.")
