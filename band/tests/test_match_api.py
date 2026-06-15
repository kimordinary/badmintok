from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from band.models import Band, BandMember, BandSchedule, BandScheduleApplication
from accounts.models import UserProfile

User = get_user_model()


class MatchApiSetup(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="o@o.com", password="x", activity_name="Owner")
        UserProfile.objects.update_or_create(
            user=self.owner, defaults={"badminton_level": "b", "gender": "male"})
        self.band = Band.objects.create(name="b", created_by=self.owner)
        BandMember.objects.create(band=self.band, user=self.owner, role="owner", status="active")
        self.schedule = BandSchedule.objects.create(
            band=self.band, title="t", start_datetime=timezone.now(), created_by=self.owner)
        self.client.force_authenticate(self.owner)

    def _approved_applicant(self, email, level, gender):
        u = User.objects.create_user(email=email, password="x", activity_name=email[:3])
        UserProfile.objects.update_or_create(
            user=u, defaults={"badminton_level": level, "gender": gender})
        BandScheduleApplication.objects.create(
            schedule=self.schedule, user=u, status="approved")
        return u


class StartSessionTest(MatchApiSetup):
    def test_start_creates_session_with_present_participants_snapshot(self):
        self._approved_applicant("m1@x.com", "a", "male")
        self._approved_applicant("f1@x.com", "c", "female")
        resp = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2, "discipline_mode": "all", "preset": "balanced"},
            format="json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(len(data["participants"]), 2)
        # 급수 a=5 점수로 스냅샷
        levels = sorted(p["base_level"] for p in data["participants"])
        self.assertEqual(levels, [3, 5])  # c=3, a=5

    def test_non_operator_forbidden(self):
        stranger = User.objects.create_user(email="s@s.com", password="x", activity_name="S")
        self.client.force_authenticate(stranger)
        resp = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2}, format="json")
        self.assertEqual(resp.status_code, 403)


class StateTest(MatchApiSetup):
    def test_get_state_returns_courts_and_queue(self):
        self._approved_applicant("m1@x.com", "a", "male")
        start = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2}, format="json").json()
        sid = start["id"]
        resp = self.client.get(f"/api/bands/match/{sid}/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["courts"]), 2)
        self.assertIn("queue", body)
