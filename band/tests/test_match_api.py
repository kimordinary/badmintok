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
            user=u, defaults={"badminton_level": level, "gender": gender, "name": email[:3]})
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

    def test_site_admin_can_operate_without_membership(self):
        # 밴드 멤버가 아니어도 사이트 관리자(슈퍼유저)는 대진 시작·운영 가능 (조회 can_manage와 일치)
        admin = User.objects.create_user(email="adm@x.com", password="x", activity_name="Adm")
        admin.is_superuser = True
        admin.is_staff = True
        admin.save()
        self._approved_applicant("m1@x.com", "a", "male")
        self.client.force_authenticate(admin)
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 1, "discipline_mode": "all"}, format="json")
        self.assertEqual(sid.status_code, 201)
        # 시작뿐 아니라 다른 운영 액션(세션 종료)도 통과해야 함
        end = self.client.post(f"/api/bands/match/{sid.json()['id']}/end/", {}, format="json")
        self.assertEqual(end.status_code, 200)


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
        # 내 카드 표시용 — 이름·성별·급수
        self.assertEqual(body["name"], users["a@x.com"].activity_name)
        self.assertEqual(body["gender"], "male")
        self.assertEqual(body["base_level"], 4)  # b=4

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

    def test_present_member_excluded_from_pool_when_profile_incomplete(self):
        # present로 체크인한 뒤 급수를 비우면: present는 유지되나 매칭 후보에선 제외
        sid, users = self._present_session_users([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        u = users["a@x.com"]
        u.profile.badminton_level = ""
        u.profile.save()
        self.client.force_authenticate(u)
        body = self.client.get(f"/api/bands/match/{sid}/me/").json()
        self.assertEqual(body["attendance"], "present")        # 출석 상태는 유지
        self.assertTrue(body["excluded_from_pool"])            # 매칭 후보에서 제외
        self.assertFalse(body["profile"]["complete"])
        self.assertIn("level", body["profile"]["missing"])
        # 실제 pool에서도 빠져 queue에 안 잡힘
        self.assertIsNone(body["queue_position"])

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


class ReservationApiTest(FlowTest):
    def _present(self, specs, court_count=2):
        users = {email: self._approved_applicant(email, level, gender)
                 for email, level, gender in specs}
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": court_count, "discipline_mode": "all"}, format="json").json()["id"]
        raw = {}
        for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
            raw[p["user_id"]] = p["id"]
        pid = {email.split("@")[0]: raw[u.id] for email, u in users.items()}
        return sid, pid

    def _six(self):
        return self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male"),
            ("e@x.com", "b", "female"), ("f@x.com", "b", "female")])

    def test_reserve_excludes_players_from_queue(self):
        sid, pid = self._six()
        ids = [pid["a"], pid["b"], pid["e"], pid["f"]]
        r = self.client.post(f"/api/bands/match/{sid}/reservations/",
                             {"participant_ids": ids}, format="json")
        self.assertEqual(r.status_code, 201)
        state = self.client.get(f"/api/bands/match/{sid}/").json()
        self.assertEqual(len(state["reservations"]), 1)
        qids = [q["participant_id"] for q in state["queue"]]
        for i in ids:
            self.assertNotIn(i, qids)        # 예약된 4명은 큐에서 빠짐(확보)
        self.assertIn(pid["c"], qids)        # 예약 안 된 사람은 큐에 남음

    def test_reserved_players_excluded_from_auto_fill(self):
        # court_count=2: 한 코트를 자동으로 채워도 예약된 4명은 안 뽑힘
        sid, pid = self._six()
        ids = [pid["a"], pid["b"], pid["e"], pid["f"]]
        self.client.post(f"/api/bands/match/{sid}/reservations/",
                         {"participant_ids": ids}, format="json")
        # 큐에 남은 건 c,d 둘뿐 → 자동으로 4명 못 채움
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        # 예약 4명은 준비됐으니 예약이 우선 투입됨
        on = {p["participant_id"] for p in resp.json()["match"]["team1"] + resp.json()["match"]["team2"]}
        self.assertEqual(on, set(ids))

    def test_reserved_game_priority_then_consumed(self):
        sid, pid = self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male"),
            ("e@x.com", "b", "female"), ("f@x.com", "b", "female")], court_count=1)
        ids = [pid["c"], pid["d"], pid["e"], pid["f"]]
        self.client.post(f"/api/bands/match/{sid}/reservations/",
                         {"participant_ids": ids}, format="json")
        match = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json").json()["match"]
        on = {p["participant_id"] for p in match["team1"] + match["team2"]}
        self.assertEqual(on, set(ids))       # 자동보다 예약 우선
        self.assertEqual(len(self.client.get(f"/api/bands/match/{sid}/").json()["reservations"]), 0)

    def test_counts_increment_after_reserved_game_ends(self):
        sid, pid = self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")], court_count=1)
        ids = [pid["a"], pid["b"], pid["c"], pid["d"]]
        self.client.post(f"/api/bands/match/{sid}/reservations/",
                         {"participant_ids": ids}, format="json")
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        self.client.post(f"/api/bands/match/{sid}/courts/1/end/", {}, format="json")
        state = self.client.get(f"/api/bands/match/{sid}/").json()
        played = [p for p in state["participants"] if p["total_games"] == 1]
        self.assertEqual(len(played), 4)     # 예약 경기도 카운트 자동 반영

    def test_reserve_requires_exactly_four(self):
        sid, pid = self._six()
        r = self.client.post(f"/api/bands/match/{sid}/reservations/",
                             {"participant_ids": [pid["a"], pid["b"], pid["c"]]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reserve_conflict_when_already_reserved(self):
        sid, pid = self._six()
        self.client.post(f"/api/bands/match/{sid}/reservations/",
                         {"participant_ids": [pid["a"], pid["b"], pid["e"], pid["f"]]}, format="json")
        r = self.client.post(f"/api/bands/match/{sid}/reservations/",
                             {"participant_ids": [pid["a"], pid["c"], pid["d"], pid["e"]]}, format="json")
        self.assertEqual(r.status_code, 409)

    def test_reserve_rejects_player_on_court(self):
        sid, pid = self._six()
        match = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json").json()["match"]
        on_id = match["team1"][0]["participant_id"]
        # 경기 중인 사람 포함 예약 → 400
        rest = [v for v in pid.values() if v != on_id][:3]
        r = self.client.post(f"/api/bands/match/{sid}/reservations/",
                             {"participant_ids": [on_id] + rest}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_delete_reservation_returns_players_to_queue(self):
        sid, pid = self._six()
        ids = [pid["a"], pid["b"], pid["e"], pid["f"]]
        rid = self.client.post(f"/api/bands/match/{sid}/reservations/",
                               {"participant_ids": ids}, format="json").json()["id"]
        d = self.client.delete(f"/api/bands/match/{sid}/reservations/{rid}/")
        self.assertEqual(d.status_code, 204)
        state = self.client.get(f"/api/bands/match/{sid}/").json()
        self.assertEqual(len(state["reservations"]), 0)
        qids = [q["participant_id"] for q in state["queue"]]
        for i in ids:
            self.assertIn(i, qids)           # 해제하면 큐로 복귀


class OperatorExtrasTest(FlowTest):
    def _present(self, specs, court_count=2):
        users = {email: self._approved_applicant(email, level, gender)
                 for email, level, gender in specs}
        sid = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": court_count, "discipline_mode": "all"}, format="json").json()["id"]
        for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
        byuser = {p["user_id"]: p["id"]
                  for p in self.client.get(f"/api/bands/match/{sid}/").json()["participants"]}
        pid = {e.split("@")[0]: byuser[u.id] for e, u in users.items()}
        return sid, pid

    # --- ① 직접 채우기 ---
    def test_manual_fill_places_exactly_those_four(self):
        sid, pid = self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male"), ("f@x.com", "b", "female")], court_count=1)
        ids = [pid["a"], pid["b"], pid["c"], pid["d"]]
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/",
                                {"participant_ids": ids}, format="json")
        self.assertEqual(resp.status_code, 200)
        on = {p["participant_id"] for p in resp.json()["match"]["team1"] + resp.json()["match"]["team2"]}
        self.assertEqual(on, set(ids))

    def test_manual_fill_requires_four(self):
        sid, pid = self._present([("a@x.com", "b", "male")], court_count=1)
        resp = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/",
                                {"participant_ids": [pid["a"]]}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_manual_fill_rejects_player_on_court(self):
        sid, pid = self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male"), ("f@x.com", "b", "female"),
            ("g@x.com", "b", "male"), ("h@x.com", "b", "female")], court_count=2)
        m = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json").json()["match"]
        busy = m["team1"][0]["participant_id"]
        free = [v for v in pid.values() if v != busy
                and v not in {x["participant_id"] for x in m["team1"] + m["team2"]}][:3]
        resp = self.client.post(f"/api/bands/match/{sid}/courts/2/fill/",
                                {"participant_ids": [busy] + free}, format="json")
        self.assertEqual(resp.status_code, 400)

    # --- ② 코트 설정 ---
    def test_add_court(self):
        sid, _ = self._present([("a@x.com", "b", "male")], court_count=2)
        resp = self.client.post(f"/api/bands/match/{sid}/courts/", {"name": "중앙"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["court_count"], 3)
        self.assertEqual(resp.json()["courts"][-1]["name"], "중앙")

    def test_rename_court(self):
        sid, _ = self._present([("a@x.com", "b", "male")], court_count=2)
        resp = self.client.patch(f"/api/bands/match/{sid}/courts/1/", {"name": "A코트"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["courts"][0]["name"], "A코트")

    def test_delete_court(self):
        sid, _ = self._present([("a@x.com", "b", "male")], court_count=2)
        resp = self.client.delete(f"/api/bands/match/{sid}/courts/2/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["court_count"], 1)

    def test_delete_court_with_playing_match_blocked(self):
        sid, _ = self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")], court_count=1)
        self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json")
        resp = self.client.delete(f"/api/bands/match/{sid}/courts/1/")
        self.assertEqual(resp.status_code, 409)

    # --- ③ 임시 인원 ---
    def test_add_guest_participant(self):
        sid, _ = self._present([("a@x.com", "b", "male")], court_count=1)
        resp = self.client.post(f"/api/bands/match/{sid}/participants/",
                                {"name": "홍길동", "gender": "male", "level": "c"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["name"], "홍길동")
        self.assertIsNone(resp.json()["user_id"])
        self.assertEqual(resp.json()["attendance"], "present")

    def test_guest_can_be_matched(self):
        sid, _ = self._present([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female")], court_count=1)
        gid = self.client.post(f"/api/bands/match/{sid}/participants/",
                               {"name": "게스트", "gender": "female", "level": "b"},
                               format="json").json()["id"]
        match = self.client.post(f"/api/bands/match/{sid}/courts/1/fill/", {}, format="json").json()["match"]
        on = {p["participant_id"] for p in match["team1"] + match["team2"]}
        self.assertIn(gid, on)

    # --- 승인자 재동기화 ---
    def test_sync_adds_late_approved_applicant(self):
        sid, _ = self._present([("a@x.com", "b", "male")], court_count=1)
        self._approved_applicant("late@x.com", "c", "female")  # 세션 시작 후 승인
        resp = self.client.post(f"/api/bands/match/{sid}/participants/sync/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["added"], 1)
        names = {p["name"] for p in resp.json()["participants"]}
        self.assertIn("lat", names)  # activity_name = email[:3]

    def test_sync_no_duplicate(self):
        sid, _ = self._present([("a@x.com", "b", "male")], court_count=1)
        resp = self.client.post(f"/api/bands/match/{sid}/participants/sync/", {}, format="json")
        self.assertEqual(resp.json()["added"], 0)

    def test_add_participant_validation(self):
        sid, _ = self._present([("a@x.com", "b", "male")], court_count=1)
        self.assertEqual(self.client.post(
            f"/api/bands/match/{sid}/participants/",
            {"name": "", "gender": "male"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(
            f"/api/bands/match/{sid}/participants/",
            {"name": "x", "gender": "unknown"}, format="json").status_code, 400)


class SessionBridgeTest(MatchApiSetup):
    def test_ensure_session_creates_and_is_idempotent(self):
        from band.match_service import ensure_session
        from band.match_models import MatchSession
        u = self._approved_applicant("a@x.com", "b", "male")
        s1 = ensure_session(self.schedule, self.owner)
        self.assertEqual(MatchSession.objects.filter(schedule=self.schedule).count(), 1)
        self.assertEqual(s1.participants.count(), 1)
        s2 = ensure_session(self.schedule, self.owner)  # 이미 있으면 그대로
        self.assertEqual(s1.id, s2.id)
        self.assertEqual(MatchSession.objects.filter(schedule=self.schedule).count(), 1)

    def test_me_returns_session_after_bridge(self):
        from band.match_service import ensure_session
        u = self._approved_applicant("a@x.com", "b", "male")
        ensure_session(self.schedule, self.owner)  # 웹 콘솔 진입 시뮬레이션
        self.client.force_authenticate(u)
        body = self.client.get(
            f"/api/bands/match/schedules/{self.schedule.id}/me/").json()
        self.assertIsNotNone(body["session_id"])
        self.assertIsNotNone(body["participant_id"])  # 승인자가 스냅샷에 연결됨

    def test_ensure_session_never_touches_existing(self):
        """순수 get-or-create: 세션 있으면 재생성·참가자 추가 절대 안 함."""
        from band.match_service import ensure_session
        from band.match_models import MatchSession
        self._approved_applicant("a@x.com", "b", "male")
        s1 = ensure_session(self.schedule, self.owner)
        self.assertEqual(s1.participants.count(), 1)
        # 세션 생성 후 새 승인자가 생겨도 ensure_session은 손대지 않는다(재동기화 아님)
        self._approved_applicant("late@x.com", "c", "female")
        s2 = ensure_session(self.schedule, self.owner)
        self.assertEqual(s1.id, s2.id)
        self.assertEqual(s2.participants.count(), 1)            # 안 늘어남
        self.assertEqual(MatchSession.objects.filter(schedule=self.schedule).count(), 1)


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
