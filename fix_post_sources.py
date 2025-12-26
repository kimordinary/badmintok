"""
게시물의 source를 카테고리에 맞게 수정하는 스크립트
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Post, Category

print("=== 게시물 source 수정 ===\n")

# 배드민톡 카테고리 slug 목록
badmintok_cat_slugs = [
    'news', 'reviews', 'brand', 'feed',
    'tournament', 'player', 'community', 'equipment',
    'racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories',
    'yonex', 'lining', 'victor', 'mizuno', 'technist',
    'strokus', 'redsun', 'trion', 'tricore', 'apacs'
]

# 동호인톡 카테고리 slug 목록
community_cat_slugs = ['free', 'review']

# 배드민톡 카테고리에 속한 게시물의 source를 'badmintok'으로 수정
badmintok_cats = Category.objects.filter(slug__in=badmintok_cat_slugs)
for cat in badmintok_cats:
    posts = Post.objects.filter(category=cat).exclude(source=Post.Source.BADMINTOK)
    for post in posts:
        old_source = post.source
        post.source = Post.Source.BADMINTOK
        post.save()
        print(f"[배드민톡] {post.id}: {post.title[:30]} - {old_source} -> {post.source}")

# 동호인톡 카테고리에 속한 게시물의 source를 'community'로 수정
community_cats = Category.objects.filter(slug__in=community_cat_slugs)
for cat in community_cats:
    posts = Post.objects.filter(category=cat).filter(source=Post.Source.BADMINTOK)
    for post in posts:
        old_source = post.source
        post.source = Post.Source.COMMUNITY
        post.save()
        print(f"[동호인톡] {post.id}: {post.title[:30]} - {old_source} -> {post.source}")

print("\n=== 수정 완료 ===")
