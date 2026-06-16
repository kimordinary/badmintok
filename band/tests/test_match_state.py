from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from band.models import Band, BandSchedule, MatchSession, SessionParticipant
from band.match_state import build_pool, build_pairstats

User = get_user_model()


class MatchStateTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(email="a@a.com", password="x", activity_name="A")
        band = Band.objects.create(name="b", created_by=self.u)
        sch = BandSchedule.objects.create(
            band=band, title="t", start_datetime=timezone.now(), created_by=self.u)
        self.session = MatchSession.objects.create(schedule=sch, court_count=2, created_by=self.u)

    def test_build_pool_only_present(self):
        SessionParticipant.objects.create(
            session=self.session, user=self.u, base_level=4, gender="male",
            attendance="present")
        u2 = User.objects.create_user(email="b@b.com", password="x", activity_name="B")
        SessionParticipant.objects.create(
            session=self.session, user=u2, base_level=3, gender="female",
            attendance="not_present")
        pool = build_pool(self.session)
        self.assertEqual([p.gender for p in pool], ["male"])  # present 만

    def test_pool_excludes_players_currently_on_court(self):
        # on_court_participant_ids 로 제외
        sp = SessionParticipant.objects.create(
            session=self.session, user=self.u, base_level=4, gender="male",
            attendance="present")
        pool = build_pool(self.session, on_court_participant_ids={sp.id})
        self.assertEqual(pool, [])
