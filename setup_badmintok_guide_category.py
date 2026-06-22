#!/usr/bin/env python
"""배드민톡 '가이드' 단일 상위 카테고리 추가 스크립트

- source: badmintok
- slug: guide
- 위치: 가장 우측 (현재 최상위 카테고리 display_order 최댓값 + 10)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'badmintok.settings')
django.setup()

from django.db.models import Max
from community.models import Category


def setup_guide_category():
    existing = Category.objects.filter(
        source=Category.Source.BADMINTOK,
        slug='guide',
        parent__isnull=True,
    ).first()
    if existing:
        print(f'[SKIP] 이미 존재: {existing.name} (slug={existing.slug}, order={existing.display_order})')
        return existing

    max_order = Category.objects.filter(
        source=Category.Source.BADMINTOK,
        parent__isnull=True,
    ).aggregate(m=Max('display_order'))['m'] or 0

    guide = Category.objects.create(
        name='가이드',
        slug='guide',
        source=Category.Source.BADMINTOK,
        parent=None,
        display_order=max_order + 10,
        is_active=True,
    )
    print(f'[OK] 생성: {guide.name} (slug={guide.slug}, order={guide.display_order})')
    return guide


if __name__ == '__main__':
    setup_guide_category()
