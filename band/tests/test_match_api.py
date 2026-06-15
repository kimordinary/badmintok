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


class TogglesTest(MatchApiSetup):
    def _session(self):
        return self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2}, format="json").json()

    def test_set_mode(self):
        sid = self._session()["id"]
        resp = self.client.post(f"/api/bands/match/{sid}/mode/",
                                {"discipline_mode": "mixed_only"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["discipline_mode"], "mixed_only")

    def test_set_preset(self):
        sid = self._session()["id"]
        resp = self.client.post(f"/api/bands/match/{sid}/preset/",
                                {"preset": "competitive"}, format="json")
        self.assertEqual(resp.json()["preset"], "competitive")

    def test_toggle_attendance_back_and_forth(self):
        u = self._approved_applicant("m1@x.com", "a", "male")
        sid = self._session()["id"]
        pid = next(p["id"] for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]
                   if p["user_id"] == u.id)
        r1 = self.client.post(f"/api/bands/match/{sid}/participants/{pid}/attendance/",
                              {"attendance": "present"}, format="json")
        self.assertEqual(r1.json()["attendance"], "present")
        r2 = self.client.post(f"/api/bands/match/{sid}/participants/{pid}/attendance/",
                              {"attendance": "left"}, format="json")
        self.assertEqual(r2.json()["attendance"], "left")


class FlowTest(MatchApiSetup):
    def _present_session(self, specs):
        # specs: [(email, level, gender), ...] 모두 present 로 시작
        for email, level, gender in specs:
            self._approved_applicant(email, level, gender)
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 1, "discipline_mode": "all"}, format="json").json()["id"]
        for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
        return sid

    def test_fill_empty_court_creates_match(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()["match"])
        # 상태 조회 시 코트1에 진행 경기
        state = self.client.get(f"/api/bands/match/{sid}/").json()
        self.assertIsNotNone(state["courts"][0]["match"])

    def test_end_increments_counts_and_refills(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male"), ("f@x.com", "b", "male"),
            ("g@x.com", "b", "female"), ("h@x.com", "b", "female")])
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/end/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        # 끝난 4명은 카운트 1, 새 경기 생성됨
        state = self.client.get(f"/api/bands/match/{sid}/").json()
        played = [p for p in state["participants"] if p["total_games"] == 1]
        self.assertEqual(len(played), 4)
        self.assertIsNotNone(state["courts"][0]["match"])

    def test_mixed_only_impossible_returns_needs_choice(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male")])
        self.client.post(f"/api/bands/match/{sid}/mode/",
                         {"discipline_mode": "mixed_only"}, format="json")
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["needs_choice"])
        self.assertIn("mens", resp.json()["options"])

    def test_fill_with_forced_discipline(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male")])
        self.client.post(f"/api/bands/match/{sid}/mode/",
                         {"discipline_mode": "mixed_only"}, format="json")
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/",
                                {"discipline": "mens"}, format="json")
        self.assertIsNotNone(resp.json()["match"])
        self.assertEqual(resp.json()["match"]["discipline"], "mens")


class EditTest(FlowTest):
    def test_swap_replaces_player_in_match(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male")])
        match = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json").json()["match"]
        in_ids = {p["participant_id"] for p in match["team1"] + match["team2"]}
        state = self.client.get(f"/api/bands/match/{sid}/").json()
        bench = next(p["participant_id"] for p in state["queue"]
                     if p["participant_id"] not in in_ids)
        leaving = next(iter(in_ids))
        resp = self.client.patch(f"/api/bands/match/{sid}/matches/{match['id']}/",
                                 {"swap": [leaving, bench]}, format="json")
        self.assertEqual(resp.status_code, 200)
        new_ids = {p["participant_id"] for p in resp.json()["team1"] + resp.json()["team2"]}
        self.assertIn(bench, new_ids)
        self.assertNotIn(leaving, new_ids)

    def test_end_session(self):
        sid = self._present_session([("a@x.com", "b", "male")])
        resp = self.client.post(f"/api/bands/match/{sid}/end/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ended")
