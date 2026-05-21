from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import is_site_admin
from centers.models import Center, CenterBookmark
from .serializers import CenterSerializer, CenterWriteSerializer

# band 앱과 동일한 지역 그룹 매핑 재사용
from band.api.views import REGION_GROUPS


def _serialize_center(center, request):
    """detail 응답에서 bookmark_count_annotated 주입 후 직렬화."""
    center = Center.objects.annotate(
        bookmark_count_annotated=Count("bookmarks", distinct=True)
    ).get(pk=center.pk)
    return CenterSerializer(center, context={"request": request}).data


@api_view(["GET"])
@permission_classes([AllowAny])
def center_list(request):
    """배드민턴 센터 목록 API.

    쿼리: search, region, fallback, page, page_size
    """
    qs = Center.objects.filter(is_published=True).select_related("created_by").annotate(
        bookmark_count_annotated=Count("bookmarks", distinct=True)
    )

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(address__icontains=search))

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


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def center_detail(request, center_id):
    """배드민턴 센터 상세 / 수정 / 삭제 API.

    GET: 누구나
    PATCH/DELETE: 작성자(created_by) 또는 사이트 관리자
    """
    if request.method == "GET":
        center = get_object_or_404(
            Center.objects.select_related("created_by").annotate(
                bookmark_count_annotated=Count("bookmarks", distinct=True)
            ),
            id=center_id,
            is_published=True,
        )
        serializer = CenterSerializer(center, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PATCH / DELETE: 로그인 필요
    if not request.user.is_authenticated:
        return Response({"detail": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED)

    center = get_object_or_404(Center, id=center_id)

    if not (is_site_admin(request.user) or center.created_by_id == request.user.id):
        return Response({"detail": "수정/삭제 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "DELETE":
        center.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = CenterWriteSerializer(center, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(_serialize_center(center, request), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def center_create(request):
    """배드민턴 센터 등록 (로그인 필요)."""
    serializer = CenterWriteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    center = serializer.save(created_by=request.user)
    return Response(_serialize_center(center, request), status=status.HTTP_201_CREATED)


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
