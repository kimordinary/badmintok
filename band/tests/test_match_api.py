from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from band.models import Band, BandMember, BandSchedule, BandScheduleApplication
from accounts.models import UserProfile
from notifications.models import Notification

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


class ParticipantApiTest(FlowTest):
    def _present_session_users(self, specs):
        users = {email: self._approved_applicant(email, level, gender)
                 for email, level, gender in specs}
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 1, "discipline_mode": "all"}, format="json").json()["id"]
        for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
        return sid, users

    def test_my_status_shows_queue_position_and_games(self):
        sid, users = self._present_session_users([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        self.client.force_authenticate(users["a@x.com"])
        resp = self.client.get(f"/api/bands/match/{sid}/me/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["attendance"], "present")
        self.assertEqual(body["games"]["total"], 0)
        self.assertIsNotNone(body["participant_id"])
        self.assertIsNotNone(body["queue_position"])
        self.assertTrue(body["up_next"])  # 4명뿐이라 모두 다음 경기 후보

    def test_my_status_shows_current_match_when_playing(self):
        sid, users = self._present_session_users([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.client.force_authenticate(users["a@x.com"])
        body = self.client.get(f"/api/bands/match/{sid}/me/").json()
        self.assertTrue(body["playing"])
        self.assertIsNotNone(body["current_match"])
        self.assertEqual(body["current_match"]["court_index"], 1)
        self.assertIn(body["current_match"]["my_team"], (1, 2))

    def test_my_checkin_in_and_out(self):
        sid, users = self._present_session_users([("a@x.com", "b", "male")])
        self.client.force_authenticate(users["a@x.com"])
        out = self.client.post(f"/api/bands/match/{sid}/me/checkin/",
                               {"action": "out"}, format="json")
        self.assertEqual(out.status_code, 200)
        self.assertEqual(out.json()["attendance"], "left")
        back = self.client.post(f"/api/bands/match/{sid}/me/checkin/",
                                {"action": "in"}, format="json")
        self.assertEqual(back.json()["attendance"], "present")

    def test_non_participant_checkin_forbidden(self):
        sid, _ = self._present_session_users([("a@x.com", "b", "male")])
        stranger = User.objects.create_user(email="z@z.com", password="x", activity_name="Z")
        self.client.force_authenticate(stranger)
        resp = self.client.post(f"/api/bands/match/{sid}/me/checkin/",
                                {"action": "in"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_my_status_by_schedule_before_session(self):
        u = self._approved_applicant("a@x.com", "b", "male")
        self.client.force_authenticate(u)
        body = self.client.get(
            f"/api/bands/match/schedules/{self.schedule.id}/me/").json()
        self.assertIsNone(body["session_id"])
        self.assertTrue(body["approved"])

    def test_my_status_by_schedule_after_session(self):
        sid, users = self._present_session_users([("a@x.com", "b", "male")])
        self.client.force_authenticate(users["a@x.com"])
        body = self.client.get(
            f"/api/bands/match/schedules/{self.schedule.id}/me/").json()
        self.assertEqual(body["session_id"], sid)
        self.assertEqual(body["attendance"], "present")
        self.assertTrue(body["approved"])

    def test_checkin_blocked_after_session_ended(self):
        sid, users = self._present_session_users([("a@x.com", "b", "male")])
        self.client.post(f"/api/bands/match/{sid}/end/", {}, format="json")
        self.client.force_authenticate(users["a@x.com"])
        resp = self.client.post(f"/api/bands/match/{sid}/me/checkin/",
                                {"action": "in"}, format="json")
        self.assertEqual(resp.status_code, 409)


class PartnerApiTest(FlowTest):
    def _present_session_users(self, specs):
        users = {email: self._approved_applicant(email, level, gender)
                 for email, level, gender in specs}
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2, "discipline_mode": "all"}, format="json").json()["id"]
        parts = {}
        for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
            parts[p["user_id"]] = p["id"]
        return sid, users, parts

    def test_request_then_host_approves_creates_pair(self):
        sid, users, parts = self._present_session_users([
            ("a@x.com", "b", "female"), ("b@x.com", "b", "female")])
        a, b = users["a@x.com"], users["b@x.com"]
        # 참가자 a가 b에게 신청
        self.client.force_authenticate(a)
        r = self.client.post(f"/api/bands/match/{sid}/partner-requests/create/",
                             {"to_participant_id": parts[b.id], "strict": True}, format="json")
        self.assertEqual(r.status_code, 201)
        req_id = r.json()["id"]
        # 모임장이 대기 신청 확인
        self.client.force_authenticate(self.owner)
        lst = self.client.get(f"/api/bands/match/{sid}/partner-requests/").json()
        self.assertEqual(len(lst["requests"]), 1)
        # 승인 → 쌍 생성
        ap = self.client.post(
            f"/api/bands/match/{sid}/partner-requests/{req_id}/approve/", {}, format="json")
        self.assertEqual(ap.status_code, 201)
        self.assertTrue(ap.json()["strict"])
        state = self.client.get(f"/api/bands/match/{sid}/").json()
        self.assertEqual(len(state["pairs"]), 1)
        self.assertEqual(len(state["partner_requests"]), 0)

    def test_non_participant_cannot_request(self):
        sid, users, parts = self._present_session_users([("a@x.com", "b", "male")])
        stranger = User.objects.create_user(email="z@z.com", password="x", activity_name="Z")
        self.client.force_authenticate(stranger)
        r = self.client.post(f"/api/bands/match/{sid}/partner-requests/create/",
                             {"to_participant_id": parts[users["a@x.com"].id]}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_self_request_rejected(self):
        sid, users, parts = self._present_session_users([("a@x.com", "b", "male")])
        self.client.force_authenticate(users["a@x.com"])
        r = self.client.post(f"/api/bands/match/{sid}/partner-requests/create/",
                             {"to_participant_id": parts[users["a@x.com"].id]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_host_direct_create_and_delete_pair(self):
        sid, users, parts = self._present_session_users([
            ("a@x.com", "b", "female"), ("b@x.com", "b", "female")])
        r = self.client.post(f"/api/bands/match/{sid}/pairs/",
                             {"p1_id": parts[users["a@x.com"].id],
                              "p2_id": parts[users["b@x.com"].id]}, format="json")
        self.assertEqual(r.status_code, 201)
        pair_id = r.json()["id"]
        d = self.client.delete(f"/api/bands/match/{sid}/pairs/{pair_id}/")
        self.assertEqual(d.status_code, 204)
        self.assertEqual(len(self.client.get(f"/api/bands/match/{sid}/").json()["pairs"]), 0)

    def test_approve_conflicts_when_already_paired(self):
        sid, users, parts = self._present_session_users([
            ("a@x.com", "b", "female"), ("b@x.com", "b", "female"),
            ("c@x.com", "b", "female")])
        a, b, c = users["a@x.com"], users["b@x.com"], users["c@x.com"]
        # a-b 쌍 직접 생성
        self.client.post(f"/api/bands/match/{sid}/pairs/",
                         {"p1_id": parts[a.id], "p2_id": parts[b.id]}, format="json")
        # a가 c에게 신청 → 승인 시 a가 이미 쌍이라 409
        self.client.force_authenticate(a)
        req_id = self.client.post(f"/api/bands/match/{sid}/partner-requests/create/",
                                  {"to_participant_id": parts[c.id]}, format="json").json()["id"]
        self.client.force_authenticate(self.owner)
        ap = self.client.post(
            f"/api/bands/match/{sid}/partner-requests/{req_id}/approve/", {}, format="json")
        self.assertEqual(ap.status_code, 409)

    def test_paired_players_share_team_in_real_match(self):
        sid, users, parts = self._present_session_users([
            ("a@x.com", "b", "female"), ("b@x.com", "b", "female"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male"), ("f@x.com", "b", "male"),
            ("g@x.com", "b", "male"), ("h@x.com", "b", "male")])
        a, b = users["a@x.com"], users["b@x.com"]
        self.client.post(f"/api/bands/match/{sid}/pairs/",
                         {"p1_id": parts[a.id], "p2_id": parts[b.id], "strict": True},
                         format="json")
        match = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {},
                                 format="json").json()["match"]
        self.assertEqual(match["discipline"], "womens")
        t1 = {p["participant_id"] for p in match["team1"]}
        t2 = {p["participant_id"] for p in match["team2"]}
        pa, pb = parts[a.id], parts[b.id]
        self.assertTrue((pa in t1 and pb in t1) or (pa in t2 and pb in t2))


class CoachApiTest(FlowTest):
    def _present(self, specs):
        users = {email: self._approved_applicant(email, level, gender)
                 for email, level, gender in specs}
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 1, "discipline_mode": "all"}, format="json").json()["id"]
        parts = {}
        for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
            parts[p["user_id"]] = p["id"]
        return sid, users, parts

    def test_set_coach_shows_in_state_with_coverage(self):
        sid, users, parts = self._present([
            ("ace@x.com", "master", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male")])
        coach_pid = parts[users["ace@x.com"].id]
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/coach/",
                                {"participant_id": coach_pid}, format="json")
        self.assertEqual(resp.status_code, 200)
        court = resp.json()["courts"][0]
        self.assertEqual(court["coach"]["participant_id"], coach_pid)
        self.assertEqual(court["coach"]["coverage"]["met"], 0)
        self.assertEqual(court["coach"]["coverage"]["total"], 3)  # 코치 제외 3명

    def test_coach_court_fill_includes_coach_and_unmet(self):
        sid, users, parts = self._present([
            ("ace@x.com", "master", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male")])
        coach_pid = parts[users["ace@x.com"].id]
        self.client.post(f"/api/bands/match/{sid}/courts/1/coach/",
                         {"participant_id": coach_pid}, format="json")
        match = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {},
                                 format="json").json()["match"]
        ids = {p["participant_id"] for p in match["team1"] + match["team2"]}
        self.assertIn(coach_pid, ids)  # 코치는 항상 자기 코트에

    def test_coverage_increases_after_coach_game(self):
        sid, users, parts = self._present([
            ("ace@x.com", "master", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male"),
            ("e@x.com", "b", "male"), ("f@x.com", "b", "male"),
            ("g@x.com", "b", "male")])
        coach_pid = parts[users["ace@x.com"].id]
        self.client.post(f"/api/bands/match/{sid}/courts/1/coach/",
                         {"participant_id": coach_pid}, format="json")
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.client.post(f"/api/bands/match/{sid}/courts/1/end/", {}, format="json")
        court = self.client.get(f"/api/bands/match/{sid}/").json()["courts"][0]
        # 1게임 종료 후 자동 리필로 코치가 나머지 3명과도 경기 중 → 6명 전원 만남
        self.assertEqual(court["coach"]["coverage"]["met"], 6)
        self.assertEqual(court["coach"]["coverage"]["total"], 6)

    def test_coach_excluded_from_normal_queue(self):
        sid, users, parts = self._present([
            ("ace@x.com", "master", "male"), ("b@x.com", "b", "male")])
        coach_pid = parts[users["ace@x.com"].id]
        self.client.post(f"/api/bands/match/{sid}/courts/1/coach/",
                         {"participant_id": coach_pid}, format="json")
        queue = self.client.get(f"/api/bands/match/{sid}/").json()["queue"]
        self.assertNotIn(coach_pid, [q["participant_id"] for q in queue])

    def test_clear_coach(self):
        sid, users, parts = self._present([("ace@x.com", "master", "male")])
        coach_pid = parts[users["ace@x.com"].id]
        self.client.post(f"/api/bands/match/{sid}/courts/1/coach/",
                         {"participant_id": coach_pid}, format="json")
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/coach/", {}, format="json")
        self.assertIsNone(resp.json()["courts"][0]["coach"])


class MatchNotificationTest(FlowTest):
    def _present(self, specs, court_count=1):
        users = {email: self._approved_applicant(email, level, gender)
                 for email, level, gender in specs}
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": court_count, "discipline_mode": "all"}, format="json").json()["id"]
        parts = {}
        for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
            parts[p["user_id"]] = p["id"]
        return sid, users, parts

    def test_fill_court_notifies_the_four_players(self):
        sid, users, parts = self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        Notification.objects.all().delete()
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.assertEqual(
            Notification.objects.filter(type=Notification.Type.MATCH_NEXT_GAME).count(), 4)

    def test_coach_excluded_from_next_game_push(self):
        sid, users, parts = self._present([
            ("ace@x.com", "master", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male")])
        self.client.post(f"/api/bands/match/{sid}/courts/1/coach/",
                         {"participant_id": parts[users["ace@x.com"].id]}, format="json")
        Notification.objects.all().delete()
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        notifs = Notification.objects.filter(type=Notification.Type.MATCH_NEXT_GAME)
        self.assertEqual(notifs.count(), 3)  # 코치 제외 3명
        self.assertNotIn(users["ace@x.com"].id, notifs.values_list("user_id", flat=True))

    def test_partner_request_notifies_recipient(self):
        sid, users, parts = self._present([
            ("a@x.com", "b", "female"), ("b@x.com", "b", "female")])
        a, b = users["a@x.com"], users["b@x.com"]
        Notification.objects.all().delete()
        self.client.force_authenticate(a)
        self.client.post(f"/api/bands/match/{sid}/partner-requests/create/",
                         {"to_participant_id": parts[b.id]}, format="json")
        notif = Notification.objects.filter(type=Notification.Type.PARTNER_REQUEST)
        self.assertEqual(notif.count(), 1)
        self.assertEqual(notif.first().user_id, b.id)  # 받는 사람 b에게

    def test_partner_approved_notifies_both(self):
        sid, users, parts = self._present([
            ("a@x.com", "b", "female"), ("b@x.com", "b", "female")])
        a, b = users["a@x.com"], users["b@x.com"]
        self.client.force_authenticate(a)
        req_id = self.client.post(f"/api/bands/match/{sid}/partner-requests/create/",
                                  {"to_participant_id": parts[b.id]}, format="json").json()["id"]
        Notification.objects.all().delete()
        self.client.force_authenticate(self.owner)
        self.client.post(
            f"/api/bands/match/{sid}/partner-requests/{req_id}/approve/", {}, format="json")
        notifs = Notification.objects.filter(type=Notification.Type.PARTNER_APPROVED)
        self.assertEqual(set(notifs.values_list("user_id", flat=True)), {a.id, b.id})


class RobustnessTest(FlowTest):
    def test_swap_wrong_length_returns_400(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male")])
        match = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json").json()["match"]
        resp = self.client.patch(
            f"/api/bands/match/{sid}/matches/{match['id']}/",
            {"swap": [1]}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_ended_session_blocks_end_court(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.client.post(f"/api/bands/match/{sid}/end/", {}, format="json")
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/end/", {}, format="json")
        self.assertEqual(resp.status_code, 409)

    def test_ended_session_blocks_fill_court(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        self.client.post(f"/api/bands/match/{sid}/end/", {}, format="json")
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.assertEqual(resp.status_code, 409)
