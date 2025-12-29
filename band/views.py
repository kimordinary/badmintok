from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
import copy
from .models import (
    Band, BandMember, BandPost, BandPostImage, BandComment,
    BandPostLike, BandCommentLike, BandVote, BandVoteOption, BandVoteChoice,
    BandSchedule, BandScheduleApplication, BandScheduleImage
)
from .forms import (
    BandForm, BandPostForm, BandCommentForm, BandVoteForm,
    BandScheduleForm, BandScheduleApplicationForm
)
from badmintok.models import BadmintokBanner, Notice


def band_list(request):
    """밴드 목록 페이지"""
    from .models import Band, BandPost
    from django.http import HttpResponseRedirect
    from urllib.parse import urlencode
    
    band_type = request.GET.get("type", "")
    
    # type 파라미터가 없으면 번개 탭으로 리다이렉트
    if not band_type:
        params = request.GET.copy()
        params['type'] = 'flash'
        return HttpResponseRedirect(f"{request.path}?{params.urlencode()}")
    
    # 번개 탭일 때는 번개 타입 밴드와 모임/동호회의 스케줄 모두 조회
    if band_type == "flash":
        from datetime import date
        today = timezone.now().date()
        
        # 1. 번개 타입(band_type="flash") 밴드 조회 (번개는 승인 없이도 표시)
        # 본인이 만든 번개도 표시되도록 수정
        if request.user.is_authenticated:
            flash_bands = Band.objects.filter(
                Q(is_public=True, band_type="flash") |  # 공개된 번개
                Q(created_by=request.user, band_type="flash")  # 본인이 만든 번개
            ).prefetch_related("schedules")
        else:
            flash_bands = Band.objects.filter(
                is_public=True,
                band_type="flash"
            ).prefetch_related("schedules")
        
        # 2. 모임/동호회 타입 밴드 중 미래 스케줄이 있는 것 조회
        # 본인이 만든 모임의 스케줄도 승인 전이라도 표시되도록 수정
        if request.user.is_authenticated:
            schedule_bands = Band.objects.filter(
                Q(is_public=True, is_approved=True) |  # 승인된 모임/동호회
                Q(created_by=request.user, band_type__in=["group", "club"])  # 본인이 만든 모임/동호회 (승인 전이라도)
            ).filter(
                band_type__in=["group", "club"],
                schedules__start_datetime__gte=timezone.now()
            ).prefetch_related("schedules").distinct()
        else:
            schedule_bands = Band.objects.filter(
                is_public=True,
                is_approved=True,
                band_type__in=["group", "club"],
                schedules__start_datetime__gte=timezone.now()
            ).prefetch_related("schedules").distinct()
        
        # 지역 필터
        region = request.GET.get("region", "")
        if region and region != "all":
            flash_bands = flash_bands.filter(region=region)
            schedule_bands = schedule_bands.filter(region=region)
        
        # 검색
        search = request.GET.get("search", "")
        if search:
            flash_bands = flash_bands.filter(Q(name__icontains=search) | Q(description__icontains=search))
            schedule_bands = schedule_bands.filter(Q(name__icontains=search) | Q(description__icontains=search))
        
        # 번개 타입 밴드 처리
        bands_with_schedules = []
        for band in flash_bands:
            # 밴드가 실제로 존재하는지 확인
            try:
                _ = band.id
                _ = band.name
            except (Band.DoesNotExist, AttributeError):
                continue
            
            # 번개 타입은 스케줄이 있어도 첫 번째 스케줄 사용, 없으면 None
            schedule = band.schedules.filter(start_datetime__gte=timezone.now()).order_by("start_datetime").first()
            if not schedule:
                schedule = band.schedules.order_by("-start_datetime").first()
            
            # 디데이 정보 계산
            if schedule:
                schedule_date = schedule.start_datetime.date()
                days_diff = (schedule_date - today).days
                if days_diff < 0:
                    d_day_text = "종료"
                    d_day_is_past = True
                elif days_diff == 0:
                    d_day_text = "D-0"
                    d_day_is_past = False
                else:
                    d_day_text = f"D-{days_diff}"
                    d_day_is_past = False
                band.first_schedule = schedule
                band.d_day_text = d_day_text
                band.d_day_is_past = d_day_is_past
            else:
                # 스케줄이 없으면 기본값 설정
                band.first_schedule = None
                band.d_day_text = None
                band.d_day_is_past = False
            
            band.total_members = band.members.filter(status="active").count()
            band.total_posts = band.posts.count()
            
            # 번개의 지역 정보 사용
            if band.flash_region_detail:
                band.parent_band_region = band.flash_region_detail
            elif band.region and band.region != "all":
                band.parent_band_region = band.get_region_display()
            else:
                band.parent_band_region = ""
            band.parent_band_region_code = band.region
            band.parent_band_name = band.name
            
            bands_with_schedules.append(band)
        
        # 모임/동호회의 스케줄 처리 - 각 스케줄을 별도 항목으로 표시
        for band in schedule_bands:
            # 밴드가 실제로 존재하는지 확인 (삭제된 밴드 제외)
            try:
                # 밴드 객체 접근 테스트
                _ = band.id
                _ = band.name
            except (Band.DoesNotExist, AttributeError):
                continue

            # 각 밴드의 모든 미래 스케줄을 가져옴
            future_schedules = band.schedules.filter(start_datetime__gte=timezone.now()).order_by("start_datetime")
            
            # 각 스케줄마다 별도 항목으로 추가
            for schedule in future_schedules:
                # 일정이 실제로 존재하는지 확인
                try:
                    _ = schedule.id
                    _ = schedule.start_datetime
                except (BandSchedule.DoesNotExist, AttributeError):
                    continue
                
                # 디데이 정보 계산
                schedule_date = schedule.start_datetime.date()
                days_diff = (schedule_date - today).days
                if days_diff < 0:
                    d_day_text = "종료"
                    d_day_is_past = True
                elif days_diff == 0:
                    d_day_text = "D-0"
                    d_day_is_past = False
                else:
                    d_day_text = f"D-{days_diff}"
                    d_day_is_past = False
                
                # 각 스케줄마다 밴드 객체를 복사하여 별도 항목으로 추가
                band_copy = copy.copy(band)
                band_copy.first_schedule = schedule
                band_copy.d_day_text = d_day_text
                band_copy.d_day_is_past = d_day_is_past
                band_copy.total_members = band.members.filter(status="active").count()
                band_copy.total_posts = band.posts.count()
                
                # 모임/동호회의 지역 정보 사용
                if band.flash_region_detail:
                    band_copy.parent_band_region = band.flash_region_detail
                elif band.region and band.region != "all":
                    band_copy.parent_band_region = band.get_region_display()
                else:
                    band_copy.parent_band_region = ""
                band_copy.parent_band_region_code = band.region
                band_copy.parent_band_name = band.name  # 모임/동호회 이름 저장
                
                bands_with_schedules.append(band_copy)
        
        # 일정 날짜순으로 정렬 (가까운 날짜부터, 스케줄이 없는 번개는 맨 뒤로)
        from datetime import timedelta
        bands_with_schedules.sort(key=lambda b: b.first_schedule.start_datetime if b.first_schedule else timezone.now() + timedelta(days=365))
        
        # 페이지네이션
        paginator = Paginator(bands_with_schedules, 20)
        page = request.GET.get("page", 1)
        bands_page = paginator.get_page(page)
        
        # 사용자가 가입한 밴드 (모임/동호회만, 번개 제외)
        my_bands = []
        if request.user.is_authenticated:
            my_bands = Band.objects.filter(
                members__user=request.user,
                members__status="active",
                band_type__in=["group", "club"]
            ).annotate(
                total_members=Count("members", filter=Q(members__status="active")),
                total_posts=Count("posts")
            ).order_by("-members__joined_at")[:5]
        
        # 인기 번개 (멤버 수가 많은 번개, 번개는 승인 없이도 표시)
        popular_bands = Band.objects.filter(
            is_public=True,
            band_type="flash"
        ).prefetch_related("schedules").annotate(
            total_members=Count("members", filter=Q(members__status="active"))
        ).order_by("-total_members", "-created_at")[:5]
        
        # 인기 번개에 디데이 정보 및 조회수 추가
        from django.db.models import Sum
        for band in popular_bands:
            schedule = band.schedules.first()
            if schedule and schedule.start_datetime:
                schedule_date = schedule.start_datetime.date()
                days_diff = (schedule_date - today).days
                if days_diff < 0:
                    band.d_day_text = "종료"
                    band.d_day_is_past = True
                elif days_diff == 0:
                    band.d_day_text = "D-0"
                    band.d_day_is_past = False
                else:
                    band.d_day_text = f"D-{days_diff}"
                    band.d_day_is_past = False
            else:
                band.d_day_text = None
                band.d_day_is_past = False
            
            # 조회수 계산 (밴드의 모든 게시글 조회수 합산)
            band.total_views = band.posts.aggregate(total=Sum('view_count'))['total'] or 0
            
            # 참가자수 정보 (스케줄이 있으면 스케줄 정보 사용)
            if schedule:
                band.current_participants = schedule.current_participants or 0
                band.max_participants = schedule.max_participants or 0
            else:
                band.current_participants = band.total_members or 0
                band.max_participants = None
            
            # 모임/동호회 이름 사용
            band.parent_band_name = band.name
        
        # 권역만 표시 (전체, 수도권, 부산권, 대구권, 광주권, 대전권, 울산권, 제주권)
        region_choices = [
            ("all", "전체"),
            ("capital", "수도권"),
            ("busan", "영남권"),
            ("daegu", "대구권"),
            ("gwangju", "호남권"),
            ("daejeon", "충청권"),
            ("ulsan", "울산권"),
            ("jeju", "제주권"),
        ]
        
        # 배너 이미지 가져오기
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

        # 고정된 공지사항 가져오기 (최신 1개)
        pinned_notice = Notice.objects.filter(is_pinned=True).order_by("-created_at").first()

        return render(request, "band/list.html", {
            "bands": bands_page,  # 번개 탭: 번개 밴드 리스트
            "posts": None,  # 명확히 None으로 설정
            "my_bands": my_bands,
            "search": search,
            "current_type": band_type,
            "current_region": region or "all",  # 번개 탭도 지역 필터 적용
            "regions": region_choices,
            "popular_bands": popular_bands,
            "banner_images": banner_images,
            "pinned_notice": pinned_notice,
        })
    
    # 모임/동호회 탭일 때는 밴드 리스트 표시 (일정 정보도 함께 가져오기)
    # 승인된 모임/동호회 또는 본인이 만든 모임 표시
    if request.user.is_authenticated:
        # 승인된 모임/동호회 또는 본인이 만든 모임
        bands = Band.objects.filter(
            Q(is_public=True, is_approved=True) |  # 승인된 모임
            Q(created_by=request.user, band_type__in=["group", "club"])  # 본인이 만든 모임 (승인 전이라도)
        ).filter(
            band_type__in=["group", "club"]  # 모임/동호회만
        )
    else:
        # 비로그인 사용자는 승인된 모임만 표시
        bands = Band.objects.filter(
            is_public=True,
            is_approved=True,  # 관리자 승인된 것만
            band_type__in=["group", "club"]  # 모임/동호회만
        )
    
    bands = bands.annotate(
        total_members=Count("members", filter=Q(members__status="active")),
        total_posts=Count("posts")
    ).prefetch_related("schedules").order_by("-created_at")
    
    if band_type:
        # band_type이 일치하거나 categories에 포함된 경우 필터링
        bands = bands.filter(
            Q(band_type=band_type) | 
            Q(categories__contains=band_type)
        )
    
    # 지역 필터
    region = request.GET.get("region", "")
    if region and region != "all":
        bands = bands.filter(region=region)
    
    # 검색
    search = request.GET.get("search", "")
    if search:
        bands = bands.filter(Q(name__icontains=search) | Q(description__icontains=search))
    
    # 페이지네이션
    paginator = Paginator(bands, 12)
    page = request.GET.get("page", 1)
    bands_page = paginator.get_page(page)

    # 각 밴드의 설명에서 위치 정보를 분리 (\"... 위치: ...\" 형태)
    for band in bands_page:
        desc = band.description or ""
        band.base_description = desc
        band.location_text = ""
        if "위치:" in desc:
            base, loc = desc.split("위치:", 1)
            band.base_description = base.strip()
            band.location_text = loc.strip()
    
    # 사용자가 가입한 밴드 (모임/동호회만, 번개 제외)
    my_bands = []
    if request.user.is_authenticated:
        my_bands = Band.objects.filter(
            members__user=request.user,
            members__status="active",
            band_type__in=["group", "club"]
        ).annotate(
            total_members=Count("members", filter=Q(members__status="active")),
            total_posts=Count("posts")
        ).order_by("-members__joined_at")[:5]
    
    # 인기 모임 (멤버 수가 많은 모임, 현재 탭에 맞는 타입) - 승인된 것만
    popular_bands_type = band_type if band_type else "group"
    popular_bands = Band.objects.filter(
        is_public=True,
        is_approved=True,  # 관리자 승인된 것만
        band_type=popular_bands_type
    ).annotate(
        total_members=Count("members", filter=Q(members__status="active"))
    ).order_by("-total_members", "-created_at")[:5]
    
    # 권역만 표시 (전체, 수도권, 부산권, 대구권, 광주권, 대전권, 울산권, 제주권)
    region_choices = [
        ("all", "전체"),
        ("capital", "수도권"),
        ("busan", "영남권"),
        ("daegu", "대구권"),
        ("gwangju", "호남권"),
        ("daejeon", "충청권"),
        ("ulsan", "울산권"),
        ("jeju", "제주권"),
    ]
    
    # 배너 이미지 가져오기
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

    # 고정된 공지사항 가져오기 (최신 1개)
    pinned_notice = Notice.objects.filter(is_pinned=True).order_by("-created_at").first()

    return render(request, "band/list.html", {
        "posts": None,  # 명확히 None으로 설정
        "bands": bands_page,  # 모임/동호회 탭: 밴드 리스트
        "my_bands": my_bands,
        "search": search,
        "current_type": band_type,
        "current_region": region or "all",
        "regions": region_choices,
        "banner_images": banner_images,
        "popular_bands": popular_bands,
        "pinned_notice": pinned_notice,
    })


@login_required
def band_create(request):
    """밴드 생성"""
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    band_type = request.GET.get("type", "")
    
    # 모임 생성 제한 확인
    if request.user.band_creation_blocked_until:
        if timezone.now() < request.user.band_creation_blocked_until:
            blocked_until = request.user.band_creation_blocked_until.strftime("%Y년 %m월 %d일 %H:%M")
            messages.error(
                request,
                f"모임 삭제로 인해 {blocked_until}까지 모임을 생성할 수 없습니다."
            )
            return redirect("band:list")
        else:
            # 제한 기간이 지났으면 필드 초기화
            request.user.band_creation_blocked_until = None
            request.user.save()
    
    # 모임/동호회 생성 시: 소셜 로그인 사용자 또는 관리자만 생성 가능
    # GET 요청 시에만 체크 (POST 요청은 폼 제출 후 처리)
    if request.method == "GET" and band_type in ["group", "club"]:
        if not request.user.is_social_auth and not (request.user.is_staff or request.user.is_superuser):
            messages.error(
                request,
                "모임/동호회를 만들려면 카카오톡 등 소셜 로그인으로 가입한 사용자만 가능합니다. "
                "소셜 로그인으로 가입해주세요."
            )
            return redirect("band:list")
    
    # 번개 생성 시: 모임/동호회를 가지고 있는 모임장만 생성 가능
    if request.method == "GET" and band_type == "flash":
        # 사용자가 모임(group) 또는 동호회(club) 타입의 밴드에서 모임장(owner)인지 확인
        owned_groups_or_clubs = Band.objects.filter(
            created_by=request.user,
            band_type__in=["group", "club"]
        ).exists()
        
        # 또는 BandMember에서 owner 역할로 모임/동호회에 속해있는지 확인
        is_owner_of_group_or_club = BandMember.objects.filter(
            user=request.user,
            role="owner",
            status="active",
            band__band_type__in=["group", "club"]
        ).exists()
        
        if not (owned_groups_or_clubs or is_owner_of_group_or_club):
            messages.error(
                request,
                "번개를 만들려면 먼저 모임 또는 동호회를 만들어야 합니다. "
                "모임/동호회의 모임장만 번개를 생성할 수 있습니다."
            )
            return redirect("band:list")
    
    if request.method == "POST":
        # POST 요청 시에도 소셜 로그인 또는 관리자 체크 (보안을 위해)
        if band_type in ["group", "club"]:
            if not request.user.is_social_auth and not (request.user.is_staff or request.user.is_superuser):
                messages.error(
                    request,
                    "모임/동호회를 만들려면 카카오톡 등 소셜 로그인으로 가입한 사용자만 가능합니다. "
                    "소셜 로그인으로 가입해주세요."
                )
                return redirect("band:list")
        
        form = BandForm(request.POST, request.FILES)
        if form.is_valid():
            band = form.save(commit=False)
            band.created_by = request.user
            # URL 파라미터에서 타입 가져오기
            if band_type:
                band.band_type = band_type

            # 분류(categories) 저장 (쉼표 문자열)
            categories = form.cleaned_data.get("categories") or []
            if not categories and band_type:
                categories = [band_type]
            band.categories = ",".join(categories)
            
            # rejection_reason은 MySQL TEXT 타입이므로 기본값을 가질 수 없음
            # 첫 번째 save() 전에 반드시 명시적으로 설정해야 함
            # setattr를 사용하여 확실하게 설정
            setattr(band, 'rejection_reason', "")
            
            # 번개 타입은 자동 승인, 모임/동호회는 나중에 설정
            if band_type == "flash":
                band.is_approved = True
                band.is_public = True
            else:
                # 모임/동호회는 기본값 설정 (나중에 False로 변경됨)
                if not hasattr(band, 'is_approved') or band.is_approved is None:
                    band.is_approved = True  # 일단 True로 설정, 나중에 False로 변경
 
            # 모든 필드를 명시적으로 저장
            # 디버깅: 저장 전 필드 값 확인
            try:
                band.save()
            except Exception as e:
                # 오류 발생 시 필드 값을 다시 명시적으로 설정하고 재시도
                setattr(band, 'rejection_reason', "")
                if not hasattr(band, 'is_approved') or band.is_approved is None:
                    setattr(band, 'is_approved', True)
                band.save()
            
            # 모임장으로 멤버 추가
            BandMember.objects.create(
                band=band,
                user=request.user,
                role="owner",
                status="active"
            )
            
            # 번개 타입은 더 이상 독립적으로 생성하지 않음
            # 번개는 모임/동호회에서 schedule_create를 통해 생성됨
            if band_type == "flash":
                messages.error(
                    request,
                    "번개는 독립적으로 생성할 수 없습니다. "
                    "모임 또는 동호회를 만든 후, 해당 모임/동호회에서 번개를 생성해주세요."
                )
                return redirect("band:list")
            
            # 아래 코드는 실행되지 않음 (위에서 리다이렉트)
            if False and band_type == "flash":
                flash_description = request.POST.get("flash_description", "")
                flash_region = request.POST.get("flash_region", "")
                meeting_date = request.POST.get("meeting_date")
                meeting_time = request.POST.get("meeting_time")
                meeting_end_time = request.POST.get("meeting_end_time")
                meeting_location = request.POST.get("meeting_location", "")
                meeting_cost = request.POST.get("meeting_cost", "")
                meeting_capacity = request.POST.get("meeting_capacity", "20")
                
                # 선택한 지역을 region 필드에 저장 (권역으로 매핑)
                if flash_region:
                    # 구체 지역을 권역으로 매핑
                    region_mapping = {
                        # 수도권
                        "서울": "capital",
                        "인천": "capital",
                        "경기": "capital",
                        # 영남권
                        "부산": "busan",
                        "대구": "daegu",
                        "울산": "ulsan",
                        "경북": "busan",  # 영남권이지만 기존 busan 사용
                        "경남": "busan",  # 영남권이지만 기존 busan 사용
                        # 호남권
                        "광주": "gwangju",
                        "전북": "gwangju",  # 호남권이지만 기존 gwangju 사용
                        "전남": "gwangju",  # 호남권이지만 기존 gwangju 사용
                        # 충청권
                        "대전": "daejeon",
                        "세종": "daejeon",  # 충청권이지만 기존 daejeon 사용
                        "충북": "daejeon",  # 충청권이지만 기존 daejeon 사용
                        "충남": "daejeon",  # 충청권이지만 기존 daejeon 사용
                        # 강원권
                        "강원": "all",  # 강원권은 all로 처리
                        # 제주권
                        "제주": "jeju",
                    }
                    # 권역으로 저장
                    band.region = region_mapping.get(flash_region, "all")
                    # 구체 지역도 저장
                    band.flash_region_detail = flash_region
                
                # 번개 설명을 description 필드에 저장
                if flash_description:
                    band.description = flash_description
                    band.save(update_fields=["description", "region", "flash_region_detail"])
                elif flash_region:
                    band.save(update_fields=["region", "flash_region_detail"])
                
                if meeting_date and meeting_time:
                    try:
                        # 날짜와 시간을 합쳐서 datetime 생성
                        datetime_str = f"{meeting_date} {meeting_time}"
                        start_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                        start_datetime = timezone.make_aware(start_datetime)
                        
                        # 종료 시간 처리
                        end_datetime = None
                        if meeting_end_time:
                            end_datetime_str = f"{meeting_date} {meeting_end_time}"
                            end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                            end_datetime = timezone.make_aware(end_datetime)
                        
                        # 일정 생성
                        schedule_description = f"위치: {meeting_location}"
                        if meeting_cost:
                            schedule_description += f"\n참가비: {meeting_cost}원"
                        if flash_description:
                            schedule_description += f"\n\n{flash_description}"
                        
                        schedule = BandSchedule.objects.create(
                            band=band,
                            title=band.name,
                            description=schedule_description,
                            start_datetime=start_datetime,
                            end_datetime=end_datetime,
                            location=meeting_location,
                            max_participants=int(meeting_capacity) if meeting_capacity else 20,
                            requires_approval=False,
                            created_by=request.user
                        )
                    except Exception as e:
                        # 일정 생성 실패해도 밴드는 생성됨
                        pass
            else:
                # 모임/동호회 타입일 때 지역 정보 처리 및 관리자 승인 대기 상태로 설정
                group_region = request.POST.get("group_region", "")
                
                # 모임/동호회는 관리자 승인 대기 상태로 생성
                band.is_approved = False
                band.is_public = False  # 승인 전에는 비공개
                
                if group_region:
                    # 구체 지역을 권역으로 매핑 (번개와 동일한 매핑 사용)
                    region_mapping = {
                        # 수도권
                        "서울": "capital",
                        "인천": "capital",
                        "경기": "capital",
                        # 영남권
                        "부산": "busan",
                        "대구": "daegu",
                        "울산": "ulsan",
                        "경북": "busan",
                        "경남": "busan",
                        # 호남권
                        "광주": "gwangju",
                        "전북": "gwangju",
                        "전남": "gwangju",
                        # 충청권
                        "대전": "daejeon",
                        "세종": "daejeon",
                        "충북": "daejeon",
                        "충남": "daejeon",
                        # 강원권
                        "강원": "all",
                        # 제주권
                        "제주": "jeju",
                    }
                    # 권역으로 저장
                    band.region = region_mapping.get(group_region, "all")
                    # 구체 지역도 저장
                    band.flash_region_detail = group_region
                    band.save(update_fields=["is_approved", "is_public", "region", "flash_region_detail"])
                else:
                    # group_region이 없어도 기본값 저장
                    if not band.flash_region_detail:
                        band.flash_region_detail = ""
                    band.save(update_fields=["is_approved", "is_public"])
            
            if band_type in ["group", "club"]:
                messages.success(
                    request,
                    "모임/동호회 생성 요청이 완료되었습니다. 관리자 승인 후 생성 가능합니다!"
                )
            else:
                messages.success(request, "밴드가 생성되었습니다.")
            return redirect("band:detail", band_id=band.id)
    else:
        form = BandForm()
        # 초기값 설정
        if band_type:
            form.fields["band_type"].initial = band_type
    
    return render(request, "band/create.html", {
        "form": form,
        "band_type": band_type,
    })


@login_required
def band_update(request, band_id):
    """밴드 수정"""
    from django.utils import timezone
    from datetime import datetime
    
    band = get_object_or_404(Band, id=band_id)
    
    # 작성자 또는 모임장/관리자만 수정 가능
    member = band.members.filter(user=request.user, status="active").first()
    if band.created_by != request.user and (not member or member.role not in ["owner", "admin"]):
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("band:detail", band_id=band.id)
    
    band_type = band.band_type
    
    if request.method == "POST":
        form = BandForm(request.POST, request.FILES, instance=band)
        if form.is_valid():
            # 이미지 삭제 요청 처리
            remove_cover = request.POST.get("remove_cover_image") == "1"
            remove_profile = request.POST.get("remove_profile_image") == "1"

            if remove_cover and band.cover_image:
                band.cover_image.delete(save=False)
                band.cover_image = None
            if remove_profile and band.profile_image:
                band.profile_image.delete(save=False)
                band.profile_image = None

            # 분류(categories) 저장 (쉼표 문자열)
            categories = form.cleaned_data.get("categories") or []
            if not categories and band_type:
                categories = [band_type]
            band.categories = ",".join(categories)

            band = form.save()
            
            # 번개 타입일 때 일정 정보도 함께 수정
            if band_type == "flash":
                flash_description = request.POST.get("flash_description", "")
                flash_region = request.POST.get("flash_region", "")
                meeting_date = request.POST.get("meeting_date")
                meeting_time = request.POST.get("meeting_time")
                meeting_end_time = request.POST.get("meeting_end_time")
                meeting_location = request.POST.get("meeting_location", "")
                meeting_cost = request.POST.get("meeting_cost", "")
                meeting_capacity = request.POST.get("meeting_capacity", "20")
                
                # 선택한 지역을 region 필드에 저장 (권역으로 매핑)
                if flash_region:
                    # 구체 지역을 권역으로 매핑
                    region_mapping = {
                        # 수도권
                        "서울": "capital",
                        "인천": "capital",
                        "경기": "capital",
                        # 영남권
                        "부산": "busan",
                        "대구": "daegu",
                        "울산": "ulsan",
                        "경북": "busan",  # 영남권이지만 기존 busan 사용
                        "경남": "busan",  # 영남권이지만 기존 busan 사용
                        # 호남권
                        "광주": "gwangju",
                        "전북": "gwangju",  # 호남권이지만 기존 gwangju 사용
                        "전남": "gwangju",  # 호남권이지만 기존 gwangju 사용
                        # 충청권
                        "대전": "daejeon",
                        "세종": "daejeon",  # 충청권이지만 기존 daejeon 사용
                        "충북": "daejeon",  # 충청권이지만 기존 daejeon 사용
                        "충남": "daejeon",  # 충청권이지만 기존 daejeon 사용
                        # 강원권
                        "강원": "all",  # 강원권은 all로 처리
                        # 제주권
                        "제주": "jeju",
                    }
                    # 권역으로 저장
                    band.region = region_mapping.get(flash_region, "all")
                    # 구체 지역도 저장
                    band.flash_region_detail = flash_region
                
                # 번개 설명을 description 필드에 저장
                if flash_description:
                    band.description = flash_description
                    band.save(update_fields=["description", "region", "flash_region_detail"])
                elif flash_region:
                    band.save(update_fields=["region", "flash_region_detail"])
                
                # 일정 수정 (기존 일정이 있으면 업데이트, 없으면 생성)
                if meeting_date and meeting_time:
                    try:
                        datetime_str = f"{meeting_date} {meeting_time}"
                        start_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                        start_datetime = timezone.make_aware(start_datetime)
                        
                        # 종료 시간 처리
                        end_datetime = None
                        if meeting_end_time:
                            end_datetime_str = f"{meeting_date} {meeting_end_time}"
                            end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                            end_datetime = timezone.make_aware(end_datetime)
                        
                        schedule_description = f"위치: {meeting_location}"
                        if meeting_cost:
                            schedule_description += f"\n참가비: {meeting_cost}원"
                        if flash_description:
                            schedule_description += f"\n\n{flash_description}"
                        
                        # 기존 일정 찾기 (첫 번째 일정 사용)
                        schedule = band.schedules.first()
                        if schedule:
                            schedule.title = band.name
                            schedule.description = schedule_description
                            schedule.start_datetime = start_datetime
                            schedule.end_datetime = end_datetime
                            schedule.location = meeting_location
                            schedule.max_participants = int(meeting_capacity) if meeting_capacity else 20
                            schedule.save()
                        else:
                            # 일정이 없으면 생성
                            BandSchedule.objects.create(
                                band=band,
                                title=band.name,
                                description=schedule_description,
                                start_datetime=start_datetime,
                                end_datetime=end_datetime,
                                location=meeting_location,
                                max_participants=int(meeting_capacity) if meeting_capacity else 20,
                                requires_approval=False,
                                created_by=request.user
                            )
                    except Exception as e:
                        pass
            else:
                # 모임/동호회 타입일 때 지역 정보 처리
                group_region = request.POST.get("group_region", "")
                group_location = request.POST.get("group_location", "")
                
                # 지역 정보 저장
                if group_region:
                    # 구체 지역을 권역으로 매핑 (번개와 동일한 매핑 사용)
                    region_mapping = {
                        # 수도권
                        "서울": "capital",
                        "인천": "capital",
                        "경기": "capital",
                        # 영남권
                        "부산": "busan",
                        "대구": "daegu",
                        "울산": "ulsan",
                        "경북": "busan",
                        "경남": "busan",
                        # 호남권
                        "광주": "gwangju",
                        "전북": "gwangju",
                        "전남": "gwangju",
                        # 충청권
                        "대전": "daejeon",
                        "세종": "daejeon",
                        "충북": "daejeon",
                        "충남": "daejeon",
                        # 강원권
                        "강원": "all",
                        # 제주권
                        "제주": "jeju",
                    }
                    # 권역과 구체 지역 모두 저장 (flash_region_detail 필드 활용)
                    band.region = region_mapping.get(group_region, "all")
                    band.flash_region_detail = group_region  # 구체 지역 저장
                
                # 위치 정보를 description에 저장 (기존 위치 정보 제거 후 추가)
                if group_location:
                    # 기존 description에서 위치 정보 제거
                    import re
                    if band.description:
                        # "위치: ..." 패턴 제거
                        band.description = re.sub(r'\s*위치:\s*[^\n]+', '', band.description).strip()
                    
                    # 새로운 위치 정보 추가
                    if band.description:
                        band.description = f"{band.description}\n위치: {group_location}"
                    else:
                        band.description = f"위치: {group_location}"
                
                # 변경사항 저장
                update_fields = []
                if group_region:
                    update_fields.extend(["region", "flash_region_detail"])
                if group_location:
                    update_fields.append("description")
                
                if update_fields:
                    band.save(update_fields=update_fields)
            
            messages.success(request, "밴드가 수정되었습니다.")
            return redirect("band:detail", band_id=band.id)
    else:
        form = BandForm(instance=band)
        if band_type:
            form.fields["band_type"].initial = band_type
    
    # 번개 타입일 때 기존 일정 정보 가져오기 및 region 역매핑
    schedule = None
    flash_region = ""
    meeting_cost = ""
    group_region = ""
    group_location = ""
    
    if band_type == "flash":
        schedule = band.schedules.first()
        # 저장된 구체 지역 사용 (없으면 기본값)
        if band.flash_region_detail:
            flash_region = band.flash_region_detail
        else:
            # 하위 호환성을 위한 기본값
            reverse_region_mapping = {
                "capital": "서울",
                "busan": "부산",
                "daegu": "대구",
                "gwangju": "광주",
                "daejeon": "대전",
                "ulsan": "울산",
                "jeju": "제주",
                "all": "",
            }
            flash_region = reverse_region_mapping.get(band.region, "")
        
        # 일정 description에서 참가비 추출
        if schedule and schedule.description:
            import re
            cost_match = re.search(r'참가비:\s*(\d+)원', schedule.description)
            if cost_match:
                meeting_cost = cost_match.group(1)
    else:
        # 모임/동호회 타입일 때 지역 정보 추출
        # flash_region_detail 필드에서 구체 지역 가져오기 (저장된 구체 지역 사용)
        if band.flash_region_detail:
            group_region = band.flash_region_detail
        else:
            # 기존 모임의 경우 flash_region_detail이 없을 수 있으므로 region을 역매핑
            # 하지만 정확한 역매핑은 불가능하므로 기본값 사용
            reverse_region_mapping = {
                "capital": "서울",  # 기본값
                "busan": "부산",
                "daegu": "대구",
                "gwangju": "광주",
                "daejeon": "대전",
                "ulsan": "울산",
                "jeju": "제주",
                "all": "",
            }
            group_region = reverse_region_mapping.get(band.region, "")
        
        # description에서 위치 정보 추출
        if band.description:
            import re
            location_match = re.search(r'위치:\s*([^\n]+)', band.description)
            if location_match:
                group_location = location_match.group(1).strip()
            else:
                group_location = ""
        else:
            group_location = ""
    
    return render(request, "band/create.html", {
        "form": form,
        "band_type": band_type,
        "band": band,
        "schedule": schedule,
        "flash_region": flash_region,
        "meeting_cost": meeting_cost,
        "group_region": group_region,
        "group_location": group_location,
        "is_update": True,
    })


def band_detail(request, band_id):
    """밴드 상세 페이지 (게시판)"""
    band = get_object_or_404(Band, id=band_id)
    
    # 멤버 여부 확인
    is_member = False
    member = None
    is_creator = False
    if request.user.is_authenticated:
        member = band.members.filter(user=request.user).first()
        is_member = member and member.status == "active"
        is_creator = band.created_by == request.user
    
    # 모임/동호회는 승인된 것만 접근 가능 (생성자는 예외)
    if band.band_type in ["group", "club"]:
        if not band.is_approved and not is_creator:
            if band.rejection_reason:
                messages.error(
                    request,
                    f"이 모임/동호회는 승인 거부되었습니다. "
                    f"거부 사유: {band.rejection_reason}"
                )
            else:
                messages.error(
                    request,
                    "이 모임/동호회는 아직 관리자 승인 대기 중입니다."
                )
            return redirect("band:list")
    
    # 공개 밴드가 아니고 멤버가 아니면 접근 불가
    if not band.is_public and not is_member:
        messages.error(request, "이 밴드에 접근할 수 없습니다.")
        return redirect("band:list")
    
    # 활성 탭 (기본값: home)
    active_tab = request.GET.get("tab", "home")
    
    # 게시글 목록 (게시판 탭용) - 질문 제외
    posts = band.posts.filter(post_type__in=["general", "announcement", "schedule", "vote"]).select_related("author").order_by("-is_pinned", "-is_notice", "-created_at")
    
    # 검색
    search = request.GET.get("search", "")
    if search:
        posts = posts.filter(Q(title__icontains=search) | Q(content__icontains=search))
    
    # 홈 탭용 게시글 (최대 3개, 페이지네이션 없음)
    home_posts = None
    if active_tab == "home" or not active_tab:
        home_posts = list(posts[:3])
    
    # 페이지네이션 (게시판 탭용)
    paginator = Paginator(posts, 20)
    page = request.GET.get("page", 1)
    posts_page = paginator.get_page(page)
    
    
    # 번개 일정 목록 (번개 탭 및 홈 탭용)
    home_schedules = []
    schedules_page = None

    # 번개는 모임/동호회의 스케줄로만 관리됨
    # 원본 밴드의 모든 스케줄 조회 (최근 생성된 순서로)
    all_schedules = band.schedules.all().select_related("band").prefetch_related("applications__user").order_by("-created_at")

    # 중복 제거
    seen_ids = set()
    unique_schedules = []

    for schedule in all_schedules:
        if schedule.id not in seen_ids:
            seen_ids.add(schedule.id)
            unique_schedules.append(schedule)

    # D-day 계산
    today = timezone.now().date()
    for schedule in unique_schedules:
        schedule_date = schedule.start_datetime.date()
        days_diff = (schedule_date - today).days
        if days_diff < 0:
            schedule.d_day_text = "종료"
            schedule.d_day_is_past = True
        elif days_diff == 0:
            schedule.d_day_text = "D-0"
            schedule.d_day_is_past = False
        else:
            schedule.d_day_text = f"D-{days_diff}"
            schedule.d_day_is_past = False

    # 홈탭: 최대 2개만 표시
    if active_tab == "home" or not active_tab:
        home_schedules = unique_schedules[:2]

    # 번개탭: 페이지네이션 적용 (페이지당 5개)
    if active_tab == "flash":
        schedule_paginator = Paginator(unique_schedules, 5)
        schedule_page = request.GET.get("page", 1)
        schedules_page = schedule_paginator.get_page(schedule_page)
    
    # 질문 게시글 목록 (질문 탭 및 홈 탭용)
    question_posts = []
    if active_tab == "question" or active_tab == "home" or not active_tab:
        # 질문 타입 게시글만 필터링 (댓글도 함께 가져오기)
        question_posts = band.posts.filter(post_type="question").select_related("author").prefetch_related(
            "images",
            Prefetch("comments", queryset=BandComment.objects.select_related("author").order_by("created_at"))
        ).order_by("-created_at")[:20]
    
    # 멤버 목록
    members = band.members.filter(status="active").select_related("user").order_by(
        "-role", "joined_at"
    )[:10]
    
    # 전체 멤버 수
    total_member_count = band.members.filter(status="active").count()
    
    return render(request, "band/detail.html", {
        "band": band,
        "posts": posts_page,
        "home_posts": home_posts,
        "home_schedules": home_schedules,
        "schedules_page": schedules_page,
        "question_posts": question_posts,
        "members": members,
        "total_member_count": total_member_count,
        "is_member": is_member,
        "is_creator": is_creator,
        "member": member,
        "search": search,
        "active_tab": active_tab,
    })


@login_required
def band_join(request, band_id):
    """밴드 가입"""
    band = get_object_or_404(Band, id=band_id)
    
    # 이미 멤버인지 확인
    existing_member = band.members.filter(user=request.user).first()
    if existing_member:
        if existing_member.status == "active":
            messages.info(request, "이미 가입된 밴드입니다.")
        elif existing_member.status == "pending":
            messages.info(request, "가입 승인 대기 중입니다.")
        else:
            messages.error(request, "차단된 밴드입니다.")
        return redirect("band:detail", band_id=band_id)
    
    # 가입 처리
    if band.join_approval_required:
        status = "pending"
        messages.success(request, "가입 신청이 완료되었습니다. 승인을 기다려주세요.")
    else:
        status = "active"
        messages.success(request, "밴드에 가입되었습니다.")
    
    BandMember.objects.create(
        band=band,
        user=request.user,
        role="member",
        status=status
    )
    
    return redirect("band:detail", band_id=band_id)


@login_required
def band_leave(request, band_id):
    """밴드 탈퇴"""
    band = get_object_or_404(Band, id=band_id)
    member = band.members.filter(user=request.user).first()
    
    if not member:
        messages.error(request, "가입되지 않은 밴드입니다.")
        return redirect("band:detail", band_id=band_id)
    
    if member.role == "owner":
        messages.error(request, "모임장은 밴드를 탈퇴할 수 없습니다.")
        return redirect("band:detail", band_id=band_id)
    
    member.delete()
    messages.success(request, "밴드를 탈퇴했습니다.")
    return redirect("band:list")


@login_required
def band_delete_request(request, band_id):
    """모임 삭제 신청 (관리자만 가능)"""
    from django.utils import timezone
    
    band = get_object_or_404(Band, id=band_id)
    member = band.members.filter(user=request.user, status="active").first()
    
    # 관리자(owner/admin)만 삭제 신청 가능
    if not member or member.role not in ["owner", "admin"]:
        messages.error(request, "모임 삭제는 관리자만 신청할 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    # 이미 삭제 신청된 경우
    if band.deletion_requested:
        messages.info(request, "이미 삭제 신청이 접수되었습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if request.method == "POST":
        deletion_reason = request.POST.get("deletion_reason", "").strip()
        
        if not deletion_reason:
            messages.error(request, "삭제 사유를 입력해주세요.")
            return render(request, "band/delete_request.html", {
                "band": band,
                "member": member,
            })
        
        # 삭제 신청 처리
        band.deletion_requested = True
        band.deletion_reason = deletion_reason
        band.deletion_requested_at = timezone.now()
        band.save()
        
        messages.success(request, "모임 삭제 신청이 접수되었습니다. 관리자 승인 후 삭제됩니다.")
        return redirect("band:detail", band_id=band_id)
    
    # GET 요청 시 삭제 신청 폼 표시
    return render(request, "band/delete_request.html", {
        "band": band,
        "member": member,
    })


@login_required
def post_image_upload(request, band_id):
    """Quill Editor에서 이미지 업로드 (임시 저장)"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    band = get_object_or_404(Band, id=band_id)
    
    # 멤버 확인
    member = band.members.filter(user=request.user, status="active").first()
    if not member:
        return JsonResponse({"error": "밴드 멤버만 이미지를 업로드할 수 있습니다."}, status=403)
    
    if "image" not in request.FILES:
        return JsonResponse({"error": "이미지 파일이 없습니다."}, status=400)
    
    image_file = request.FILES["image"]
    
    # 이미지 파일 검증
    if not image_file.content_type.startswith("image/"):
        return JsonResponse({"error": "이미지 파일만 업로드할 수 있습니다."}, status=400)
    
    # 임시 이미지 저장 (post는 None으로 저장, 나중에 게시글 저장 시 연결)
    try:
        band_image = BandPostImage.objects.create(
            post=None,  # 임시로 None 저장
            image=image_file,
            order_index=0
        )
        return JsonResponse({
            "success": True,
            "url": band_image.image.url
        })
    except Exception as e:
        return JsonResponse({"error": f"이미지 업로드 실패: {str(e)}"}, status=500)


@login_required
def post_create(request, band_id):
    """게시글 작성"""
    import re
    from urllib.parse import urlparse
    
    band = get_object_or_404(Band, id=band_id)
    
    # 멤버 확인
    member = band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 게시글을 작성할 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if request.method == "POST":
        form = BandPostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.band = band
            post.author = request.user
            
            # 관리자만 고정/공지 설정 가능
            if member.role == "member":
                post.is_pinned = False
                post.is_notice = False
            
            post.save()
            
            # content에서 img 태그 추출하여 BandPostImage로 저장
            content = form.cleaned_data.get("content", "")
            if content:
                # img 태그에서 src 추출
                img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
                img_matches = re.findall(img_pattern, content)
                
                if img_matches:
                    # MEDIA_URL을 기준으로 이미지 경로 추출
                    from django.conf import settings
                    media_url = settings.MEDIA_URL
                    
                    for idx, img_url in enumerate(img_matches):
                        # 절대 URL인 경우 경로만 추출
                        if img_url.startswith("http"):
                            parsed = urlparse(img_url)
                            img_path = parsed.path
                        else:
                            img_path = img_url
                        
                        # MEDIA_URL 제거
                        if img_path.startswith(media_url):
                            img_path = img_path[len(media_url):]
                        
                        # 이미지 파일 경로로 BandPostImage 찾기 (post가 None인 임시 이미지)
                        try:
                            # 이미지 파일명으로 찾기
                            image_filename = img_path.split("/")[-1]
                            temp_image = BandPostImage.objects.filter(
                                post__isnull=True,
                                image__icontains=image_filename
                            ).order_by("-created_at").first()  # 최신 이미지 우선
                            
                            if temp_image:
                                # 임시 이미지를 게시글에 연결
                                temp_image.post = post
                                temp_image.order_index = idx
                                temp_image.save()
                            else:
                                # 임시 이미지를 찾지 못한 경우, content에서 base64 이미지인지 확인
                                # base64 이미지는 별도 처리 필요 (현재는 스킵)
                                pass
                        except Exception as e:
                            print(f"이미지 연결 실패: {e}")
            
            messages.success(request, "게시글이 작성되었습니다.")
            # 질문 타입이면 FAQ 탭으로 리다이렉트
            if post.post_type == "question":
                from django.urls import reverse
                return redirect(reverse("band:detail", args=[band_id]) + "?tab=question")
            return redirect("band:post_detail", band_id=band_id, post_id=post.id)
    else:
        form = BandPostForm(user=request.user)
    
    return render(request, "band/post_form.html", {
        "band": band,
        "form": form,
    })


def post_detail(request, band_id, post_id):
    """게시글 상세"""
    from datetime import datetime, timedelta
    
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost, id=post_id, band=band)
    
    # 조회수 증가 (1시간 내 중복 방지)
    if request.user.is_authenticated:
        # 세션에 조회한 게시글 정보 가져오기
        viewed_posts = request.session.get('viewed_posts', {})
        current_time = datetime.now().timestamp()
        
        # 해당 게시글을 조회한 시간 확인
        last_viewed = viewed_posts.get(str(post_id))
        
        # last_viewed를 float로 변환 (세션에서 문자열로 저장되었을 수 있음)
        try:
            if last_viewed is not None:
                last_viewed = float(last_viewed)
        except (ValueError, TypeError):
            last_viewed = None
        
        # 조회한 적이 없거나 1시간(3600초) 이상 경과한 경우에만 카운팅
        if not last_viewed or (current_time - last_viewed) >= 3600:
            post.view_count += 1
            post.save(update_fields=["view_count"])
            # 세션에 조회 시간 업데이트 (float로 명시적으로 저장)
            viewed_posts[str(post_id)] = float(current_time)
            request.session['viewed_posts'] = viewed_posts
    else:
        # 비로그인 사용자는 접근 불가하지만, 혹시 모를 경우를 대비
        post.view_count += 1
        post.save(update_fields=["view_count"])
    
    # 멤버 여부
    is_member = False
    member = None
    if request.user.is_authenticated:
        member = band.members.filter(user=request.user, status="active").first()
        is_member = member is not None
    
    # 좋아요 여부
    is_liked = False
    if request.user.is_authenticated:
        is_liked = BandPostLike.objects.filter(post=post, user=request.user).exists()
    
    # 댓글 목록
    comments = post.comments.select_related("author").prefetch_related("replies__author").filter(
        parent=None
    ).order_by("created_at")
    
    # 투표 정보
    vote = None
    user_vote_choices = []
    if post.post_type == "vote":
        try:
            vote = post.vote
            if request.user.is_authenticated:
                user_vote_choices = list(
                    BandVoteChoice.objects.filter(vote=vote, user=request.user).values_list("option_id", flat=True)
                )
        except:
            pass
    
    # 작성자 여부 확인
    is_author = request.user.is_authenticated and post.author == request.user
    
    return render(request, "band/post_detail.html", {
        "band": band,
        "post": post,
        "comments": comments,
        "is_member": is_member,
        "member": member,
        "is_liked": is_liked,
        "is_author": is_author,
        "vote": vote,
        "user_vote_choices": user_vote_choices,
    })


@login_required
def post_update(request, band_id, post_id):
    """게시글 수정"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost, id=post_id, band=band)
    
    # 작성자만 수정 가능
    if post.author != request.user:
        messages.error(request, "게시글 수정 권한이 없습니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    # 멤버 확인
    member = band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 게시글을 수정할 수 있습니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    if request.method == "POST":
        form = BandPostForm(request.POST, request.FILES, instance=post, user=request.user)
        if form.is_valid():
            post = form.save()
            
            # content에서 img 태그 추출하여 BandPostImage로 저장
            content = form.cleaned_data.get("content", "")
            if content:
                # img 태그에서 src 추출
                img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
                img_matches = re.findall(img_pattern, content)
                
                if img_matches:
                    # MEDIA_URL을 기준으로 이미지 경로 추출
                    from django.conf import settings
                    media_url = settings.MEDIA_URL
                    
                    # 기존 이미지 목록 가져오기
                    existing_images = list(post.images.all())
                    existing_image_urls = {img.image.url for img in existing_images}
                    
                    for idx, img_url in enumerate(img_matches):
                        # 절대 URL인 경우 경로만 추출
                        if img_url.startswith("http"):
                            parsed = urlparse(img_url)
                            img_path = parsed.path
                        else:
                            img_path = img_url
                        
                        # MEDIA_URL 제거
                        if img_path.startswith(media_url):
                            img_path = img_path[len(media_url):]
                        
                        # 이미지가 이미 게시글에 연결되어 있는지 확인
                        full_url = img_url if img_url.startswith("http") else (media_url + img_path.lstrip("/"))
                        if full_url in existing_image_urls:
                            # 이미 연결된 이미지는 순서만 업데이트
                            image_filename = img_path.split("/")[-1]
                            existing_img = next((img for img in existing_images if image_filename in img.image.name), None)
                            if existing_img:
                                existing_img.order_index = idx
                                existing_img.save()
                            continue
                        
                        # 이미지 파일 경로로 BandPostImage 찾기 (post가 None인 임시 이미지)
                        try:
                            # 이미지 파일명으로 찾기
                            image_filename = img_path.split("/")[-1]
                            temp_image = BandPostImage.objects.filter(
                                post__isnull=True,
                                image__icontains=image_filename
                            ).order_by("-created_at").first()  # 최신 이미지 우선
                            
                            if temp_image:
                                # 임시 이미지를 게시글에 연결
                                temp_image.post = post
                                temp_image.order_index = idx
                                temp_image.save()
                        except Exception as e:
                            print(f"이미지 연결 실패: {e}")
            
            messages.success(request, "게시글이 수정되었습니다.")
            return redirect("band:post_detail", band_id=band_id, post_id=post.id)
    else:
        form = BandPostForm(instance=post, user=request.user)
    
    return render(request, "band/post_form.html", {
        "band": band,
        "form": form,
        "post": post,
        "member": member,
        "is_update": True,
    })


@login_required
def post_delete(request, band_id, post_id):
    """게시글 삭제"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost, id=post_id, band=band)
    
    # 작성자만 삭제 가능
    if post.author != request.user:
        messages.error(request, "게시글 삭제 권한이 없습니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    if request.method == "POST":
        post.delete()
        messages.success(request, "게시글이 삭제되었습니다.")
        return redirect("band:detail", band_id=band_id)
    
    return render(request, "band/post_delete_confirm.html", {
        "band": band,
        "post": post,
    })


@login_required
def post_like(request, band_id, post_id):
    """게시글 좋아요 토글"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)
    
    like, created = BandPostLike.objects.get_or_create(post=post, user=request.user)
    
    if created:
        post.like_count += 1
        is_liked = True
    else:
        like.delete()
        post.like_count = max(0, post.like_count - 1)
        is_liked = False
    
    post.save(update_fields=["like_count"])
    
    return JsonResponse({"is_liked": is_liked, "like_count": post.like_count})


@login_required
def comment_create(request, band_id, post_id):
    """댓글 작성"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)
    
    # 멤버 확인
    member = post.band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 댓글을 작성할 수 있습니다.")
        # 질문 타입이면 FAQ 탭으로 리다이렉트
        if post.post_type == "question":
            from django.urls import reverse
            return redirect(reverse("band:detail", args=[band_id]) + "?tab=question")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    if request.method == "POST":
        # 질문 타입 게시글의 경우 모임장만 답변 작성 가능
        if post.post_type == "question":
            if not member or member.role != "owner":
                messages.error(request, "모임장만 답변을 작성할 수 있습니다.")
                from django.urls import reverse
                return redirect(reverse("band:detail", args=[band_id]) + "?tab=question")
        
        form = BandCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            # parent가 있으면 대댓글, 없으면 일반 댓글
            parent_id = request.POST.get("parent")
            if parent_id:
                try:
                    parent_comment = BandComment.objects.get(id=parent_id, post=post)
                    comment.parent = parent_comment
                except BandComment.DoesNotExist:
                    pass
            comment.save()
            
            # 댓글 수 증가
            post.comment_count += 1
            post.save(update_fields=["comment_count"])
            
            messages.success(request, "댓글이 작성되었습니다.")
    
    # 질문 타입이면 FAQ 탭으로 리다이렉트
    if post.post_type == "question":
        from django.urls import reverse
        return redirect(reverse("band:detail", args=[band_id]) + "?tab=question")
    return redirect("band:post_detail", band_id=band_id, post_id=post_id)


@login_required
def comment_update(request, band_id, post_id, comment_id):
    """댓글 수정"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)
    comment = get_object_or_404(BandComment, id=comment_id, post=post)
    
    # 작성자만 수정 가능
    if comment.author != request.user:
        messages.error(request, "댓글 수정 권한이 없습니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    # 멤버 확인
    member = post.band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 댓글을 수정할 수 있습니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    if request.method == "POST":
        form = BandCommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "댓글이 수정되었습니다.")
            return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    # GET 요청 시 수정 폼 표시 (템플릿에서 처리)
    return redirect("band:post_detail", band_id=band_id, post_id=post_id)


@login_required
def comment_delete(request, band_id, post_id, comment_id):
    """댓글 삭제"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)
    comment = get_object_or_404(BandComment, id=comment_id, post=post)
    
    # 작성자만 삭제 가능
    if comment.author != request.user:
        messages.error(request, "댓글 삭제 권한이 없습니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    # 멤버 확인
    member = post.band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 댓글을 삭제할 수 있습니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    if request.method == "POST":
        # 댓글 수 감소
        post.comment_count = max(0, post.comment_count - 1)
        post.save(update_fields=["comment_count"])
        
        comment.delete()
        messages.success(request, "댓글이 삭제되었습니다.")
    
    return redirect("band:post_detail", band_id=band_id, post_id=post_id)


@login_required
def vote_create(request, band_id):
    """투표 생성"""
    band = get_object_or_404(Band, id=band_id)
    
    # 멤버 확인
    member = band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 투표를 생성할 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if request.method == "POST":
        form = BandVoteForm(request.POST)
        if form.is_valid():
            # 게시글 먼저 생성
            post = BandPost.objects.create(
                band=band,
                author=request.user,
                title=form.cleaned_data["title"],
                content="",
                post_type="vote"
            )
            
            # 투표 생성
            vote = form.save(commit=False)
            vote.post = post
            vote.save()
            
            # 옵션 추가
            options_text = form.cleaned_data["options"]
            options_list = [opt.strip() for opt in options_text.split("\n") if opt.strip()]
            for idx, option_text in enumerate(options_list):
                BandVoteOption.objects.create(
                    vote=vote,
                    option_text=option_text,
                    order_index=idx
                )
            
            messages.success(request, "투표가 생성되었습니다.")
            return redirect("band:post_detail", band_id=band_id, post_id=post.id)
    else:
        form = BandVoteForm()
    
    return render(request, "band/vote_form.html", {
        "band": band,
        "form": form,
    })


@login_required
def vote_participate(request, band_id, post_id):
    """투표 참여"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)
    
    if post.post_type != "vote":
        messages.error(request, "투표 게시글이 아닙니다.")
        return redirect("band:post_detail", band_id=band_id, post_id=post_id)
    
    vote = get_object_or_404(BandVote, post=post)
    
    if request.method == "POST":
        option_ids = request.POST.getlist("options")
        
        if not option_ids:
            messages.error(request, "최소 하나의 옵션을 선택해주세요.")
            return redirect("band:post_detail", band_id=band_id, post_id=post_id)
        
        if not vote.is_multiple_choice and len(option_ids) > 1:
            messages.error(request, "단일 선택 투표입니다.")
            return redirect("band:post_detail", band_id=band_id, post_id=post_id)
        
        # 기존 선택 삭제
        BandVoteChoice.objects.filter(vote=vote, user=request.user).delete()
        
        # 새 선택 추가
        for option_id in option_ids:
            option = get_object_or_404(BandVoteOption, id=option_id, vote=vote)
            BandVoteChoice.objects.create(
                vote=vote,
                option=option,
                user=request.user
            )
            option.vote_count = BandVoteChoice.objects.filter(option=option).count()
            option.save()
        
        messages.success(request, "투표가 완료되었습니다.")
    
    return redirect("band:post_detail", band_id=band_id, post_id=post_id)


@login_required
@login_required
def schedule_create(request, band_id):
    """번개 생성 (방장만 가능) - 기존 번개 생성 페이지 폼 사용"""
    from datetime import datetime
    
    band = get_object_or_404(Band, id=band_id)
    
    # 방장(생성자)만 번개를 만들 수 있음
    if not request.user.is_authenticated:
        messages.error(request, "로그인이 필요합니다.")
        return redirect("band:detail", band_id=band_id)
    
    if band.created_by != request.user:
        messages.error(request, "번개는 모임/동호회 방장만 만들 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if request.method == "POST":
        # 기존 번개 생성 페이지와 동일한 필드 처리
        meeting_date = request.POST.get("meeting_date")
        meeting_time = request.POST.get("meeting_time")
        meeting_end_time = request.POST.get("meeting_end_time")
        meeting_location = request.POST.get("meeting_location", "")
        flash_region = request.POST.get("flash_region", "")
        flash_description = request.POST.get("flash_description", "")
        meeting_cost = request.POST.get("meeting_cost", "")
        meeting_capacity = request.POST.get("meeting_capacity", "20")
        
        # 날짜/시간 결합
        if meeting_date and meeting_time:
            try:
                start_datetime = datetime.strptime(
                    f"{meeting_date} {meeting_time}",
                    "%Y-%m-%d %H:%M"
                )
                start_datetime = timezone.make_aware(start_datetime)
                
                # 종료 시간 처리
                end_datetime = None
                if meeting_end_time:
                    end_datetime = datetime.strptime(
                        f"{meeting_date} {meeting_end_time}",
                        "%Y-%m-%d %H:%M"
                    )
                    end_datetime = timezone.make_aware(end_datetime)
            except ValueError:
                messages.error(request, "날짜/시간 형식이 올바르지 않습니다.")
                return render(request, "band/create.html", {
                    "band": None,
                    "band_type": "flash",
                    "is_update": False,
                    "form": None,
                    "parent_band": band,
                })
        else:
            messages.error(request, "날짜와 시간을 모두 입력해주세요.")
            return render(request, "band/create.html", {
                "band": None,
                "band_type": "flash",
                "is_update": False,
                "form": None,
                "parent_band": band,
            })
        
        # 번개 이름 생성 (모임 이름 + 날짜 + 시간) - 중복 방지를 위해 시간도 포함
        schedule_title = f"{band.name} - {meeting_date} {meeting_time}"
        
        # 참가비 정보를 description에 포함
        description = flash_description
        if meeting_cost:
            description += f"\n참가비: {meeting_cost}원"

        # 번개는 모임/동호회의 스케줄로만 관리 (별도의 flash 타입 Band 생성하지 않음)
        # 원본 모임/동호회에 스케줄 생성
        schedule = BandSchedule.objects.create(
            band=band,
            title=schedule_title,
            description=description,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=meeting_location,
            max_participants=int(meeting_capacity) if meeting_capacity else None,
            current_participants=0,
            requires_approval=False,
            created_by=request.user
        )
        
        # 이미지 저장 (최대 5장)
        images = request.FILES.getlist('schedule_images')
        for index, image in enumerate(images[:5]):  # 최대 5장까지만
            BandScheduleImage.objects.create(
                schedule=schedule,
                image=image,
                order=index
            )

        messages.success(request, "번개가 생성되었습니다.")
        from django.urls import reverse
        return redirect(f"{reverse('band:detail', args=[band_id])}?tab=flash")
    else:
        # GET 요청 시 기존 번개 생성 페이지 템플릿 사용
        return render(request, "band/create.html", {
            "band": None,
            "band_type": "flash",
            "is_update": False,
            "form": None,
            "parent_band": band,  # 부모 밴드 정보 전달
        })


@login_required
def schedule_update(request, band_id, schedule_id):
    """번개 수정 (방장만 가능)"""
    from datetime import datetime
    
    band = get_object_or_404(Band, id=band_id)
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band=band)
    
    # 방장(생성자) 또는 번개 작성자만 번개를 수정할 수 있음
    if band.created_by != request.user and schedule.created_by != request.user:
        messages.error(request, "번개는 모임/동호회 방장 또는 번개 작성자만 수정할 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if request.method == "POST":
        # 기존 번개 생성 페이지와 동일한 필드 처리
        flash_name = request.POST.get("name", "").strip()  # 사용자가 입력한 번개 이름
        meeting_date = request.POST.get("meeting_date")
        meeting_time = request.POST.get("meeting_time")
        meeting_end_time = request.POST.get("meeting_end_time")
        meeting_location = request.POST.get("meeting_location", "")
        flash_description = request.POST.get("flash_description", "")
        meeting_cost = request.POST.get("meeting_cost", "")
        meeting_capacity = request.POST.get("meeting_capacity", "20")
        flash_region = request.POST.get("flash_region", "")  # 지역 정보
        
        # 날짜/시간 결합
        if meeting_date and meeting_time:
            try:
                start_datetime = datetime.strptime(
                    f"{meeting_date} {meeting_time}",
                    "%Y-%m-%d %H:%M"
                )
                start_datetime = timezone.make_aware(start_datetime)
                
                # 종료 시간 처리
                end_datetime = None
                if meeting_end_time:
                    end_datetime = datetime.strptime(
                        f"{meeting_date} {meeting_end_time}",
                        "%Y-%m-%d %H:%M"
                    )
                    end_datetime = timezone.make_aware(end_datetime)
            except ValueError:
                messages.error(request, "날짜/시간 형식이 올바르지 않습니다.")
                return render(request, "band/create.html", {
                    "band": None,
                    "band_type": "flash",
                    "is_update": True,
                    "form": None,
                    "parent_band": band,
                    "schedule": schedule,
                })
        else:
            messages.error(request, "날짜와 시간을 모두 입력해주세요.")
            return render(request, "band/create.html", {
                "band": None,
                "band_type": "flash",
                "is_update": True,
                "form": None,
                "parent_band": band,
                "schedule": schedule,
            })
        
        # 번개 이름: 사용자가 입력한 이름이 있으면 사용, 없으면 기본값 (모임 이름 + 날짜 + 시간)
        if flash_name:
            schedule_title = flash_name
        else:
            schedule_title = f"{band.name} - {meeting_date} {meeting_time}"
        
        # 참가비 정보를 description에 포함
        description = flash_description
        if meeting_cost:
            description += f"\n참가비: {meeting_cost}원"
        
        # 스케줄 업데이트
        schedule.title = schedule_title
        schedule.description = description
        schedule.start_datetime = start_datetime
        schedule.end_datetime = end_datetime
        schedule.location = meeting_location
        schedule.max_participants = int(meeting_capacity) if meeting_capacity else None
        schedule.save()
        
        # 지역 정보를 부모 Band에 저장
        if flash_region:
            # 구체 지역을 권역으로 매핑
            region_mapping = {
                # 수도권
                "서울": "capital",
                "경기": "capital",
                "인천": "capital",
                # 영남권
                "부산": "yeongnam",
                "대구": "yeongnam",
                "울산": "yeongnam",
                "경남": "yeongnam",
                "경북": "yeongnam",
                # 호남권
                "광주": "honam",
                "전남": "honam",
                "전북": "honam",
                # 충청권
                "대전": "chungcheong",
                "충남": "chungcheong",
                "충북": "chungcheong",
                "세종": "chungcheong",
                # 강원권
                "강원": "gangwon",
                # 제주권
                "제주": "jeju",
            }
            band.region = region_mapping.get(flash_region, "all")
            band.flash_region_detail = flash_region
            band.save(update_fields=["region", "flash_region_detail"])
        
        # 기존 이미지 삭제 여부 확인
        delete_images = request.POST.getlist('delete_images')
        if delete_images:
            BandScheduleImage.objects.filter(
                schedule=schedule,
                id__in=delete_images
            ).delete()
        
        # 남은 기존 이미지들의 순서 재정렬
        remaining_images = schedule.images.all().order_by('order')
        for index, img in enumerate(remaining_images):
            img.order = index
            img.save()
        
        # 새 이미지 추가 (최대 5장)
        existing_count = schedule.images.count()
        images = request.FILES.getlist('schedule_images')
        for index, image in enumerate(images[:5 - existing_count]):  # 최대 5장까지만
            BandScheduleImage.objects.create(
                schedule=schedule,
                image=image,
                order=existing_count + index
            )
        
        messages.success(request, "번개가 수정되었습니다.")
        return redirect("band:detail", band_id=band_id)
    else:
        # GET 요청 시 기존 번개 생성 페이지 템플릿 사용
        # 스케줄 정보에서 기존 데이터 추출
        import re
        flash_description = schedule.description or ""
        meeting_cost = ""
        
        # description에서 참가비 추출
        if schedule.description:
            cost_match = re.search(r'참가비:\s*(\d+)원', schedule.description)
            if cost_match:
                meeting_cost = cost_match.group(1)
                # description에서 참가비 부분 제거
                flash_description = re.sub(r'\n참가비:\s*\d+원', '', flash_description).strip()
        
        # 기존 이미지 가져오기
        existing_images = schedule.images.all().order_by('order')
        
        # 지역 정보 가져오기 (부모 Band에서)
        flash_region = band.flash_region_detail or ""
        
        return render(request, "band/create.html", {
            "band": None,
            "band_type": "flash",
            "is_update": True,
            "form": None,
            "parent_band": band,  # 부모 밴드 정보 전달
            "schedule": schedule,  # 수정할 스케줄 정보 전달
            "flash_region": flash_region,  # 지역 정보 전달
            "flash_description": flash_description,  # 번개 설명 전달
            "meeting_cost": meeting_cost,  # 참가비 전달
            "existing_images": existing_images,  # 기존 이미지 전달
            "flash_description": flash_description,  # 번개 설명
            "meeting_cost": meeting_cost,  # 참가비
            "existing_images": existing_images,  # 기존 이미지
        })


def schedule_delete(request, band_id, schedule_id):
    """번개 삭제 (방장 또는 번개 작성자만 가능)"""
    band = get_object_or_404(Band, id=band_id)
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band=band)
    
    # 방장(생성자) 또는 번개 작성자만 번개를 삭제할 수 있음
    if band.created_by != request.user and schedule.created_by != request.user:
        messages.error(request, "번개는 모임/동호회 방장 또는 번개 작성자만 삭제할 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if request.method == "POST":
        # 스케줄 삭제 (관련 이미지도 CASCADE로 자동 삭제됨)
        schedule.delete()
        messages.success(request, "번개가 삭제되었습니다.")
        return redirect("band:detail", band_id=band_id)
    else:
        # GET 요청 시 삭제 확인 페이지로 리다이렉트 (또는 바로 삭제)
        messages.error(request, "잘못된 요청입니다.")
        return redirect("band:detail", band_id=band_id)


@login_required
def schedule_detail(request, band_id, schedule_id):
    """번개 참석 페이지 (신청/취소)"""
    import re
    
    band = get_object_or_404(Band, id=band_id)
    schedule = get_object_or_404(
        BandSchedule.objects.prefetch_related("images", "applications__user"),
        id=schedule_id,
        band=band
    )
    
    # 멤버 확인
    member = band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 볼 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    # 사용자 신청 여부
    user_application = None
    if request.user.is_authenticated:
        user_application = schedule.applications.filter(user=request.user).first()
    
    # 승인된 참가자 목록
    approved_participants = schedule.applications.filter(status="approved").select_related("user").order_by("applied_at")
    
    # 대기 중인 신청자 목록 (방장/관리자만)
    pending_applications = None
    can_manage = member.role in ["owner", "admin"]
    if can_manage:
        pending_applications = schedule.applications.filter(status="pending").select_related("user").order_by("-applied_at")
    
    # description에서 참가비 추출
    meeting_cost = ""
    if schedule.description:
        cost_match = re.search(r'참가비:\s*(\d+)원', schedule.description)
        if cost_match:
            meeting_cost = cost_match.group(1)
    
    return render(request, "band/schedule_detail.html", {
        "band": band,
        "schedule": schedule,
        "member": member,
        "user_application": user_application,
        "approved_participants": approved_participants,
        "pending_applications": pending_applications,
        "can_manage": can_manage,
        "meeting_cost": meeting_cost,
    })


@login_required
def schedule_apply(request, band_id, schedule_id):
    """일정 신청"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)
    
    # 멤버 확인
    member = schedule.band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 신청할 수 있습니다.")
        return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    
    # 이미 신청했는지 확인
    existing = schedule.applications.filter(user=request.user).first()
    if existing and existing.status in ["pending", "approved"]:
        messages.info(request, "이미 신청하셨습니다.")
        return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    
    # 신청 가능 여부 확인
    if schedule.application_deadline and schedule.application_deadline < timezone.now():
        messages.error(request, "신청 마감일이 지났습니다.")
        return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    
    if schedule.max_participants and schedule.current_participants >= schedule.max_participants:
        messages.error(request, "참가 인원이 마감되었습니다.")
        return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    
    if request.method == "POST":
        form = BandScheduleApplicationForm(request.POST)
        if form.is_valid():
            # 기존 신청이 있고 rejected나 cancelled 상태인 경우 업데이트
            if existing and existing.status in ["rejected", "cancelled"]:
                application = existing
                application.notes = form.cleaned_data.get("notes", "")
                application.status = "pending"
                application.applied_at = timezone.now()
                application.reviewed_at = None
                application.reviewed_by = None
                application.rejection_reason = ""
                application.save()
            else:
                # 새 신청 생성
                application = form.save(commit=False)
                application.schedule = schedule
                application.user = request.user
                application.status = "pending"
                application.save()
            
            messages.success(request, "신청이 완료되었습니다.")
            return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    else:
        form = BandScheduleApplicationForm()
    
    return render(request, "band/schedule_apply.html", {
        "band": schedule.band,
        "schedule": schedule,
        "form": form,
    })


@login_required
def schedule_application_approve(request, band_id, schedule_id, application_id):
    """일정 신청 승인"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)
    application = get_object_or_404(BandScheduleApplication, id=application_id, schedule=schedule)
    
    # 관리자 권한 확인
    member = schedule.band.members.filter(user=request.user, status="active").first()
    if not member or member.role not in ["owner", "admin"]:
        messages.error(request, "권한이 없습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if application.status != "pending":
        messages.error(request, "이미 처리된 신청입니다.")
        return redirect("band:detail", band_id=band_id)
    
    # 인원 체크
    if schedule.max_participants and schedule.current_participants >= schedule.max_participants:
        messages.error(request, "참가 인원이 마감되었습니다.")
        return redirect("band:detail", band_id=band_id)
    
    # 승인 처리
    application.status = "approved"
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save()
    
    schedule.current_participants += 1
    schedule.save(update_fields=["current_participants"])
    
    messages.success(request, "신청이 승인되었습니다.")
    return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)


@login_required
def schedule_application_reject(request, band_id, schedule_id, application_id):
    """일정 신청 거부"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)
    application = get_object_or_404(BandScheduleApplication, id=application_id, schedule=schedule)
    
    # 관리자 권한 확인
    member = schedule.band.members.filter(user=request.user, status="active").first()
    if not member or member.role not in ["owner", "admin"]:
        messages.error(request, "권한이 없습니다.")
        return redirect("band:detail", band_id=band_id)
    
    if application.status != "pending":
        messages.error(request, "이미 처리된 신청입니다.")
        return redirect("band:detail", band_id=band_id)
    
    if request.method == "POST":
        rejection_reason = request.POST.get("rejection_reason", "")
        application.status = "rejected"
        application.reviewed_at = timezone.now()
        application.reviewed_by = request.user
        application.rejection_reason = rejection_reason
        application.save()
        
        messages.success(request, "신청이 거부되었습니다.")
        return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    
    return render(request, "band/schedule_reject.html", {
        "band": schedule.band,
        "schedule": schedule,
        "application": application,
    })


@login_required
def schedule_application_cancel(request, band_id, schedule_id):
    """번개 참가 신청 취소"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)
    
    # 멤버 확인
    member = schedule.band.members.filter(user=request.user, status="active").first()
    if not member:
        messages.error(request, "밴드 멤버만 취소할 수 있습니다.")
        return redirect("band:detail", band_id=band_id)
    
    # 신청 확인
    application = schedule.applications.filter(user=request.user).first()
    if not application:
        messages.error(request, "신청 내역이 없습니다.")
        return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    
    # 취소 가능한 상태인지 확인 (대기중 또는 승인됨)
    if application.status not in ["pending", "approved"]:
        messages.error(request, "취소할 수 없는 상태입니다.")
        return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)
    
    # 취소 처리
    was_approved = application.status == "approved"
    application.status = "cancelled"
    application.reviewed_at = timezone.now()
    application.save()
    
    # 승인된 상태였다면 참가 인원 감소
    if was_approved:
        schedule.current_participants = max(0, schedule.current_participants - 1)
        schedule.save(update_fields=["current_participants"])
    
    messages.success(request, "참가 신청이 취소되었습니다.")
    return redirect("band:schedule_detail", band_id=band_id, schedule_id=schedule_id)

