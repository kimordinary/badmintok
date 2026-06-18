from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import is_site_admin
from band.api.views import REGION_GROUPS
from badmintok.models import BadmintokBanner, Notice
from centers.models import Center, CenterBookmark

REGION_CHOICES = Center.Region.choices

# band 페이지와 동일한 권역 옵션 (사이드/모바일 가로 스크롤용)
REGION_OPTIONS_FULL = [
    ("all", "전체"),
    ("capital", "수도권"),
    ("busan", "영남권"),
    ("daegu", "대구권"),
    ("gwangju", "호남권"),
    ("daejeon", "충청권"),
    ("ulsan", "울산권"),
    ("jeju", "제주권"),
]


def _user_can_manage(user, center):
    # 사이트 관리자 · 등록자 · 지정된 센터 관리자(CenterManager)
    return center.is_managed_by(user)


def _load_banner_images():
    """band 페이지와 동일한 배너 데이터 형식."""
    banner_images = []
    for banner in BadmintokBanner.objects.filter(is_active=True):
        if not banner.image:
            continue
        banner_images.append({
            "url": banner.image.url,
            "alt": banner.alt_text or banner.title or "",
            "link_url": banner.link_url,
        })
    return banner_images


def center_list(request):
    """센터 목록 페이지 (band 페이지와 동일 구조)."""
    qs = Center.objects.filter(is_published=True).select_related("created_by").annotate(
        bookmark_count_annotated=Count("bookmarks", distinct=True),
    )

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(address__icontains=search))

    region = request.GET.get("region", "").strip()
    if region and region != "all":
        region_values = REGION_GROUPS.get(region, [region])
        qs = qs.filter(region__in=region_values)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # 내가 등록한 센터 (band의 my_bands 대응)
    my_centers = []
    if request.user.is_authenticated:
        my_centers = list(
            Center.objects.filter(created_by=request.user, is_published=True)
            .order_by("-created_at")[:5]
        )

    # 사용자별 북마크 여부 (카드 표시는 안 하지만 호환용)
    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(
            CenterBookmark.objects.filter(
                user=request.user,
                center__in=[c.pk for c in page_obj]
            ).values_list("center_id", flat=True)
        )

    return render(request, "center/list.html", {
        "centers": page_obj,
        "my_centers": my_centers,
        "search": search,
        "current_type": "center",
        "current_region": region or "all",
        "regions": REGION_OPTIONS_FULL,
        "banner_images": _load_banner_images(),
        "pinned_notice": Notice.objects.filter(is_pinned=True).order_by("-created_at").first(),
        "bookmarked_ids": bookmarked_ids,
    })


def center_detail(request, center_id):
    """센터 상세 페이지."""
    center = get_object_or_404(
        Center.objects.select_related("created_by").annotate(
            bookmark_count_annotated=Count("bookmarks", distinct=True)
        ),
        id=center_id,
        is_published=True,
    )
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = CenterBookmark.objects.filter(
            center=center, user=request.user
        ).exists()

    return render(request, "center/detail.html", {
        "center": center,
        "can_manage": _user_can_manage(request.user, center),
        "is_bookmarked": is_bookmarked,
        "amenities_list": [s.strip() for s in (center.amenities or "").split(",") if s.strip()],
    })


@login_required
def center_create(request):
    """센터 등록 폼."""
    if request.method == "POST":
        center = _save_center_form(request, instance=None)
        if center:
            messages.success(request, "센터가 등록되었습니다.")
            return redirect("center:detail", center_id=center.id)

    return render(request, "center/form.html", {
        "mode": "create",
        "center": None,
        "region_options": [
            {"value": v, "label": l}
            for v, l in REGION_CHOICES if v != "all"
        ],
    })


@login_required
def center_update(request, center_id):
    """센터 수정 폼."""
    center = get_object_or_404(Center, id=center_id)
    if not _user_can_manage(request.user, center):
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("center:detail", center_id=center.id)

    if request.method == "POST":
        updated = _save_center_form(request, instance=center)
        if updated:
            messages.success(request, "센터 정보가 수정되었습니다.")
            return redirect("center:detail", center_id=center.id)

    return render(request, "center/form.html", {
        "mode": "update",
        "center": center,
        "region_options": [
            {"value": v, "label": l}
            for v, l in REGION_CHOICES if v != "all"
        ],
    })


@login_required
@require_POST
def center_delete(request, center_id):
    """센터 삭제."""
    center = get_object_or_404(Center, id=center_id)
    if not _user_can_manage(request.user, center):
        messages.error(request, "삭제 권한이 없습니다.")
        return redirect("center:detail", center_id=center.id)
    center.delete()
    messages.success(request, "센터가 삭제되었습니다.")
    return redirect("center:list")


@login_required
@require_POST
def center_bookmark_toggle(request, center_id):
    """센터 북마크 토글 (웹 폼 POST)."""
    center = get_object_or_404(Center, id=center_id, is_published=True)
    bookmark = CenterBookmark.objects.filter(center=center, user=request.user).first()
    if bookmark:
        bookmark.delete()
    else:
        CenterBookmark.objects.create(center=center, user=request.user)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/center/"
    return HttpResponseRedirect(next_url)


# === helpers ===

def _save_center_form(request, instance=None):
    """폼 데이터로 Center 인스턴스 생성/수정. 검증 실패 시 None 반환."""
    name = request.POST.get("name", "").strip()
    region = request.POST.get("region", "").strip()
    address = request.POST.get("address", "").strip()

    if not name:
        messages.error(request, "센터명은 필수입니다.")
        return None
    if region not in {v for v, _ in REGION_CHOICES}:
        messages.error(request, "올바른 지역을 선택해주세요.")
        return None
    if not address:
        messages.error(request, "주소는 필수입니다.")
        return None

    center = instance or Center(created_by=request.user)
    center.name = name
    center.region = region
    center.address = address
    center.address_detail = request.POST.get("address_detail", "").strip()
    center.phone = request.POST.get("phone", "").strip()
    center.description = request.POST.get("description", "").strip()
    center.operating_hours = request.POST.get("operating_hours", "").strip()
    center.pricing = request.POST.get("pricing", "").strip()
    center.amenities = request.POST.get("amenities", "").strip()

    court_count_raw = request.POST.get("court_count", "").strip()
    if court_count_raw:
        try:
            center.court_count = max(0, int(court_count_raw))
        except ValueError:
            messages.error(request, "코트 수는 숫자여야 합니다.")
            return None

    for coord_field in ("latitude", "longitude"):
        raw = request.POST.get(coord_field, "").strip()
        if raw:
            try:
                setattr(center, coord_field, float(raw))
            except ValueError:
                messages.error(request, "좌표는 숫자여야 합니다.")
                return None

    if request.FILES.get("cover_image"):
        center.cover_image = request.FILES["cover_image"]
    if request.FILES.get("profile_image"):
        center.profile_image = request.FILES["profile_image"]

    center.save()
    return center
