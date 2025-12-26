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


class ContestListView(ListView):
    model = Contest
    template_name = "contest/index.html"
    context_object_name = "contests"

    def get_queryset(self):
        queryset = Contest.objects.all()

        # category 필터링
        category_param = self.request.GET.get('category')
        if category_param:
            try:
                category_id = int(category_param)
                queryset = queryset.filter(category_id=category_id)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid category parameter: {category_param}, error: {e}")

        # 검색 필터링
        search = self.request.GET.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(region_detail__icontains=search)
            )

        # 승급/비승급 필터링
        qualifying_list = self.request.GET.getlist('qualifying')
        if qualifying_list:
            # true와 false가 모두 선택된 경우 필터링하지 않음
            if len(qualifying_list) == 1:
                if 'true' in qualifying_list:
                    queryset = queryset.filter(is_qualifying=True)
                elif 'false' in qualifying_list:
                    queryset = queryset.filter(is_qualifying=False)

        # 스폰서 필터링
        sponsor_list = self.request.GET.getlist('sponsor')
        if sponsor_list:
            # sponsor 값이 숫자(ID)인지 문자열(이름)인지 확인
            sponsor_ids = []
            for sponsor_value in sponsor_list:
                try:
                    # 숫자로 변환 가능하면 ID로 처리
                    sponsor_id = int(sponsor_value)
                    sponsor_ids.append(sponsor_id)
                except (ValueError, TypeError):
                    # 숫자가 아니면 이름으로 처리하여 Sponsor 객체에서 찾기
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

        # 아무 필터도 선택되지 않은 경우, 종료되지 않은 대회만 표시
        has_any_filter = (
            category_param or
            search or
            qualifying_list or
            sponsor_list or
            region_list
        )
        
        if not has_any_filter:
            from django.utils import timezone
            from django.db.models import Q
            today = timezone.now().date()
            # schedule_end가 None이거나 오늘 이후인 대회만 표시
            queryset = queryset.filter(
                Q(schedule_end__isnull=True) | Q(schedule_end__gte=today)
            )

        # select_related를 제거하여 데이터베이스에 잘못된 FK 값이 있어도 크래시 방지
        # category와 sponsor는 개별적으로 접근하며 try-except로 처리
        # prefetch_related로 이미지들을 미리 로드 (N+1 쿼리 방지)
        # only()를 사용하여 필요한 필드만 선택
        # sponsor_id는 마이그레이션 이슈로 인해 제외 (나중에 안전하게 접근)
        return queryset.prefetch_related('images').only(
            'id', 'title', 'slug', 'schedule_start', 'schedule_end',
            'region', 'region_detail', 'participant_reward', 'category_id', 'is_qualifying'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 캘린더용 전체 대회 데이터 (필터링 없이)
        # sponsor_id는 마이그레이션 이슈로 인해 제외 (나중에 안전하게 접근)
        all_contests = Contest.objects.all().prefetch_related('images', 'category').only(
            'id', 'title', 'slug', 'schedule_start', 'schedule_end',
            'region', 'region_detail', 'participant_reward', 'category_id', 'is_qualifying'
        )

        # contest_data 생성 시 category가 None이거나 잘못된 경우 처리
        # 캘린더는 전체 대회를 표시해야 하므로 all_contests 사용
        contest_data_list = []
        for contest in all_contests:
            try:
                category_data = None
                if contest.category_id:  # category_id가 있는지 먼저 확인
                    try:
                        # category 객체에 안전하게 접근
                        category = contest.category
                        if category:
                            category_data = {
                                "id": int(category.id),
                                "name": category.name,
                                "color": category.color,
                            }
                    except (AttributeError, ValueError, TypeError, Exception) as e:
                        logger.warning(f"Error accessing category for contest {contest.id}: {e}")
                        category_data = None
                
                sponsor_name = None
                try:
                    # sponsor_id가 숫자인지 확인
                    sponsor_id_value = getattr(contest, 'sponsor_id', None)
                    if sponsor_id_value:
                        # sponsor_id가 숫자인지 확인
                        try:
                            int(sponsor_id_value)  # 숫자로 변환 가능한지 확인
                            # sponsor 객체에 안전하게 접근
                            sponsor = contest.sponsor
                            if sponsor:
                                sponsor_name = sponsor.name
                        except (ValueError, TypeError):
                            # sponsor_id가 문자열이면 무시 (마이그레이션 이슈)
                            logger.warning(f"Contest {contest.id} has invalid sponsor_id: {sponsor_id_value}")
                            sponsor_name = None
                except (AttributeError, ValueError, TypeError, Exception) as e:
                    logger.warning(f"Error accessing sponsor for contest {contest.id}: {e}")
                    sponsor_name = None
                
                contest_data_list.append({
                    "title": contest.title,
                    "slug": contest.slug,
                    "schedule_start": contest.schedule_start.isoformat() if contest.schedule_start else None,
                    "schedule_end": contest.schedule_end.isoformat() if contest.schedule_end else None,
                    "period_display": contest.get_period_display(),
                    "location": contest.get_location_display(),
                    "image_url": None,
                    # contest.images.first.image.url if contest.images.first else None,
                    "participant_reward": contest.participant_reward or None,
                    "sponsor": sponsor_name,
                    "category": category_data,
                })
            except Exception as e:
                # 개별 contest 처리 중 에러가 발생하면 로그만 남기고 계속 진행
                logger.warning(f"Error processing contest {contest.id}: {e}")
                continue
        
        context["contest_data"] = json.dumps(contest_data_list, cls=DjangoJSONEncoder)
        # 모든 카테고리 리스트를 context에 추가 (id 순으로 정렬)
        try:
            categories = ContestCategory.objects.all().order_by('id')
        except Exception as e:
            logger.error(f"Error ordering categories: {e}")
            categories = ContestCategory.objects.all()
        context["categories"] = categories

        # 각 카테고리별 대회 목록을 딕셔너리로 생성 (캘린더용이므로 전체 데이터 사용)
        contests_by_category = {}
        for category in categories:
            try:
                category_id = int(category.id)
                category_contests = []
                for contest in all_contests:
                    try:
                        # category_id를 직접 비교하여 안전하게 처리
                        if contest.category_id and int(contest.category_id) == category_id:
                            category_contests.append(contest)
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"Error comparing category for contest {contest.id}: {e}")
                        continue
                contests_by_category[str(category_id)] = category_contests
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Error processing category {category.id}: {e}")
                continue
        context["contests_by_category"] = contests_by_category

        # admin에서 설정한 배너 이미지 목록
        banners_qs = BadmintokBanner.objects.filter(is_active=True)
        banner_images = []
        for banner in banners_qs:
            if not banner.image:
                continue
            banner_images.append(
                {
                    "url": banner.image.url,
                    "alt": banner.alt_text or banner.title or "",
                    "link_url": banner.link_url,
                }
            )
        context["banner_images"] = banner_images

        # 스폰서 목록
        sponsors = Sponsor.objects.all().order_by('name')
        context["sponsors"] = sponsors

        # 지역 목록 (Contest.Region.choices)
        context["regions"] = Contest.Region.choices

        # 접수 마감이 5일 이내인 대회 (최대 5개, 우측 사이드바용)
        try:
            from django.utils import timezone

            today = timezone.now().date()
            deadline = today + timedelta(days=5)

            closing_soon_contests = (
                Contest.objects.filter(
                    registration_end__isnull=False,
                    registration_end__gte=today,
                    registration_end__lte=deadline,
                )
                .prefetch_related("images")
                .only(
                    "id",
                    "title",
                    "slug",
                    "registration_end",
                    "schedule_start",
                    "schedule_end",
                    "region",
                    "region_detail",
                    "participant_reward",
                    "category_id",
                    "sponsor_id",
                    "is_qualifying",
                )
                .order_by("registration_end", "schedule_start")[:5]
            )
        except Exception as e:
            logger.error(f"Error fetching closing_soon_contests: {e}")
            closing_soon_contests = Contest.objects.none()

        context["closing_soon_contests"] = closing_soon_contests

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
        context["schedule_entries"] = contest.schedules.all()

        # 대회 이미지들 가져오기 (순서대로)
        context["contest_images"] = contest.images.all().order_by('order', 'id')

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
