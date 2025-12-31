# Generated manually to fix badmintok category sources

from django.db import migrations


def update_badmintok_sources(apps, schema_editor):
    """배드민톡 카테고리들의 source를 'badmintok'으로 업데이트"""
    Category = apps.get_model('community', 'Category')

    # 상위 카테고리 (탭) slug 리스트
    badmintok_tab_slugs = ['news', 'reviews', 'brand', 'feed']

    # 1. 배드민톡 탭들의 source 업데이트
    updated_tabs = Category.objects.filter(
        slug__in=badmintok_tab_slugs,
        parent__isnull=True
    ).update(source='badmintok')

    print(f"Updated {updated_tabs} parent categories to badmintok")

    # 2. 배드민톡 탭의 하위 카테고리들 source 업데이트
    badmintok_parents = Category.objects.filter(
        slug__in=badmintok_tab_slugs,
        parent__isnull=True
    )

    updated_children = 0
    for parent in badmintok_parents:
        count = Category.objects.filter(parent=parent).update(source='badmintok')
        updated_children += count

    print(f"Updated {updated_children} child categories to badmintok")


def reverse_update(apps, schema_editor):
    """롤백: 배드민톡 카테고리들을 다시 community로 되돌림"""
    Category = apps.get_model('community', 'Category')

    badmintok_tab_slugs = ['news', 'reviews', 'brand', 'feed']

    # 탭과 하위 카테고리 모두 community로 변경
    Category.objects.filter(
        slug__in=badmintok_tab_slugs,
        parent__isnull=True
    ).update(source='community')

    badmintok_parents = Category.objects.filter(
        slug__in=badmintok_tab_slugs,
        parent__isnull=True
    )

    for parent in badmintok_parents:
        Category.objects.filter(parent=parent).update(source='community')


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0018_alter_tab_unique_together_remove_tab_category_and_more'),
    ]

    operations = [
        migrations.RunPython(update_badmintok_sources, reverse_update),
    ]
