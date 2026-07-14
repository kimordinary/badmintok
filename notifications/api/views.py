from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from notifications.models import Notification, DeviceToken
from .serializers import NotificationSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """알림 목록 API"""
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related("actor", "related_band_post", "related_notice")

    # 읽음 필터
    is_read = request.GET.get("is_read")
    if is_read == "true":
        notifications = notifications.filter(is_read=True)
    elif is_read == "false":
        notifications = notifications.filter(is_read=False)

    # 유형 필터
    noti_type = request.GET.get("type")
    if noti_type:
        notifications = notifications.filter(type=noti_type)

    # 페이지네이션
    page_number = request.GET.get("page", 1)
    page_size = min(int(request.GET.get("page_size", 20)), 100)
    paginator = Paginator(notifications, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = NotificationSerializer(page_obj, many=True)

    return Response({
        "count": paginator.count,
        "page_size": page_size,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
        "previous": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "results": serializer.data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_sent(request):
    """보낸 쪽지(내가 발송한 일정 안내) 목록. 동시 발송분은 하나로 묶어 수신자 표기."""
    from collections import OrderedDict
    sent = Notification.objects.filter(
        actor=request.user, type=Notification.Type.SCHEDULE_NOTICE
    ).select_related(
        "user", "user__profile", "related_band", "related_band_schedule"
    ).order_by("-created_at")

    # (초 단위 시각, 메시지, 일정) 기준 그룹핑
    groups = OrderedDict()
    for n in sent:
        key = (n.created_at.replace(microsecond=0), n.message, n.related_band_schedule_id)
        g = groups.get(key)
        if g is None:
            g = {
                "message": n.message,
                "created_at": n.created_at,
                "band_id": n.related_band_id,
                "band_name": n.related_band.name if n.related_band else None,
                "schedule_id": n.related_band_schedule_id,
                "schedule_title": n.related_band_schedule.title if n.related_band_schedule else None,
                "recipients": [],
            }
            groups[key] = g
        if n.user:
            g["recipients"].append({
                "id": n.user.id,
                "name": getattr(n.user, "activity_name", "") or getattr(n.user, "real_name", ""),
            })

    grouped = list(groups.values())
    for g in grouped:
        g["recipient_count"] = len(g["recipients"])

    page_number = request.GET.get("page", 1)
    page_size = min(int(request.GET.get("page_size", 20)), 100)
    paginator = Paginator(grouped, page_size)
    page_obj = paginator.get_page(page_number)

    return Response({
        "count": paginator.count,
        "page_size": page_size,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
        "previous": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "results": list(page_obj),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_read(request, notification_id):
    """개별 알림 읽음 처리 API"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "알림을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    return Response({"message": "읽음 처리되었습니다."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_read_all(request):
    """모든 알림 읽음 처리 API"""
    count = Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)

    return Response({"message": f"{count}개의 알림이 읽음 처리되었습니다.", "count": count})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    """읽지 않은 알림 개수 API"""
    count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    return Response({"unread_count": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def device_token_register(request):
    """FCM 디바이스 토큰 등록/갱신 API.

    body: { "token": "...", "platform": "android|ios|web" }
    동일 token이 이미 있으면 owner 사용자/플랫폼/활성 상태를 갱신한다.
    """
    token = (request.data.get("token") or "").strip()
    platform = (request.data.get("platform") or "").strip().lower()

    if not token:
        return Response({"error": "token이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
    if platform not in DeviceToken.Platform.values:
        return Response(
            {"error": f"platform은 {list(DeviceToken.Platform.values)} 중 하나여야 합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    obj, created = DeviceToken.objects.update_or_create(
        token=token,
        defaults={
            "user": request.user,
            "platform": platform,
            "is_active": True,
        },
    )
    return Response(
        {"id": obj.id, "platform": obj.platform, "created": created},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def device_token_unregister(request):
    """FCM 디바이스 토큰 삭제 API (로그아웃 시 호출).

    body: { "token": "..." }
    """
    token = (request.data.get("token") or "").strip()
    if not token:
        return Response({"error": "token이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

    deleted, _ = DeviceToken.objects.filter(token=token, user=request.user).delete()
    return Response({"deleted": deleted})
