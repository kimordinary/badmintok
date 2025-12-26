"""
카테고리별 게시물과 source 확인 스크립트
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Post, Category

print("=== 배드민톡 카테고리별 게시물 ===")
badmintok_cat_slugs = [
    'news', 'reviews', 'brand', 'feed',
    'tournament', 'player', 'community', 'equipment',
    'racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories',
    'yonex', 'lining', 'victor', 'mizuno', 'technist',
    'strokus', 'redsun', 'trion', 'tricore', 'apacs'
]

badmintok_cats = Category.objects.filter(slug__in=badmintok_cat_slugs)
for cat in badmintok_cats:
    posts = Post.objects.filter(category=cat)
    sources = list(posts.values_list('source', flat=True).distinct())
    if posts.count() > 0:
        print(f'{cat.get_full_path()}: {posts.count()}개 - sources: {sources}')

print("\n=== 동호인톡 카테고리별 게시물 ===")
community_cat_slugs = ['free', 'review']
community_cats = Category.objects.filter(slug__in=community_cat_slugs)
for cat in community_cats:
    posts = Post.objects.filter(category=cat)
    sources = list(posts.values_list('source', flat=True).distinct())
    if posts.count() > 0:
        print(f'{cat.get_full_path()}: {posts.count()}개 - sources: {sources}')

print("\n=== 전체 게시물 source 분포 ===")
for source_choice in Post.Source.choices:
    source_value = source_choice[0]
    source_label = source_choice[1]
    count = Post.objects.filter(source=source_value).count()
    print(f'{source_label} ({source_value}): {count}개')
