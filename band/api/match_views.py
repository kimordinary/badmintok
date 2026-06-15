from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction

from band.models import BandMember, BandSchedule, BandScheduleApplication
from band.match_models import MatchSession, SessionParticipant, Court
from band.matchmaking.scoring import level_to_score
from band.api.match_serializers import serialize_session


def _is_operator(user, band) -> bool:
    return BandMember.objects.filter(
        band=band, user=user, status="active",
        role__in=["owner", "admin"]).exists()


def _profile_level_gender(user):
    profile = getattr(user, "profile", None)
    level = getattr(profile, "badminton_level", "") if profile else ""
    gender = getattr(profile, "gender", "unknown") if profile else "unknown"
    return level_to_score(level), gender


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request, schedule_id):
    schedule = get_object_or_404(BandSchedule, id=schedule_id)
    if not _is_operator(request.user, schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if hasattr(schedule, "match_session"):
        return Response({"detail": "이미 대진 세션이 있습니다.", "id": schedule.match_session.id},
                        status=status.HTTP_409_CONFLICT)

    court_count = int(request.data.get("court_count", 4))
    mode = request.data.get("discipline_mode", MatchSession.DisciplineMode.ALL)
    preset = request.data.get("preset", MatchSession.Preset.BALANCED)

    with transaction.atomic():
        session = MatchSession.objects.create(
            schedule=schedule, court_count=court_count,
            discipline_mode=mode, preset=preset, created_by=request.user)
        for i in range(1, court_count + 1):
            Court.objects.create(session=session, index=i)
        apps = BandScheduleApplication.objects.filter(
            schedule=schedule, status="approved").select_related("user")
        for app in apps:
            score, gender = _profile_level_gender(app.user)
            SessionParticipant.objects.create(
                session=session, user=app.user, base_level=score, gender=gender,
                attendance=SessionParticipant.Attendance.NOT_PRESENT)

    return Response(serialize_session(session), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_state(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    return Response(serialize_session(session))
