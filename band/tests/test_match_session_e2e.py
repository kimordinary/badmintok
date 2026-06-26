"""실서버(Django API) 풀세션 E2E — 시작→출석→코트채움→종료 반복을 실제 API로 돌려
   카운트 균등·매칭 유효성·무오류를 검증한다(core.jsx가 아닌 진짜 백엔드 경로)."""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from band.models import Band, BandMember, BandSchedule, BandScheduleApplication
from accounts.models import UserProfile

User = get_user_model()
LEVELS = ["s", "a", "a", "b", "b", "c", "c", "d"]  # 순환 배정
GENDERS = ["male", "male", "female"]               # 약 2:1


class MatchSessionE2E(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="o@o.com", password="x", activity_name="Owner")
        UserProfile.objects.update_or_create(user=self.owner, defaults={"badminton_level": "b", "gender": "male"})
        self.band = Band.objects.create(name="b", created_by=self.owner)
        BandMember.objects.create(band=self.band, user=self.owner, role="owner", status="active")
        self.schedule = BandSchedule.objects.create(
            band=self.band, title="t", start_datetime=timezone.now(), created_by=self.owner)
        for i in range(20):
            u = User.objects.create_user(email=f"u{i}@x.com", password="x", activity_name=f"P{i:02d}")
            UserProfile.objects.update_or_create(
                user=u, defaults={"badminton_level": LEVELS[i % len(LEVELS)],
                                  "gender": GENDERS[i % len(GENDERS)], "name": f"P{i:02d}"})
            BandScheduleApplication.objects.create(schedule=self.schedule, user=u, status="approved")
        self.client.force_authenticate(self.owner)

    def _state(self, sid):
        return self.client.get(f"/api/bands/match/{sid}/").json()

    def test_full_session_stays_balanced_and_valid(self):
        # 1) 세션 시작 (20명, 4코트, 모두 모드)
        start = self.client.post(
            f"/api/bands/match/schedules/{self.schedule.id}/start/",
            {"court_count": 4, "discipline_mode": "all", "preset": "balanced"}, format="json")
        self.assertEqual(start.status_code, 201)
        sid = start.json()["id"]

        # 2) 전원 출석 체크
        for p in start.json()["participants"]:
            r = self.client.post(
                f"/api/bands/match/{sid}/participants/{p['id']}/attendance/",
                {"attendance": "present"}, format="json")
            self.assertEqual(r.status_code, 200)

        # 3) 4코트 채우기
        for idx in range(1, 5):
            r = self.client.post(f"/api/bands/match/{sid}/courts/{idx}/fill/", {}, format="json")
            self.assertEqual(r.status_code, 200, r.content)
            self.assertIsNotNone(r.json().get("match"), f"코트{idx} 채움 실패")

        seen_players = []
        # 4) 종료→자동 다음경기 30라운드 반복 (코트 라운드로빈)
        for rnd in range(30):
            idx = (rnd % 4) + 1
            r = self.client.post(f"/api/bands/match/{sid}/courts/{idx}/end/", {}, format="json")
            self.assertEqual(r.status_code, 200, f"라운드{rnd} 코트{idx} 종료 실패: {r.content}")
            body = r.json()
            self.assertFalse(body.get("needs_choice"), "모두 모드는 needs_choice 안 떠야")
            m = body.get("match")
            self.assertIsNotNone(m, f"라운드{rnd}: 다음 경기 자동생성 실패")
            # 매칭 유효성: 4명 서로 다름, 팀 2/2
            ids = [pl["participant_id"] for pl in m["team1"] + m["team2"]]
            self.assertEqual(len(ids), 4)
            self.assertEqual(len(set(ids)), 4, "한 경기에 같은 사람 중복")
            self.assertEqual(len(m["team1"]), 2)
            self.assertEqual(len(m["team2"]), 2)
            seen_players.append(set(ids))

        # 5) 종료 후 카운트 균등성 검증
        state = self._state(sid)
        totals = [p["total_games"] for p in state["participants"]]
        spread = max(totals) - min(totals)
        self.assertLessEqual(spread, 3, f"출전 편차 과대: {sorted(totals)}")
        self.assertGreater(min(totals), 0, "한 게임도 못 뛴 사람 존재")

        # 6) 다양성 sanity: 연속 라운드가 완전 동일 4명은 아님(어느정도 섞임)
        repeats = sum(1 for a, b in zip(seen_players, seen_players[1:]) if a == b)
        self.assertLess(repeats, 10, "같은 4명이 너무 자주 반복")
