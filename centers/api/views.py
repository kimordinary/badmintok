"""센터 API 뷰.

내부적으로 Band 모델(band_type='center')을 사용하지만, 외부 API는
기존 Center API와 호환되도록 유지된다.
"""
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import is_site_admin
from band.models import Band, BandBookmark
from .serializers import CenterSerializer, CenterWriteSerializer

# band 앱과 동일한 지역 그룹 매핑 재사용
from band.api.views import REGION_GROUPS


def _center_queryset():
    """band_type='center' 인 Band만 조회하는 베이스 쿼리셋."""
    return Band.objects.filter(band_type="center", is_public=True)


def _serialize_with_annotation(band_id, request):
    band = _center_queryset().annotate(
        bookmark_count_annotated=Count("bookmarks", distinct=True)
    ).get(pk=band_id)
    return CenterSerializer(band, context={"request": request}).data


@api_view(["GET"])
@permission_classes([AllowAny])
def center_list(request):
    """배드민턴 센터 목록 API (band_type='center' 데이터)."""
    qs = _center_queryset().select_related("created_by").annotate(
        bookmark_count_annotated=Count("bookmarks", distinct=True)
    )

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(facility_address__icontains=search))

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
    """배드민턴 센터 상세 / 수정 / 삭제 API."""
    if request.method == "GET":
        band = get_object_or_404(
            _center_queryset().select_related("created_by").annotate(
                bookmark_count_annotated=Count("bookmarks", distinct=True)
            ),
            id=center_id,
        )
        return Response(
            CenterSerializer(band, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    if not request.user.is_authenticated:
        return Response({"detail": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED)

    band = get_object_or_404(Band, id=center_id, band_type="center")

    if not (is_site_admin(request.user) or band.created_by_id == request.user.id):
        return Response({"detail": "수정/삭제 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "DELETE":
        band.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CenterWriteSerializer(band, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(_serialize_with_annotation(band.id, request), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def center_create(request):
    """배드민턴 센터 등록 (로그인 필요)."""
    serializer = CenterWriteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    band = serializer.save(
        created_by=request.user,
        band_type="center",
        categories="center",
        is_public=True,
        is_approved=True,
    )
    return Response(_serialize_with_annotation(band.id, request), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def center_bookmark_toggle(request, center_id):
    """센터 북마크 토글 (로그인 필요)."""
    band = get_object_or_404(Band, id=center_id, band_type="center", is_public=True)
    bookmark = BandBookmark.objects.filter(band=band, user=request.user).first()
    if bookmark:
        bookmark.delete()
        is_bookmarked = False
    else:
        BandBookmark.objects.create(band=band, user=request.user)
        is_bookmarked = True
    return Response({
        "is_bookmarked": is_bookmarked,
        "bookmark_count": band.bookmarks.count(),
    }, status=status.HTTP_200_OK)
