#!/usr/bin/env python
"""배드민톡 카테고리 계층 구조 설정 스크립트"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'badmintok.settings')
django.setup()

from community.models import Category

def setup_badmintok_categories():
    """배드민톡 카테고리 계층 구조 생성"""

    # 1. 상위 카테고리 생성
    news_cat, _ = Category.objects.get_or_create(
        slug='news',
        defaults={
            'name': '뉴스',
            'display_order': 10,
            'is_active': True
        }
    )
    print(f'[OK] Created parent category: {news_cat.name}')

    reviews_cat, _ = Category.objects.get_or_create(
        slug='reviews',
        defaults={
            'name': '리뷰',
            'display_order': 20,
            'is_active': True
        }
    )
    print(f'[OK] Created parent category: {reviews_cat.name}')

    brands_cat, _ = Category.objects.get_or_create(
        slug='brands',
        defaults={
            'name': '브랜드관',
            'display_order': 30,
            'is_active': True
        }
    )
    print(f'[OK] Created parent category: {brands_cat.name}')

    feed_cat, _ = Category.objects.get_or_create(
        slug='feed',
        defaults={
            'name': '피드',
            'display_order': 40,
            'is_active': True
        }
    )
    print(f'[OK] Created independent category: {feed_cat.name}')

    # 2. 뉴스 하위 카테고리 연결
    news_children = ['tournament', 'player', 'equipment', 'community']
    for idx, slug in enumerate(news_children):
        cat = Category.objects.filter(slug=slug).first()
        if cat:
            cat.parent = news_cat
            cat.display_order = (idx + 1) * 10
            cat.save()
            print(f'  -> Linked {cat.name} under News')

    # 3. 리뷰 하위 카테고리 연결
    reviews_children = ['racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories']
    for idx, slug in enumerate(reviews_children):
        cat = Category.objects.filter(slug=slug).first()
        if cat:
            cat.parent = reviews_cat
            cat.display_order = (idx + 1) * 10
            cat.save()
            print(f'  -> Linked {cat.name} under Reviews')

    # 4. 브랜드관 하위 카테고리 연결
    brands_children = ['yonex', 'lining', 'victor', 'mizuno', 'technist',
                       'strokus', 'redsun', 'trion', 'tricore', 'apacs']
    for idx, slug in enumerate(brands_children):
        cat = Category.objects.filter(slug=slug).first()
        if cat:
            cat.parent = brands_cat
            cat.display_order = (idx + 1) * 10
            cat.save()
            print(f'  -> Linked {cat.name} under Brands')

    print('\n[DONE] Badmintok category hierarchy setup completed!')
    print('\n=== Final Structure ===')
    print('News')
    print('  - tournament, player, equipment, community')
    print('Reviews')
    print('  - racket, shoes, apparel, shuttlecock, protective, accessories')
    print('Brands')
    print('  - yonex, lining, victor, mizuno, technist, strokus, redsun, trion, tricore, apacs')
    print('Feed (independent)')

if __name__ == '__main__':
    setup_badmintok_categories()
