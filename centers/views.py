from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import is_site_admin
from band.api.views import REGION_GROUPS
from centers.models import Center, CenterBookmark

REGION_CHOICES = Center.Region.choices


def _build_region_options():
    """band의 지역 그룹 매핑을 그대로 사용해 옵션 리스트 생성."""
    options = [{"value": "all", "label": "전체"}]
    options += [
        {"value": v, "label": l}
        for v, l in REGION_CHOICES if v != "all"
    ]
    return options


def _user_can_manage(user, center):
    if not user.is_authenticated:
        return False
    if is_site_admin(user):
        return True
    return center.created_by_id == user.id


def center_list(request):
    """센터 목록 페이지."""
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

    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(
            CenterBookmark.objects.filter(
                user=request.user,
                center__in=[c.pk for c in page_obj]
            ).values_list("center_id", flat=True)
        )

    centers_with_meta = [
        {
            "obj": c,
            "can_manage": _user_can_manage(request.user, c),
            "is_bookmarked": c.id in bookmarked_ids,
        }
        for c in page_obj
    ]

    return render(request, "center/list.html", {
        "page_obj": page_obj,
        "centers_with_meta": centers_with_meta,
        "search": search,
        "current_region": region or "all",
        "region_options": _build_region_options(),
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

    center.save()
    return center
