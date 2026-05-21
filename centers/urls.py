"""센터 URL은 Band 모델로 통합되었음.

기존 /center/* URL은 /band/* (band_type='center') 로 redirect한다.
사용자가 보던 모든 페이지가 그대로 동작하되, 내부 데이터는 Band 모델 사용.
"""
from django.urls import path
from django.shortcuts import redirect

from band.models import Band


app_name = "center"


def list_redirect(request):
    """/center/ -> /band/?type=center"""
    qs = request.GET.urlencode()
    target = "/band/?type=center"
    if qs:
        target = f"{target}&{qs}"
    return redirect(target)


def create_redirect(request):
    """/center/create/ -> /band/create/?type=center"""
    return redirect("/band/create/?type=center")


def _resolve_band_id(center_id):
    """예전 Center.id 로 들어오는 요청을 같은 사람이 만든 Band로 매핑.

    데이터 마이그레이션 후엔 Band.id가 바뀌므로,
    /center/{id}/ 형식의 옛 링크를 redirect할 때만 사용.
    1차로는 Center 모델 lookup으로 매핑한다.
    """
    try:
        from centers.models import Center
        c = Center.objects.filter(id=center_id).first()
        if not c:
            return None
        b = Band.objects.filter(name=c.name, band_type="center", created_by=c.created_by).first()
        return b.id if b else None
    except Exception:
        return None


def detail_redirect(request, center_id):
    """/center/{old_id}/ -> /band/{new_band_id}/"""
    band_id = _resolve_band_id(center_id)
    if band_id is None:
        return redirect("/band/?type=center")
    return redirect(f"/band/{band_id}/")


def update_redirect(request, center_id):
    band_id = _resolve_band_id(center_id)
    if band_id is None:
        return redirect("/band/?type=center")
    return redirect(f"/band/{band_id}/update/")


def delete_redirect(request, center_id):
    band_id = _resolve_band_id(center_id)
    if band_id is None:
        return redirect("/band/?type=center")
    return redirect(f"/band/{band_id}/delete-request/")


def bookmark_redirect(request, center_id):
    band_id = _resolve_band_id(center_id)
    if band_id is None:
        return redirect("/band/?type=center")
    return redirect(f"/band/{band_id}/bookmark/")


urlpatterns = [
    path("", list_redirect, name="list"),
    path("create/", create_redirect, name="create"),
    path("<int:center_id>/", detail_redirect, name="detail"),
    path("<int:center_id>/update/", update_redirect, name="update"),
    path("<int:center_id>/delete/", delete_redirect, name="delete"),
    path("<int:center_id>/bookmark/", bookmark_redirect, name="bookmark_toggle"),
]
