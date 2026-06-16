from django.test import TestCase
from django.contrib.auth import get_user_model
from band.models import Band, BandSchedule, MatchSession, SessionParticipant
from django.utils import timezone

User = get_user_model()


class MatchModelsTest(TestCase):
    def test_create_session_and_participant(self):
        u = User.objects.create_user(email="a@a.com", password="x", activity_name="A")
        band = Band.objects.create(name="b", created_by=u)
        sch = BandSchedule.objects.create(
            band=band, title="t", start_datetime=timezone.now(), created_by=u)
        session = MatchSession.objects.create(schedule=sch, court_count=4, created_by=u)
        sp = SessionParticipant.objects.create(
            session=session, user=u, base_level=4, gender="male")
        self.assertEqual(session.participants.count(), 1)
        self.assertEqual(sp.attendance, "not_present")
