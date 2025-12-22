from community.models import Category


def community_categories(request):
    """커뮤니티 카테고리를 모든 템플릿에 제공"""
    return {
        'community_categories': Category.objects.filter(is_active=True).order_by('display_order', 'name'),
    }

