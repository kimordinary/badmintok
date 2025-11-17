import json
from datetime import datetime, date
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from .models import Contest, ContestCategory

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


class ContestListView(ListView):
    model = Contest
    template_name = "contest/index.html"
    context_object_name = "contests"

    def get_queryset(self):
        return Contest.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contest_data"] = json.dumps(
            [
                {
                    "title": contest.title,
                    "slug": contest.slug,
                    "schedule_start": contest.schedule_start.isoformat() if contest.schedule_start else None,
                    "schedule_end": contest.schedule_end.isoformat() if contest.schedule_end else None,
                    "period_display": contest.get_period_display(),
                    "location": contest.location,
                    "image_url": contest.image.url if contest.image else None,
                    "participant_reward": contest.participant_reward or None,
                    "sponsor": contest.sponsor or None,
                    "category": {
                        "id": contest.category.id,
                        "name": contest.category.name,
                        "color": contest.category.color,
                    }
                    if contest.category
                    else None,
                }
                for contest in context["contests"]
            ],
            cls=DjangoJSONEncoder,
        )
        # 모든 카테고리 리스트를 context에 추가 (id 순으로 정렬)
        context["categories"] = ContestCategory.objects.all().order_by('id')
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
            ).exclude(pk=contest.pk)
            
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
