from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from centers.models import Center, CenterBookmark
from .serializers import CenterSerializer

# band 앱과 동일한 지역 그룹 매핑 재사용
from band.api.views import REGION_GROUPS


@api_view(["GET"])
@permission_classes([AllowAny])
def center_list(request):
    """배드민턴 센터 목록 API.

    쿼리: search, region, fallback, page, page_size
    응답 구조는 bands list와 동일.
    """
    qs = Center.objects.filter(is_published=True).annotate(
        bookmark_count_annotated=Count("bookmarks", distinct=True)
    )

    # 검색
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(address__icontains=search))

    # 지역 필터 (대분류 코드는 그룹 내 모든 세부 region 포함)
    region = request.GET.get("region", "").strip()
    is_fallback = False
    if region and region != "all":
        region_values = REGION_GROUPS.get(region, [region])
        filtered = qs.filter(region__in=region_values)
        if not filtered.exists() and request.GET.get("fallback", "").lower() == "true":
            is_fallback = True
        else:
            qs = filtered

    qs = qs.order_by("-created_at")

    # 페이지네이션
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 20)
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        if page_size < 1:
            page_size = 20
    except (ValueError, TypeError):
        page_size = 20

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page_number)
    serializer = CenterSerializer(page_obj, many=True, context={"request": request})

    return Response({
        "count": paginator.count,
        "page_size": page_size,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
        "previous": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "is_fallback": is_fallback,
        "results": serializer.data,
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def center_detail(request, center_id):
    """배드민턴 센터 상세 API."""
    center = get_object_or_404(
        Center.objects.annotate(
            bookmark_count_annotated=Count("bookmarks", distinct=True)
        ),
        id=center_id,
        is_published=True,
    )
    serializer = CenterSerializer(center, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def center_bookmark_toggle(request, center_id):
    """센터 북마크 토글 (로그인 필요)."""
    center = get_object_or_404(Center, id=center_id, is_published=True)
    bookmark = CenterBookmark.objects.filter(center=center, user=request.user).first()
    if bookmark:
        bookmark.delete()
        is_bookmarked = False
    else:
        CenterBookmark.objects.create(center=center, user=request.user)
        is_bookmarked = True
    return Response({
        "is_bookmarked": is_bookmarked,
        "bookmark_count": center.bookmarks.count(),
    }, status=status.HTTP_200_OK)
