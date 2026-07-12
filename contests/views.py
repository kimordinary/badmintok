import json
from datetime import datetime, date, timedelta
import logging

from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .models import Contest, ContestCategory, Sponsor
from badmintok.models import BadmintokBanner

logger = logging.getLogger(__name__)


def get_week_of_month(date_obj):
    """날짜가 속한 월의 주차를 계산합니다 (1일이 포함된 주가 1주차)"""
    if not date_obj:
        return None
    
    # 해당 날짜의 일수
    day = date_obj.day
    
    # 월의 첫 날
    first_day = date_obj.replace(day=1)
    # 첫 날의 요일 (0=월요일, 6=일요일)
    first_day_weekday = first_day.weekday()
    
    # 1일이 포함된 주가 1주차
    # 첫 날이 월요일(0)이면: 1-7일 = 1주차, 8-14일 = 2주차, ...
    # 첫 날이 일요일(6)이면: 1일만 = 1주차 끝, 2-8일 = 2주차, ...
    # 첫 날이 화요일(1)이면: 1-6일 = 1주차, 7-13일 = 2주차, ...
    
    # 첫 주에 포함된 일수 계산
    # 첫 날이 월요일이면 첫 주는 7일, 화요일이면 6일, ... 일요일이면 1일
    days_in_first_week = 7 - first_day_weekday
    
    if day <= days_in_first_week:
        # 1주차에 포함
        return 1
    else:
        # 첫 주를 제외한 일수
        remaining_days = day - days_in_first_week
        # 남은 일수를 7로 나눠서 주차 계산 (첫 주 제외)
        week_number = (remaining_days - 1) // 7 + 2  # +2는 1주차가 이미 포함되었으므로
        return week_number


class ContestPreviewView(ListView):
    """대회 목록 정식 페이지 (캘린더+리스트 리디자인).

    /badminton-tournament/ 의 정식 목록 뷰. 대회 데이터를 파생필드와 함께 JSON으로
    내려주고, 필터/캘린더/리스트는 프론트(바닐라 JS)에서 처리한다. SEO를 위해
    템플릿에서 동일 데이터를 SSR 링크 목록 + JSON-LD로도 렌더한다.
    """
    model = Contest
    template_name = "contest/preview.html"
    context_object_name = "contests"

    def get_queryset(self):
        # 캘린더가 과거 월도 탐색하므로 schedule_start 기준 윈도우로 로드한다
        # (2개월 전 1일 ~ 미래 전체). 종료일 기준 제외는 null-end 누수/과거월 누락
        # 문제가 있어 사용하지 않는다. 더 오래된 종료 대회는 /archive 담당.
        from django.utils import timezone

        today = timezone.now().date()
        y, m = today.year, today.month - 2
        while m < 1:
            m += 12
            y -= 1
        window_start = date(y, m, 1)
        return (
            Contest.objects.filter(schedule_start__gte=window_start)
            .select_related("category", "sponsor")
            .order_by("schedule_start")
        )

    # 핸드오프 샘플 데이터 (?demo=1 일 때 사용. DB 미변경).
    # [name, date, region, venue, deadline|None, scope, grade, sponsor|None, views, endDate|None]
    DEMO_RAW = [
        ['제6회 저소득층 학생선수 한마음 배드민턴 축제', '2026-06-06', '서울', '잠실학생체육관', '2026-06-03', '전국', '비승급', None, 142, None],
        ['제19회 산청군 산림조합장기 배드민턴대회', '2026-06-06', '경남', '산청국민체육센터', '2026-06-04', '지역', '비승급', None, 88, None],
        ['제1회 대전광역시 여성 배드민턴대회', '2026-06-07', '대전', '한밭종합운동장 보조경기장', '2026-06-04', '지역', '승급', None, 211, None],
        ['제2회 목포시 체육회장기 배드민턴대회', '2026-06-09', '전남', '목포실내체육관', '2026-06-04', '지역', '승급', None, 55, None],
        ['제6회 윤봉길배 전국배드민턴대회', '2026-06-13', '충남', '예산스포츠센터', '2026-06-05', '전국', '승급', '요넥스 코리아', 173, '2026-06-14'],
        ['스포츠클럽 디비전리그 시니어 남자부 3차전', '2026-06-13', '경기', '수원 실내체육관', '2026-06-05', '전국', '비승급', None, 162, '2026-06-14'],
        ['제19회 화성특례시 시장기 배드민턴대회', '2026-06-14', '경기', '화성종합경기타운', '2026-06-08', '지역', '승급', None, 304, None],
        ['제13회 부산 남구 청년부 배드민턴대회', '2026-06-14', '부산', '남구 국민체육센터 제2체육관', '2026-06-07', '지역', '승급', '인투스', 195, None],
        ['제8회 박원욱병원장배 부산 여성연맹대회', '2026-06-20', '부산', '강서실내체육관', '2026-06-10', '지역', '승급', '버디 엑시언트', 179, '2026-06-21'],
        ['2026 인천 디비전리그 시니어부 남자 A 3차전', '2026-06-20', '인천', '인천 도원체육관', '2026-06-12', '지역', '승급', None, 138, '2026-06-21'],
        ['경동도시가스배 울산 MBC 초청 전국 OPEN', '2026-06-21', '울산', '동천체육관', '2026-06-12', '전국', '비승급', None, 103, None],
        ['2026 안동시장배 배드민턴 리그전 2차', '2026-06-27', '경북', '용상다목적체육관', '2026-06-18', '지역', '승급', None, 96, '2026-06-28'],
        ['제13회 강서구배드민턴협회 여성부 대회', '2026-06-28', '부산', '강서체육공원 보조경기장', '2026-06-15', '지역', '승급', '스트로커스', 211, None],
        ['제4회 렉스배 SSP 전국 배드민턴대회', '2026-07-05', '서울', '강서구 마곡배드민턴장', '2026-06-25', '전국', '비승급', 'OPTIMO', 94, None],
    ]

    def _demo_items(self, today):
        from datetime import date as _date
        dow_names = ["일", "월", "화", "수", "목", "금", "토"]
        items = []
        for i, r in enumerate(self.DEMO_RAW):
            name, ds, region, venue, deadline, scope, grade, sponsor, views, ende = r
            start = _date.fromisoformat(ds)
            end = _date.fromisoformat(ende) if ende else start
            multi_day = bool(ende and ende != ds)
            dl = _date.fromisoformat(deadline) if deadline else None
            dday = (dl - today).days if dl else None
            if dday is None:
                status = "open"
            elif dday < 0:
                status = "closed"
            elif dday <= 5:
                status = "soon"
            else:
                status = "open"
            items.append({
                "id": "demo" + str(i),
                "name": name,
                "slug": "#",
                "url": "#",
                "date": start.isoformat(),
                "endDate": end.isoformat() if multi_day else None,
                "region": region,
                "venue": venue,
                "deadline": dl.isoformat() if dl else None,
                "scope": scope,
                "grade": grade,
                "sponsor": sponsor,
                "views": views,
                "day": start.day, "month": start.month, "year": start.year,
                "weekday": start.weekday(),
                "dow": dow_names[(start.weekday() + 1) % 7],
                "endDay": end.day, "endMonth": end.month,
                "endDow": dow_names[(end.weekday() + 1) % 7],
                "multiDay": multi_day, "dday": dday, "status": status,
            })
        items.sort(key=lambda x: x["date"])
        return items

    def get_context_data(self, **kwargs):
        from django.utils import timezone

        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        day_names = ["월", "화", "수", "목", "금", "토", "일"]
        dow_names = ["일", "월", "화", "수", "목", "금", "토"]

        if self.request.GET.get("demo"):
            demo_items = self._demo_items(today)
            context["preview_data"] = json.dumps(demo_items, cls=DjangoJSONEncoder)
            context["items"] = demo_items
            context["regions"] = [r[0] for r in Contest.Region.choices]
            context["today_iso"] = today.isoformat()
            context["today"] = today
            context["canonical_url"] = self.request.build_absolute_uri(self.request.path)
            context["is_demo"] = True
            return context

        items = []
        for c in self.object_list:
            if not c.schedule_start:
                continue
            start = c.schedule_start
            end = c.schedule_end or start
            multi_day = bool(c.schedule_end and c.schedule_end != start)

            # scope: category명이 '전국'/'지역' 두 값. 없으면 '지역'으로 간주.
            scope = "지역"
            try:
                if c.category_id and c.category and c.category.name in ("전국", "지역"):
                    scope = c.category.name
            except Exception as e:
                logger.warning(f"preview scope error contest {c.id}: {e}")

            # dday: 접수 마감 기준 남은 일수 (디자인의 deadline 기준)
            dday = None
            if c.registration_end:
                dday = (c.registration_end - today).days

            if dday is None:
                status = "open"
            elif dday < 0:
                status = "closed"
            elif dday <= 5:
                status = "soon"
            else:
                status = "open"

            sponsor_name = None
            try:
                if c.sponsor_id:
                    int(c.sponsor_id)
                    if c.sponsor:
                        sponsor_name = c.sponsor.name
            except (ValueError, TypeError):
                sponsor_name = None
            except Exception as e:
                logger.warning(f"preview sponsor error contest {c.id}: {e}")

            items.append({
                "id": c.id,
                "name": c.title,
                "slug": c.slug,
                "url": f"/badminton-tournament/{c.slug}/",
                "date": start.isoformat(),
                "endDate": end.isoformat() if multi_day else None,
                "region": c.get_region_display(),
                "venue": c.region_detail or "",
                "deadline": c.registration_end.isoformat() if c.registration_end else None,
                "scope": scope,
                "grade": "승급" if c.is_qualifying else "비승급",
                "sponsor": sponsor_name,
                "views": c.view_count or 0,
                "day": start.day,
                "month": start.month,
                "year": start.year,
                "weekday": start.weekday(),          # 0=월
                "dow": dow_names[(start.weekday() + 1) % 7],  # 한글 요일(일=0 기준 표기)
                "endDay": end.day,
                "endMonth": end.month,
                "endDow": dow_names[(end.weekday() + 1) % 7],
                "multiDay": multi_day,
                "dday": dday,
                "status": status,
            })

        items.sort(key=lambda x: x["date"])
        context["preview_data"] = json.dumps(items, cls=DjangoJSONEncoder)
        context["items"] = items
        context["regions"] = [r[0] for r in Contest.Region.choices]
        context["today_iso"] = today.isoformat()
        context["today"] = today
        context["last_updated"] = max((c.updated_at for c in self.object_list if c.updated_at), default=None)
        context["canonical_url"] = self.request.build_absolute_uri(self.request.path)
        return context


class ContestArchiveView(ListView):
    """종료된 대회 아카이브 페이지"""
    model = Contest
    template_name = "contest/archive.html"
    context_object_name = "contests"
    paginate_by = 20

    def get_queryset(self):
        from django.utils import timezone
        from django.db.models import Q

        queryset = Contest.objects.all()
        today = timezone.now().date()

        # 종료된 대회만 표시 (schedule_end가 오늘보다 이전)
        queryset = queryset.filter(
            schedule_end__isnull=False,
            schedule_end__lt=today
        )

        # 검색 필터링
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(region_detail__icontains=search)
            )

        # 승급/비승급 필터링
        qualifying_list = self.request.GET.getlist('qualifying')
        if qualifying_list:
            if len(qualifying_list) == 1:
                if 'true' in qualifying_list:
                    queryset = queryset.filter(is_qualifying=True)
                elif 'false' in qualifying_list:
                    queryset = queryset.filter(is_qualifying=False)

        # 스폰서 필터링
        sponsor_list = self.request.GET.getlist('sponsor')
        if sponsor_list:
            sponsor_ids = []
            for sponsor_value in sponsor_list:
                try:
                    sponsor_id = int(sponsor_value)
                    sponsor_ids.append(sponsor_id)
                except (ValueError, TypeError):
                    try:
                        from .models import Sponsor
                        sponsor_obj = Sponsor.objects.get(name=sponsor_value)
                        sponsor_ids.append(sponsor_obj.id)
                    except Sponsor.DoesNotExist:
                        logger.warning(f"Sponsor with name '{sponsor_value}' not found")
                        continue

            if sponsor_ids:
                queryset = queryset.filter(sponsor_id__in=sponsor_ids)

        # 지역 필터링
        region_list = self.request.GET.getlist('region')
        if region_list:
            queryset = queryset.filter(region__in=region_list)

        # 최신 종료 순으로 정렬
        queryset = queryset.order_by('-schedule_end', '-schedule_start')

        return queryset.select_related('category', 'sponsor').prefetch_related('images')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 스폰서 목록
        sponsors = Sponsor.objects.all().order_by('name')
        context["sponsors"] = sponsors

        # 지역 목록
        context["regions"] = Contest.Region.choices

        # 카테고리 목록
        try:
            categories = ContestCategory.objects.all().order_by('id')
        except Exception as e:
            logger.error(f"Error ordering categories: {e}")
            categories = ContestCategory.objects.all()
        context["categories"] = categories

        return context


class ContestDetailView(DetailView):
    model = Contest
    template_name = "contest/detail.html"
    context_object_name = "contest"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contest = context["contest"]
        # 세션 기반 조회수 중복 방지 (3시간 제한)
        session_key = "viewed_contests"
        viewed_contests = self.request.session.get(session_key, {})
        contest_id_str = str(contest.id)
        current_time = datetime.now()

        should_increase = True
        if contest_id_str in viewed_contests:
            last_viewed_time = datetime.fromisoformat(viewed_contests[contest_id_str])
            if (current_time - last_viewed_time).total_seconds() < 10800:
                should_increase = False

        if should_increase:
            contest.increase_view_count()
            viewed_contests[contest_id_str] = current_time.isoformat()
            self.request.session[session_key] = viewed_contests
            self.request.session.modified = True
        schedule_entries = contest.schedules.all()
        context["schedule_entries"] = schedule_entries

        # 종목 요약 텍스트 생성 (예: "혼복, 여복, 남복, 단식")
        all_events = []
        seen = set()
        for entry in schedule_entries:
            for event in entry.get_events_display():
                if event not in seen:
                    seen.add(event)
                    all_events.append(event)
        context["events_summary"] = ", ".join(all_events)
        context["all_events"] = all_events

        # 대회 이미지들 가져오기 (순서대로)
        context["contest_images"] = contest.images.all().order_by('order', 'id')

        # === SEO: title / description / body / canonical / OG image / JSON-LD ===
        import json as _json
        from django.urls import reverse as _reverse
        from django.templatetags.static import static as _static

        context["seo_title"] = contest.get_seo_title()
        context["seo_description"] = contest.get_seo_description()
        context["seo_body_text"] = contest.get_seo_body_text()
        context["canonical_url"] = self.request.build_absolute_uri(
            _reverse("contests:detail", args=[contest.slug])
        )

        # og:image — 첫 이미지가 있으면 사용 (사이즈 판단은 1단계 결과 따라 향후 추가)
        first_img = contest.images.order_by("order", "id").first()
        if first_img and first_img.image:
            context["og_image_url"] = self.request.build_absolute_uri(first_img.image.url)
        else:
            context["og_image_url"] = self.request.build_absolute_uri(
                _static("images/og-image/OG image (1).png")
            )

        context["contest_jsonld"] = _json.dumps(
            contest.get_jsonld(request=self.request),
            ensure_ascii=False,
        )

        # 기본값 설정
        context["same_week_contests"] = []
        context["week_number"] = None
        context["contest_month"] = None
        context["contest_year"] = None
        
        if contest.schedule_start:
            # 현재 대회의 주차 계산
            week_number = get_week_of_month(contest.schedule_start)
            month = contest.schedule_start.month
            year = contest.schedule_start.year
            
            logger.debug(f"Current contest: {contest.title}, date: {contest.schedule_start}, week: {week_number}")
            
            # 같은 월의 다른 대회들 (현재 대회 제외)
            same_month_contests = Contest.objects.filter(
                schedule_start__year=year,
                schedule_start__month=month,
            ).exclude(pk=contest.pk).prefetch_related('images')
            
            logger.debug(f"Same month contests count: {same_month_contests.count()}")
            
            # 주차에 맞는 대회들만 필터링
            filtered_contests = []
            for other_contest in same_month_contests:
                if other_contest.schedule_start:
                    other_week = get_week_of_month(other_contest.schedule_start)
                    logger.debug(f"Other contest: {other_contest.title}, date: {other_contest.schedule_start}, week: {other_week}")
                    if other_week == week_number:
                        filtered_contests.append(other_contest)
                        logger.debug(f"Added to filtered: {other_contest.title}")
            
            logger.debug(f"Filtered contests count: {len(filtered_contests)}")
            
            context["same_week_contests"] = filtered_contests
            context["week_number"] = week_number
            context["contest_month"] = month
            context["contest_year"] = year

        return context


@login_required
@require_POST
def contest_like(request, slug):
    """대회 좋아요 토글"""
    contest = get_object_or_404(Contest, slug=slug)
    user = request.user

    if user in contest.likes.all():
        contest.likes.remove(user)
        liked = False
    else:
        contest.likes.add(user)
        liked = True

    return JsonResponse({
        'success': True,
        'liked': liked,
        'like_count': contest.like_count
    })
