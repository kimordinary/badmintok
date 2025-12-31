# Generated manually to fix badmintok category display_order

from django.db import migrations


def fix_badmintok_display_order(apps, schema_editor):
    """배드민톡 하위 카테고리의 display_order를 각 부모별로 1부터 시작하도록 수정"""
    Category = apps.get_model('community', 'Category')

    # 배드민톡 상위 카테고리들 (탭)
    badmintok_parents = Category.objects.filter(
        source='badmintok',
        parent__isnull=True
    ).order_by('display_order')

    total_updated = 0

    # 각 부모별로 자식 카테고리의 display_order를 1부터 재설정
    for parent in badmintok_parents:
        children = Category.objects.filter(
            parent=parent,
            source='badmintok'
        ).order_by('display_order')

        # 자식 카테고리를 1, 2, 3, ... 순서로 재설정
        for index, child in enumerate(children, start=1):
            child.display_order = index
            child.save(update_fields=['display_order'])
            total_updated += 1
            print(f"Updated {child.name} (parent: {parent.name}): display_order = {index}")

    print(f"Total updated: {total_updated} child categories")


def reverse_fix(apps, schema_editor):
    """롤백: 이전 상태로 되돌림 (10, 20, 30 단위)"""
    Category = apps.get_model('community', 'Category')

    # 뉴스 탭 (parent_id=24)
    news_children = [
        ('tournament', 10),
        ('player', 11),
        ('equipment', 12),
        ('community', 13),
    ]

    # 리뷰 탭 (parent_id=25)
    reviews_children = [
        ('racket', 20),
        ('shoes', 21),
        ('apparel', 22),
        ('shuttlecock', 23),
        ('protective', 24),
        ('accessories', 25),
    ]

    # 브랜드 탭 (parent_id=26)
    brand_children = [
        ('yonex', 30),
        ('lining', 31),
        ('victor', 32),
        ('mizuno', 33),
        ('technist', 34),
        ('strokus', 35),
        ('redsun', 36),
        ('trion', 37),
        ('tricore', 38),
        ('apacs', 39),
    ]

    all_mappings = news_children + reviews_children + brand_children

    for slug, order in all_mappings:
        try:
            category = Category.objects.get(slug=slug, source='badmintok')
            category.display_order = order
            category.save(update_fields=['display_order'])
        except Category.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0019_update_badmintok_category_source'),
    ]

    operations = [
        migrations.RunPython(fix_badmintok_display_order, reverse_fix),
    ]
