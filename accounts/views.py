import datetime
import os
import uuid
import json
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, TemplateView

from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count, Q
from django.core.paginator import Paginator

from .forms import UserSignupForm, UserProfileForm, PasswordChangeFormCustom, InquiryForm, RealNameForm
from .models import User, UserProfile, UserBlock, Report, Inquiry
from band.models import (
    Band, BandPost, BandComment, BandPostLike,
    BandScheduleApplication, BandVoteChoice, BandBookmark
)
from community.models import Post, Comment, PostShare
from contests.models import Contest


class SignupView(CreateView):
    template_name = "accounts/signup.html"
    form_class = UserSignupForm
    success_url = reverse_lazy("accounts:signup_success")

    def dispatch(self, request, *args, **kwargs):
        # staff 권한이 없으면 접근 불가
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "계정 생성 권한이 없습니다.")
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)


class SignupSuccessView(TemplateView):
    template_name = "accounts/signup_success.html"


@login_required
def mypage(request):
    """마이페이지 - 요약 대시보드"""
    user = request.user
    
    # 프로필 정보
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    # 각 섹션별 카운트만 조회 (요약 정보)
    my_bands_count = Band.objects.filter(
        members__user=user,
        members__status="active"
    ).count()

    created_bands_count = Band.objects.filter(created_by=user).count()
    bookmarked_bands_count = BandBookmark.objects.filter(user=user).count()
    band_posts_count = BandPost.objects.filter(author=user).count()
    band_comments_count = BandComment.objects.filter(author=user).count()
    liked_band_posts_count = BandPost.objects.filter(likes__user=user).distinct().count()
    schedule_applications_count = BandScheduleApplication.objects.filter(user=user).count()
    vote_choices_count = BandVoteChoice.objects.filter(user=user).count()
    community_posts_count = Post.objects.filter(author=user).count()
    comments_count = Comment.objects.filter(author=user).count()

    # 통합 게시물/댓글 카운트
    total_posts_comments_count = band_posts_count + band_comments_count + community_posts_count + comments_count

    return render(request, "accounts/mypage.html", {
        "profile": profile,
        "my_bands_count": my_bands_count,
        "created_bands_count": created_bands_count,
        "bookmarked_bands_count": bookmarked_bands_count,
        "total_posts_comments_count": total_posts_comments_count,
    })


@login_required
def profile_edit(request):
    """프로필 편집"""
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, "프로필이 성공적으로 수정되었습니다.")
            return redirect("accounts:mypage")
    else:
        form = UserProfileForm(instance=profile, user=user)
    
    return render(request, "accounts/profile_edit.html", {
        "form": form,
        "profile": profile,
    })


# 각 섹션별 상세 페이지 뷰들
@login_required
def mypage_bands(request):
    """내 모임 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    my_bands = Band.objects.filter(
        members__user=user,
        members__status="active"
    ).annotate(
        total_members=Count("members", filter=Q(members__status="active")),
        total_posts=Count("posts")
    ).order_by("-members__joined_at")
    
    paginator = Paginator(my_bands, per_page)
    bands_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_bands.html", {
        "bands_page": bands_page,
        "title": "내 모임",
    })


@login_required
def mypage_created_bands(request):
    """내가 만든 모임 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)

    created_bands = Band.objects.filter(created_by=user).order_by("-created_at")
    paginator = Paginator(created_bands, per_page)
    bands_page = paginator.get_page(page)

    return render(request, "accounts/mypage_bands.html", {
        "bands_page": bands_page,
        "title": "내가 만든 모임",
    })


@login_required
def mypage_bookmarked_bands(request):
    """관심 모임 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)

    # 북마크한 모임 조회 (북마크 생성일 기준 정렬)
    bookmarked_bands = Band.objects.filter(
        bookmarks__user=user
    ).order_by("-bookmarks__created_at")

    paginator = Paginator(bookmarked_bands, per_page)
    bands_page = paginator.get_page(page)

    return render(request, "accounts/mypage_bands.html", {
        "bands_page": bands_page,
        "title": "관심 모임",
    })


@login_required
def mypage_band_posts(request):
    """작성한 모임 게시글 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    band_posts = BandPost.objects.filter(author=user).order_by("-created_at")
    paginator = Paginator(band_posts, per_page)
    posts_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_band_posts.html", {
        "posts_page": posts_page,
        "title": "작성한 모임 게시글",
    })


@login_required
def mypage_band_comments(request):
    """작성한 모임 댓글 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    band_comments = BandComment.objects.filter(author=user).order_by("-created_at")
    paginator = Paginator(band_comments, per_page)
    comments_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_band_comments.html", {
        "comments_page": comments_page,
        "title": "작성한 모임 댓글",
    })


@login_required
def mypage_liked_band_posts(request):
    """좋아요한 모임 게시글 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    liked_band_posts = BandPost.objects.filter(likes__user=user).order_by("-created_at").distinct()
    paginator = Paginator(liked_band_posts, per_page)
    posts_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_band_posts.html", {
        "posts_page": posts_page,
        "title": "좋아요한 모임 게시글",
    })


@login_required
def mypage_schedule_applications(request):
    """참여한 일정 신청 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    schedule_applications = BandScheduleApplication.objects.filter(user=user).order_by("-applied_at")
    paginator = Paginator(schedule_applications, per_page)
    applications_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_schedule_applications.html", {
        "applications_page": applications_page,
        "title": "참여한 일정 신청",
    })


@login_required
def mypage_vote_choices(request):
    """참여한 투표 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    vote_choices = BandVoteChoice.objects.filter(user=user).order_by("-created_at")
    paginator = Paginator(vote_choices, per_page)
    choices_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_vote_choices.html", {
        "choices_page": choices_page,
        "title": "참여한 투표",
    })


@login_required
def mypage_community_posts(request):
    """작성한 커뮤니티 게시글 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    community_posts = Post.objects.filter(author=user).order_by("-created_at")
    paginator = Paginator(community_posts, per_page)
    posts_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_community_posts.html", {
        "posts_page": posts_page,
        "title": "작성한 게시글",
    })


@login_required
def mypage_liked_posts(request):
    """좋아요한 커뮤니티 게시글 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    liked_posts = Post.objects.filter(likes=user).order_by("-created_at").distinct()
    paginator = Paginator(liked_posts, per_page)
    posts_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_community_posts.html", {
        "posts_page": posts_page,
        "title": "좋아요한 게시글",
    })


@login_required
def mypage_comments(request):
    """작성한 커뮤니티 댓글 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    comments = Comment.objects.filter(author=user).order_by("-created_at")
    paginator = Paginator(comments, per_page)
    comments_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_comments.html", {
        "comments_page": comments_page,
        "title": "작성한 댓글",
    })


@login_required
def mypage_shared_posts(request):
    """공유한 게시글 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    shared_posts = Post.objects.filter(shares__user=user).order_by("-created_at").distinct()
    paginator = Paginator(shared_posts, per_page)
    posts_page = paginator.get_page(page)
    
    return render(request, "accounts/mypage_community_posts.html", {
        "posts_page": posts_page,
        "title": "공유한 게시글",
    })


@login_required
def mypage_liked_contests(request):
    """좋아요한 대회 상세"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)

    liked_contests = Contest.objects.filter(likes=user).order_by("-created_at").distinct()
    paginator = Paginator(liked_contests, per_page)
    contests_page = paginator.get_page(page)

    return render(request, "accounts/mypage_contests.html", {
        "contests_page": contests_page,
        "title": "좋아요한 대회",
    })


@login_required
def mypage_my_posts_comments(request):
    """통합 내 게시물/댓글 페이지"""
    user = request.user
    tab = request.GET.get('tab', 'posts')
    per_page = 20
    page = request.GET.get('page', 1)

    # 카운트 계산
    band_posts_count = BandPost.objects.filter(author=user).count()
    band_comments_count = BandComment.objects.filter(author=user).count()
    community_posts_count = Post.objects.filter(author=user).count()
    community_comments_count = Comment.objects.filter(author=user).count()

    total_posts_count = band_posts_count + community_posts_count
    total_comments_count = band_comments_count + community_comments_count

    if tab == 'comments':
        # 모임 댓글 + 커뮤니티 댓글 통합
        band_comments_list = list(BandComment.objects.filter(author=user).order_by("-created_at"))
        community_comments_list = list(Comment.objects.filter(author=user).order_by("-created_at"))

        # 타입 구분을 위한 wrapper
        all_comments = []
        for c in band_comments_list:
            all_comments.append({'type': 'band', 'item': c, 'created_at': c.created_at})
        for c in community_comments_list:
            all_comments.append({'type': 'community', 'item': c, 'created_at': c.created_at})

        # 날짜순 정렬
        all_comments.sort(key=lambda x: x['created_at'], reverse=True)

        paginator = Paginator(all_comments, per_page)
        items_page = paginator.get_page(page)
    else:
        # 모임 게시글 + 커뮤니티 게시글 통합
        band_posts_list = list(BandPost.objects.filter(author=user).order_by("-created_at"))
        community_posts_list = list(Post.objects.filter(author=user).order_by("-created_at"))

        all_posts = []
        for p in band_posts_list:
            all_posts.append({'type': 'band', 'item': p, 'created_at': p.created_at})
        for p in community_posts_list:
            all_posts.append({'type': 'community', 'item': p, 'created_at': p.created_at})

        # 날짜순 정렬
        all_posts.sort(key=lambda x: x['created_at'], reverse=True)

        paginator = Paginator(all_posts, per_page)
        items_page = paginator.get_page(page)

    return render(request, "accounts/mypage_my_posts_comments.html", {
        "items_page": items_page,
        "tab": tab,
        "total_posts_count": total_posts_count,
        "total_comments_count": total_comments_count,
        "title": "내 게시물/댓글",
    })


class KakaoLoginView(View):
    """카카오 로그인 시작 - REST API 방식으로 직접 리다이렉트"""
    def get(self, request):
        try:
            client_id = settings.KAKAO_CLIENT_ID
            redirect_uri = settings.KAKAO_REDIRECT_URI

            if not client_id:
                messages.error(request, "카카오 로그인 설정이 올바르지 않습니다. 관리자에게 문의하세요.")
                return redirect("accounts:login")

            if not redirect_uri:
                messages.error(request, "카카오 리다이렉트 URI가 설정되지 않았습니다. 관리자에게 문의하세요.")
                return redirect("accounts:login")

            # state 생성 및 세션에 저장
            state = uuid.uuid4().hex
            request.session["kakao_oauth_state"] = state
            request.session.save()

            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"카카오 로그인 시작 - state: {state}, session_key: {request.session.session_key}")

            # 요청할 권한 범위
            scope = "account_email profile_nickname"

            # 카카오 인증 URL 생성 및 리다이렉트
            from urllib.parse import urlencode
            params = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'state': state,
                'scope': scope
            }
            kakao_authorize_url = f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}"
            return redirect(kakao_authorize_url)
        except Exception as e:
            import traceback
            print(f"카카오 로그인 오류: {e}")
            print(traceback.format_exc())
            messages.error(request, f"카카오 로그인 중 오류가 발생했습니다: {str(e)}")
            return redirect("accounts:login")


class KakaoCallbackView(View):
    def get(self, request):
        state = request.GET.get("state")
        code = request.GET.get("code")
        error = request.GET.get("error")

        session_state = request.session.pop("kakao_oauth_state", None)

        # 디버깅 로그
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"카카오 콜백 - state: {state}, code: {code}, error: {error}, session_state: {session_state}")

        if error:
            logger.error(f"카카오 콜백 에러: {error}")
            messages.error(request, f"카카오 로그인에 실패했습니다: {error}")
            return redirect("accounts:login")
        
        if not code:
            logger.error("카카오 콜백: code가 없음")
            messages.error(request, "카카오 로그인에 실패했습니다. 인증 코드를 받지 못했습니다.")
            return redirect("accounts:login")
        
        if session_state != state:
            logger.error(f"카카오 콜백: state 불일치 - session_state: {session_state}, state: {state}")
            logger.error(f"카카오 콜백: request.get_host()={request.get_host()}, request.META.get('HTTP_HOST')={request.META.get('HTTP_HOST')}")
            logger.error(f"카카오 콜백: request.META.get('HTTP_X_FORWARDED_HOST')={request.META.get('HTTP_X_FORWARDED_HOST')}")
            logger.error(f"카카오 콜백: 세션 키={request.session.session_key}, 세션 전체={dict(request.session)}")
            # 세션 쿠키 정보 로깅
            if hasattr(request, 'COOKIES'):
                logger.error(f"카카오 콜백: 쿠키={dict(request.COOKIES)}")
            
            # 세션이 없을 경우: 카카오 콜백이 Nginx를 거치지 않고 직접 127.0.0.1:8080으로 들어온 경우
            # 이 경우 state만으로 검증하거나, 세션을 재생성해야 함
            # 보안상 state만으로는 충분하지 않으므로, 사용자에게 안내
            if session_state is None and state:
                logger.error("카카오 콜백: 세션이 없음 - 카카오 개발자 콘솔의 Redirect URI가 Nginx를 거치도록 설정되어야 함")
                messages.error(request, "카카오 로그인에 실패했습니다. 세션이 만료되었습니다. 카카오 개발자 콘솔의 Redirect URI를 'http://localhost/accounts/kakao'로 설정해주세요.")
            else:
                messages.error(request, "카카오 로그인에 실패했습니다. 세션이 만료되었거나 보안 검증에 실패했습니다.")
            return redirect("accounts:login")

        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_CLIENT_ID,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
        }

        client_secret = getattr(settings, "KAKAO_CLIENT_SECRET", None)
        if client_secret:
            token_data["client_secret"] = client_secret

        try:
            logger.error(f"카카오 토큰 요청 - redirect_uri: {settings.KAKAO_REDIRECT_URI}")
            token_response = requests.post(
                "https://kauth.kakao.com/oauth/token", data=token_data, timeout=5
            )
            logger.error(f"카카오 토큰 응답 상태: {token_response.status_code}")
            token_response.raise_for_status()
            token_json = token_response.json()
            logger.error(f"카카오 토큰 응답: {token_json}")
        except requests.RequestException as e:
            logger.error(f"카카오 토큰 요청 실패: {str(e)}, 응답: {token_response.text if 'token_response' in locals() else 'N/A'}")
            messages.error(request, "카카오 로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            return redirect("accounts:login")

        access_token = token_json.get("access_token")
        if not access_token:
            messages.error(request, "카카오 인증 토큰을 가져오지 못했습니다.")
            return redirect("accounts:login")

        try:
            user_info_response = requests.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.RequestException:
            messages.error(request, "카카오 사용자 정보를 가져오는 데 실패했습니다.")
            return redirect("accounts:login")

        kakao_account = user_info.get("kakao_account", {})
        email = kakao_account.get("email")
        # legal_name: 법적 이름 (실제 본명, 별도 동의 필요)
        # name: 카카오계정에 등록된 이름 (사용자가 설정한 이름일 수 있음)
        legal_name = kakao_account.get("legal_name")  # 실제 본명
        account_name = kakao_account.get("name")  # 카카오계정 이름 (본명이 아닐 수 있음)
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname")
        profile_image_url = profile.get("profile_image_url")
        is_default_image = profile.get("is_default_image", True)
        gender = kakao_account.get("gender")
        age_range = kakao_account.get("age_range")
        birthday = kakao_account.get("birthday")  # MMDD 형식
        birthyear = kakao_account.get("birthyear")
        phone_number = kakao_account.get("phone_number")

        if not email:
            messages.error(request, "카카오 계정에서 이메일 정보를 제공하지 않았습니다. 카카오 설정을 확인해주세요.")
            return redirect("accounts:login")

        defaults = {
            "activity_name": nickname or email.split("@")[0],
            "auth_provider": "kakao"  # 카카오 로그인 사용자 표시
        }
        user, created = User.objects.get_or_create(email=email, defaults=defaults)
        if created:
            user.set_unusable_password()
            user.save()
        else:
            # 기존 사용자도 카카오 로그인으로 업데이트
            update_fields = []
            if not user.auth_provider:
                user.auth_provider = "kakao"
                update_fields.append("auth_provider")
            if nickname and user.activity_name != nickname:
                user.activity_name = nickname
                update_fields.append("activity_name")
            if update_fields:
                user.save(update_fields=update_fields)

        profile_defaults = {}
        # 소셜 로그인에서 받은 이름은 실명으로 인정하지 않음
        # 사용자가 직접 실명을 입력하도록 실명 입력 화면을 항상 보여줌
        # 따라서 name 필드는 저장하지 않음

        if gender:
            gender_map = {
                "male": UserProfile.Gender.MALE,
                "female": UserProfile.Gender.FEMALE,
            }
            profile_defaults["gender"] = gender_map.get(gender, UserProfile.Gender.OTHER)

        if age_range:
            profile_defaults["age_range"] = age_range
        if birthyear and birthyear.isdigit():
            profile_defaults["birth_year"] = int(birthyear)
        if birthday and len(birthday) == 4:
            try:
                birth_month = int(birthday[:2])
                birth_day = int(birthday[2:])
                birth_year_value = int(birthyear) if birthyear and birthyear.isdigit() else 1900
                profile_defaults["birthday"] = datetime.date(birth_year_value, birth_month, birth_day)
            except ValueError:
                pass
        if phone_number:
            profile_defaults["phone_number"] = phone_number

        profile_obj, created_profile = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)

        update_fields = set()
        if not created_profile:
            for field, value in profile_defaults.items():
                if value and getattr(profile_obj, field) != value:
                    setattr(profile_obj, field, value)
                    update_fields.add(field)

        default_profile_path = "images/userprofile/user.png"

        if is_default_image:
            current_name = profile_obj.profile_image.name if profile_obj.profile_image else ""
            if current_name and current_name != default_profile_path:
                try:
                    profile_obj.profile_image.delete(save=False)
                except Exception:
                    pass
            if current_name != default_profile_path:
                profile_obj.profile_image.name = default_profile_path
                update_fields.add("profile_image")
        elif profile_image_url:
            try:
                image_response = requests.get(profile_image_url, timeout=5)
                image_response.raise_for_status()
                parsed = urlparse(profile_image_url)
                basename = os.path.basename(parsed.path.rstrip("/"))
                base, _ = os.path.splitext(basename)
                file_name = f"kakao_{user.id}.jpg"
                storage = profile_obj.profile_image.field.storage
                save_path = f"images/userprofile/{file_name}"
                stored_path = storage.save(save_path, ContentFile(image_response.content))
                if profile_obj.profile_image.name != stored_path:
                    profile_obj.profile_image.name = stored_path
                    update_fields.add("profile_image")
            except requests.RequestException:
                pass

        if update_fields:
            profile_obj.save(update_fields=list(update_fields))

        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "카카오 계정으로 로그인되었습니다.")
        
        # 실명이 없으면 실명 입력 페이지로 리다이렉트
        if not profile_obj.name:
            return redirect("accounts:enter_real_name")
        
        redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_to)


@method_decorator(csrf_exempt, name='dispatch')
class KakaoMobileLoginView(View):
    """
    모바일 앱을 위한 카카오 로그인 API
    모바일 앱에서 카카오 SDK로 받은 access_token을 서버로 전송하여 로그인 처리
    
    POST /api/accounts/kakao/mobile/
    Body: {
        "access_token": "카카오에서 받은 access_token"
    }
    
    Response: {
        "success": true,
        "user": {
            "id": 1,
            "email": "user@example.com",
            "activity_name": "사용자명",
            "profile_image_url": "프로필 이미지 URL"
        },
        "session_id": "세션 ID (쿠키로도 전달됨)",
        "requires_real_name": true/false  // 실명 입력 필요 여부
    }
    """
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # JSON 요청 본문 파싱
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            
            access_token = data.get('access_token')
            
            if not access_token:
                return JsonResponse({
                    'success': False,
                    'error': 'access_token이 필요합니다.'
                }, status=400)
            
            # 카카오 API로 사용자 정보 조회
            try:
                user_info_response = requests.get(
                    "https://kapi.kakao.com/v2/user/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=5,
                )
                user_info_response.raise_for_status()
                user_info = user_info_response.json()
            except requests.RequestException as e:
                logger.error(f"카카오 사용자 정보 조회 실패: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': '카카오 사용자 정보를 가져오는 데 실패했습니다.'
                }, status=400)
            
            # 사용자 정보 파싱 (기존 KakaoCallbackView와 동일한 로직)
            kakao_account = user_info.get("kakao_account", {})
            email = kakao_account.get("email")
            legal_name = kakao_account.get("legal_name")
            account_name = kakao_account.get("name")
            profile = kakao_account.get("profile", {})
            nickname = profile.get("nickname")
            profile_image_url = profile.get("profile_image_url")
            is_default_image = profile.get("is_default_image", True)
            gender = kakao_account.get("gender")
            age_range = kakao_account.get("age_range")
            birthday = kakao_account.get("birthday")
            birthyear = kakao_account.get("birthyear")
            phone_number = kakao_account.get("phone_number")
            
            if not email:
                return JsonResponse({
                    'success': False,
                    'error': '카카오 계정에서 이메일 정보를 제공하지 않았습니다.'
                }, status=400)
            
            # 사용자 생성 또는 조회
            defaults = {
                "activity_name": nickname or email.split("@")[0],
                "auth_provider": "kakao"
            }
            user, created = User.objects.get_or_create(email=email, defaults=defaults)
            if created:
                user.set_unusable_password()
                user.save()
            else:
                update_fields = []
                if not user.auth_provider:
                    user.auth_provider = "kakao"
                    update_fields.append("auth_provider")
                if nickname and user.activity_name != nickname:
                    user.activity_name = nickname
                    update_fields.append("activity_name")
                if update_fields:
                    user.save(update_fields=update_fields)
            
            # 프로필 처리
            profile_defaults = {}
            if gender:
                gender_map = {
                    "male": UserProfile.Gender.MALE,
                    "female": UserProfile.Gender.FEMALE,
                }
                profile_defaults["gender"] = gender_map.get(gender, UserProfile.Gender.OTHER)
            
            if age_range:
                profile_defaults["age_range"] = age_range
            if birthyear and birthyear.isdigit():
                profile_defaults["birth_year"] = int(birthyear)
            if birthday and len(birthday) == 4:
                try:
                    birth_month = int(birthday[:2])
                    birth_day = int(birthday[2:])
                    birth_year_value = int(birthyear) if birthyear and birthyear.isdigit() else 1900
                    profile_defaults["birthday"] = datetime.date(birth_year_value, birth_month, birth_day)
                except ValueError:
                    pass
            if phone_number:
                profile_defaults["phone_number"] = phone_number
            
            profile_obj, created_profile = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)
            
            update_fields = set()
            if not created_profile:
                for field, value in profile_defaults.items():
                    if value and getattr(profile_obj, field) != value:
                        setattr(profile_obj, field, value)
                        update_fields.add(field)
            
            # 프로필 이미지 처리
            default_profile_path = "images/userprofile/user.png"
            if not is_default_image and profile_image_url:
                try:
                    image_response = requests.get(profile_image_url, timeout=5)
                    image_response.raise_for_status()
                    file_name = f"kakao_{user.id}.jpg"
                    storage = profile_obj.profile_image.field.storage
                    save_path = f"images/userprofile/{file_name}"
                    stored_path = storage.save(save_path, ContentFile(image_response.content))
                    if profile_obj.profile_image.name != stored_path:
                        profile_obj.profile_image.name = stored_path
                        update_fields.add("profile_image")
                except requests.RequestException:
                    pass
            
            if update_fields:
                profile_obj.save(update_fields=list(update_fields))
            
            # 로그인 처리
            auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            
            # 응답 데이터 구성
            response_data = {
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'activity_name': user.activity_name,
                    'profile_image_url': request.build_absolute_uri(profile_obj.profile_image.url) if profile_obj.profile_image else None,
                },
                'session_id': request.session.session_key,
                'requires_real_name': not bool(profile_obj.name),
            }
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': '잘못된 JSON 형식입니다.'
            }, status=400)
        except Exception as e:
            logger.error(f"모바일 카카오 로그인 오류: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'로그인 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=500)


class NaverLoginView(View):
    def get(self, request):
        try:
            client_id = settings.NAVER_CLIENT_ID
            redirect_uri = settings.NAVER_REDIRECT_URI

            if not client_id:
                messages.error(request, "네이버 로그인 설정이 올바르지 않습니다. 관리자에게 문의하세요.")
                return redirect("accounts:login")

            if not redirect_uri:
                messages.error(request, "네이버 리다이렉트 URI가 설정되지 않았습니다. 관리자에게 문의하세요.")
                return redirect("accounts:login")

            state = uuid.uuid4().hex
            request.session["naver_oauth_state"] = state
            request.session.save()

            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"네이버 로그인 시작 - state: {state}, session_key: {request.session.session_key}")

            from urllib.parse import urlencode
            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'state': state
            }
            naver_authorize_url = f"https://nid.naver.com/oauth2.0/authorize?{urlencode(params)}"
            
            # 모바일 환경 감지 및 네이버 앱 전환 지원
            user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
            is_mobile = 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent or 'ipad' in user_agent
            
            if is_mobile:
                # 모바일에서는 네이버 앱으로 전환될 수 있도록 처리
                # 네이버 앱이 설치되어 있으면 자동으로 앱으로 전환됨
                pass
            
            return redirect(naver_authorize_url)
        except Exception as e:
            import traceback
            print(f"네이버 로그인 오류: {e}")
            print(traceback.format_exc())
            messages.error(request, f"네이버 로그인 중 오류가 발생했습니다: {str(e)}")
            return redirect("accounts:login")


class NaverCallbackView(View):
    def get(self, request):
        state = request.GET.get("state")
        code = request.GET.get("code")
        error = request.GET.get("error")
        error_description = request.GET.get("error_description")

        session_state = request.session.pop("naver_oauth_state", None)

        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"네이버 콜백 - state: {state}, code: {code}, error: {error}, session_state: {session_state}")

        if error:
            logger.error(f"네이버 콜백 에러: {error} - {error_description}")
            messages.error(request, f"네이버 로그인에 실패했습니다: {error_description or error}")
            return redirect("accounts:login")

        if not code:
            logger.error("네이버 콜백: code가 없음")
            messages.error(request, "네이버 로그인에 실패했습니다. 인증 코드를 받지 못했습니다.")
            return redirect("accounts:login")

        if session_state != state:
            logger.error(f"네이버 콜백: state 불일치 - session_state: {session_state}, state: {state}")
            logger.error(f"네이버 콜백: request.get_host()={request.get_host()}, request.META.get('HTTP_HOST')={request.META.get('HTTP_HOST')}")
            logger.error(f"네이버 콜백: request.META.get('HTTP_X_FORWARDED_HOST')={request.META.get('HTTP_X_FORWARDED_HOST')}")
            logger.error(f"네이버 콜백: 세션 키={request.session.session_key}, 세션 전체={dict(request.session)}")
            # 세션 쿠키 정보 로깅
            if hasattr(request, 'COOKIES'):
                logger.error(f"네이버 콜백: 쿠키={dict(request.COOKIES)}")
            
            # 세션이 없을 경우: 네이버 콜백이 Nginx를 거치지 않고 직접 들어온 경우
            if session_state is None and state:
                logger.error("네이버 콜백: 세션이 없음 - 네이버 개발자 콘솔의 Redirect URI가 올바르게 설정되어야 함")
                messages.error(request, "네이버 로그인에 실패했습니다. 세션이 만료되었습니다. 네이버 개발자 콘솔의 Redirect URI를 확인해주세요.")
            else:
                messages.error(request, "네이버 로그인에 실패했습니다. 세션이 만료되었거나 보안 검증에 실패했습니다.")
            return redirect("accounts:login")

        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.NAVER_CLIENT_ID,
            "client_secret": settings.NAVER_CLIENT_SECRET,
            "code": code,
            "state": state
        }

        try:
            logger.error(f"네이버 토큰 요청 - redirect_uri: {settings.NAVER_REDIRECT_URI}")
            token_response = requests.post(
                "https://nid.naver.com/oauth2.0/token", data=token_data, timeout=5
            )
            logger.error(f"네이버 토큰 응답 상태: {token_response.status_code}")
            token_response.raise_for_status()
            token_json = token_response.json()
            logger.error(f"네이버 토큰 응답: {token_json}")
        except requests.RequestException as e:
            logger.error(f"네이버 토큰 요청 실패: {str(e)}, 응답: {token_response.text if 'token_response' in locals() else 'N/A'}")
            messages.error(request, "네이버 로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            return redirect("accounts:login")

        access_token = token_json.get("access_token")
        if not access_token:
            messages.error(request, "네이버 인증 토큰을 가져오지 못했습니다.")
            return redirect("accounts:login")

        try:
            user_info_response = requests.get(
                "https://openapi.naver.com/v1/nid/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.RequestException:
            messages.error(request, "네이버 사용자 정보를 가져오는 데 실패했습니다.")
            return redirect("accounts:login")

        response = user_info.get("response", {})
        email = response.get("email")
        name = response.get("name")
        nickname = response.get("nickname")
        profile_image = response.get("profile_image")
        gender = response.get("gender")  # M or F
        birthday = response.get("birthday")  # MM-DD
        birthyear = response.get("birthyear")  # YYYY
        mobile = response.get("mobile")

        if not email:
            messages.error(request, "네이버 계정에서 이메일 정보를 제공하지 않았습니다. 네이버 설정을 확인해주세요.")
            return redirect("accounts:login")

        defaults = {
            "activity_name": nickname or name or email.split("@")[0],
            "auth_provider": "naver"
        }
        user, created = User.objects.get_or_create(email=email, defaults=defaults)
        if created:
            user.set_unusable_password()
            user.save()
        else:
            update_fields = []
            if not user.auth_provider:
                user.auth_provider = "naver"
                update_fields.append("auth_provider")
            if nickname and user.activity_name != nickname:
                user.activity_name = nickname
                update_fields.append("activity_name")
            if update_fields:
                user.save(update_fields=update_fields)

        profile_defaults = {}
        # 소셜 로그인에서 받은 이름은 실명으로 인정하지 않음
        # 사용자가 직접 실명을 입력하도록 실명 입력 화면을 항상 보여줌
        # 따라서 name 필드는 저장하지 않음

        if gender:
            gender_map = {
                "M": UserProfile.Gender.MALE,
                "F": UserProfile.Gender.FEMALE,
            }
            profile_defaults["gender"] = gender_map.get(gender, UserProfile.Gender.OTHER)

        if birthyear and birthyear.isdigit():
            profile_defaults["birth_year"] = int(birthyear)
        if birthday and birthyear:
            try:
                birth_month = int(birthday.split("-")[0])
                birth_day = int(birthday.split("-")[1])
                birth_year_value = int(birthyear) if birthyear.isdigit() else 1900
                profile_defaults["birthday"] = datetime.date(birth_year_value, birth_month, birth_day)
            except (ValueError, IndexError):
                pass
        if mobile:
            profile_defaults["phone_number"] = mobile

        profile_obj, created_profile = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)

        update_fields = set()
        if not created_profile:
            for field, value in profile_defaults.items():
                if value and getattr(profile_obj, field) != value:
                    setattr(profile_obj, field, value)
                    update_fields.add(field)

        default_profile_path = "images/userprofile/user.png"

        if profile_image:
            try:
                image_response = requests.get(profile_image, timeout=5)
                image_response.raise_for_status()
                file_name = f"naver_{user.id}.jpg"
                storage = profile_obj.profile_image.field.storage
                save_path = f"images/userprofile/{file_name}"
                stored_path = storage.save(save_path, ContentFile(image_response.content))
                if profile_obj.profile_image.name != stored_path:
                    profile_obj.profile_image.name = stored_path
                    update_fields.add("profile_image")
            except requests.RequestException:
                pass

        if update_fields:
            profile_obj.save(update_fields=list(update_fields))

        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "네이버 계정으로 로그인되었습니다.")
        
        # 실명이 없으면 실명 입력 페이지로 리다이렉트
        if not profile_obj.name:
            return redirect("accounts:enter_real_name")
        
        redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_to)


@method_decorator(csrf_exempt, name='dispatch')
class NaverMobileLoginView(View):
    """
    모바일 앱을 위한 네이버 로그인 API
    모바일 앱에서 네이버 SDK로 받은 access_token을 서버로 전송하여 로그인 처리
    
    POST /api/accounts/naver/mobile/
    Body: {
        "access_token": "네이버에서 받은 access_token"
    }
    
    Response: {
        "success": true,
        "user": {
            "id": 1,
            "email": "user@example.com",
            "activity_name": "사용자명",
            "profile_image_url": "프로필 이미지 URL"
        },
        "session_id": "세션 ID (쿠키로도 전달됨)",
        "requires_real_name": true/false  // 실명 입력 필요 여부
    }
    """
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # JSON 요청 본문 파싱
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            
            access_token = data.get('access_token')
            
            if not access_token:
                return JsonResponse({
                    'success': False,
                    'error': 'access_token이 필요합니다.'
                }, status=400)
            
            # 네이버 API로 사용자 정보 조회
            try:
                user_info_response = requests.get(
                    "https://openapi.naver.com/v1/nid/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=5,
                )
                user_info_response.raise_for_status()
                user_info = user_info_response.json()
            except requests.RequestException as e:
                logger.error(f"네이버 사용자 정보 조회 실패: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': '네이버 사용자 정보를 가져오는 데 실패했습니다.'
                }, status=400)
            
            # 사용자 정보 파싱 (기존 NaverCallbackView와 동일한 로직)
            response = user_info.get("response", {})
            email = response.get("email")
            name = response.get("name")
            nickname = response.get("nickname")
            profile_image = response.get("profile_image")
            gender = response.get("gender")  # M or F
            birthday = response.get("birthday")  # MM-DD
            birthyear = response.get("birthyear")  # YYYY
            mobile = response.get("mobile")
            
            if not email:
                return JsonResponse({
                    'success': False,
                    'error': '네이버 계정에서 이메일 정보를 제공하지 않았습니다.'
                }, status=400)
            
            # 사용자 생성 또는 조회
            defaults = {
                "activity_name": nickname or name or email.split("@")[0],
                "auth_provider": "naver"
            }
            user, created = User.objects.get_or_create(email=email, defaults=defaults)
            if created:
                user.set_unusable_password()
                user.save()
            else:
                update_fields = []
                if not user.auth_provider:
                    user.auth_provider = "naver"
                    update_fields.append("auth_provider")
                if nickname and user.activity_name != nickname:
                    user.activity_name = nickname
                    update_fields.append("activity_name")
                if update_fields:
                    user.save(update_fields=update_fields)
            
            # 프로필 처리
            profile_defaults = {}
            if gender:
                gender_map = {
                    "M": UserProfile.Gender.MALE,
                    "F": UserProfile.Gender.FEMALE,
                }
                profile_defaults["gender"] = gender_map.get(gender, UserProfile.Gender.OTHER)
            
            if birthyear and birthyear.isdigit():
                profile_defaults["birth_year"] = int(birthyear)
            if birthday and birthyear:
                try:
                    birth_month = int(birthday.split("-")[0])
                    birth_day = int(birthday.split("-")[1])
                    birth_year_value = int(birthyear) if birthyear.isdigit() else 1900
                    profile_defaults["birthday"] = datetime.date(birth_year_value, birth_month, birth_day)
                except (ValueError, IndexError):
                    pass
            if mobile:
                profile_defaults["phone_number"] = mobile
            
            profile_obj, created_profile = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)
            
            update_fields = set()
            if not created_profile:
                for field, value in profile_defaults.items():
                    if value and getattr(profile_obj, field) != value:
                        setattr(profile_obj, field, value)
                        update_fields.add(field)
            
            # 프로필 이미지 처리
            default_profile_path = "images/userprofile/user.png"
            if profile_image:
                try:
                    image_response = requests.get(profile_image, timeout=5)
                    image_response.raise_for_status()
                    file_name = f"naver_{user.id}.jpg"
                    storage = profile_obj.profile_image.field.storage
                    save_path = f"images/userprofile/{file_name}"
                    stored_path = storage.save(save_path, ContentFile(image_response.content))
                    if profile_obj.profile_image.name != stored_path:
                        profile_obj.profile_image.name = stored_path
                        update_fields.add("profile_image")
                except requests.RequestException:
                    pass
            
            if update_fields:
                profile_obj.save(update_fields=list(update_fields))
            
            # 로그인 처리
            auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            
            # 응답 데이터 구성
            response_data = {
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'activity_name': user.activity_name,
                    'profile_image_url': request.build_absolute_uri(profile_obj.profile_image.url) if profile_obj.profile_image else None,
                },
                'session_id': request.session.session_key,
                'requires_real_name': not bool(profile_obj.name),
            }
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': '잘못된 JSON 형식입니다.'
            }, status=400)
        except Exception as e:
            logger.error(f"모바일 네이버 로그인 오류: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'로그인 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=500)


class GoogleLoginView(View):
    def get(self, request):
        try:
            client_id = settings.GOOGLE_CLIENT_ID
            redirect_uri = settings.GOOGLE_REDIRECT_URI

            if not client_id:
                messages.error(request, "구글 로그인 설정이 올바르지 않습니다. 관리자에게 문의하세요.")
                return redirect("accounts:login")

            if not redirect_uri:
                messages.error(request, "구글 리다이렉트 URI가 설정되지 않았습니다. 관리자에게 문의하세요.")
                return redirect("accounts:login")

            state = uuid.uuid4().hex
            request.session["google_oauth_state"] = state
            request.session.save()

            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"구글 로그인 시작 - state: {state}, session_key: {request.session.session_key}")

            from urllib.parse import urlencode
            params = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': 'openid email profile',
                'state': state,
                'access_type': 'offline',
                'prompt': 'consent'
            }
            google_authorize_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            return redirect(google_authorize_url)
        except Exception as e:
            import traceback
            print(f"구글 로그인 오류: {e}")
            print(traceback.format_exc())
            messages.error(request, f"구글 로그인 중 오류가 발생했습니다: {str(e)}")
            return redirect("accounts:login")


class GoogleCallbackView(View):
    def get(self, request):
        state = request.GET.get("state")
        code = request.GET.get("code")
        error = request.GET.get("error")

        session_state = request.session.pop("google_oauth_state", None)

        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"구글 콜백 - state: {state}, code: {code}, error: {error}, session_state: {session_state}")

        if error:
            logger.error(f"구글 콜백 에러: {error}")
            messages.error(request, f"구글 로그인에 실패했습니다: {error}")
            return redirect("accounts:login")

        if not code:
            logger.error("구글 콜백: code가 없음")
            messages.error(request, "구글 로그인에 실패했습니다. 인증 코드를 받지 못했습니다.")
            return redirect("accounts:login")

        if session_state != state:
            logger.error(f"구글 콜백: state 불일치 - session_state: {session_state}, state: {state}")
            logger.error(f"구글 콜백: request.get_host()={request.get_host()}, request.META.get('HTTP_HOST')={request.META.get('HTTP_HOST')}")
            logger.error(f"구글 콜백: request.META.get('HTTP_X_FORWARDED_HOST')={request.META.get('HTTP_X_FORWARDED_HOST')}")
            logger.error(f"구글 콜백: 세션 키={request.session.session_key}, 세션 전체={dict(request.session)}")
            # 세션 쿠키 정보 로깅
            if hasattr(request, 'COOKIES'):
                logger.error(f"구글 콜백: 쿠키={dict(request.COOKIES)}")
            
            # 세션이 없을 경우: 구글 콜백이 Nginx를 거치지 않고 직접 들어온 경우
            if session_state is None and state:
                logger.error("구글 콜백: 세션이 없음 - 구글 클라우드 콘솔의 Redirect URI가 올바르게 설정되어야 함")
                messages.error(request, "구글 로그인에 실패했습니다. 세션이 만료되었습니다. 구글 클라우드 콘솔의 Redirect URI를 확인해주세요.")
            else:
                messages.error(request, "구글 로그인에 실패했습니다. 세션이 만료되었거나 보안 검증에 실패했습니다.")
            return redirect("accounts:login")

        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        try:
            logger.error(f"구글 토큰 요청 - redirect_uri: {settings.GOOGLE_REDIRECT_URI}")
            token_response = requests.post(
                "https://oauth2.googleapis.com/token", data=token_data, timeout=5
            )
            logger.error(f"구글 토큰 응답 상태: {token_response.status_code}")
            token_response.raise_for_status()
            token_json = token_response.json()
            logger.error(f"구글 토큰 응답: {token_json}")
        except requests.RequestException as e:
            logger.error(f"구글 토큰 요청 실패: {str(e)}, 응답: {token_response.text if 'token_response' in locals() else 'N/A'}")
            messages.error(request, "구글 로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            return redirect("accounts:login")

        access_token = token_json.get("access_token")
        id_token = token_json.get("id_token")

        if not access_token:
            messages.error(request, "구글 인증 토큰을 가져오지 못했습니다.")
            return redirect("accounts:login")

        try:
            user_info_response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
        except requests.RequestException:
            messages.error(request, "구글 사용자 정보를 가져오는 데 실패했습니다.")
            return redirect("accounts:login")

        email = user_info.get("email")
        name = user_info.get("name")
        given_name = user_info.get("given_name")
        family_name = user_info.get("family_name")
        picture = user_info.get("picture")
        verified_email = user_info.get("verified_email", False)

        if not email:
            messages.error(request, "구글 계정에서 이메일 정보를 제공하지 않았습니다.")
            return redirect("accounts:login")

        if not verified_email:
            messages.error(request, "구글 계정의 이메일이 인증되지 않았습니다.")
            return redirect("accounts:login")

        defaults = {
            "activity_name": name or email.split("@")[0],
            "auth_provider": "google"
        }
        user, created = User.objects.get_or_create(email=email, defaults=defaults)
        if created:
            user.set_unusable_password()
            user.save()
        else:
            update_fields = []
            if not user.auth_provider:
                user.auth_provider = "google"
                update_fields.append("auth_provider")
            if name and user.activity_name != name:
                user.activity_name = name
                update_fields.append("activity_name")
            if update_fields:
                user.save(update_fields=update_fields)

        profile_defaults = {}
        # 소셜 로그인에서 받은 이름은 실명으로 인정하지 않음
        # 사용자가 직접 실명을 입력하도록 실명 입력 화면을 항상 보여줌
        # 따라서 name 필드는 저장하지 않음

        profile_obj, created_profile = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)

        update_fields = set()
        if not created_profile:
            for field, value in profile_defaults.items():
                if value and getattr(profile_obj, field) != value:
                    setattr(profile_obj, field, value)
                    update_fields.add(field)

        if picture:
            try:
                image_response = requests.get(picture, timeout=5)
                image_response.raise_for_status()
                file_name = f"google_{user.id}.jpg"
                storage = profile_obj.profile_image.field.storage
                save_path = f"images/userprofile/{file_name}"
                stored_path = storage.save(save_path, ContentFile(image_response.content))
                if profile_obj.profile_image.name != stored_path:
                    profile_obj.profile_image.name = stored_path
                    update_fields.add("profile_image")
            except requests.RequestException:
                pass

        if update_fields:
            profile_obj.save(update_fields=list(update_fields))

        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "구글 계정으로 로그인되었습니다.")

        # 실명이 없으면 실명 입력 페이지로 리다이렉트
        if not profile_obj.name:
            return redirect("accounts:enter_real_name")

        redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_to)


@method_decorator(csrf_exempt, name="dispatch")
class GoogleMobileLoginView(View):
    """
    모바일 앱을 위한 구글 로그인 API
    모바일 앱에서 구글 SDK로 받은 access_token을 서버로 전송하여 로그인 처리

    POST /accounts/api/google/mobile/
    Body: {
        "access_token": "구글에서 받은 access_token"
    }

    Response: {
        "success": true,
        "user": {
            "id": 1,
            "email": "user@example.com",
            "activity_name": "사용자명",
            "profile_image_url": "프로필 이미지 URL"
        },
        "session_id": "세션 ID (쿠키로도 전달됨)",
        "requires_real_name": true/false  # 실명 입력 필요 여부
    }
    """

    def post(self, request):
        import logging

        logger = logging.getLogger(__name__)

        try:
            # JSON 요청 본문 파싱
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = request.POST

            access_token = data.get("access_token")

            if not access_token:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "access_token이 필요합니다.",
                    },
                    status=400,
                )

            # 구글 API로 사용자 정보 조회
            try:
                user_info_response = requests.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=5,
                )
                user_info_response.raise_for_status()
                user_info = user_info_response.json()
            except requests.RequestException as e:
                logger.error(f"구글 사용자 정보 조회 실패: {str(e)}")
                return JsonResponse(
                    {
                        "success": False,
                        "error": "구글 사용자 정보를 가져오는 데 실패했습니다.",
                    },
                    status=400,
                )

            # 사용자 정보 파싱 (기존 GoogleCallbackView와 유사한 로직)
            email = user_info.get("email")
            name = user_info.get("name")
            picture = user_info.get("picture")
            verified_email = user_info.get("verified_email", False)

            if not email:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "구글 계정에서 이메일 정보를 제공하지 않았습니다.",
                    },
                    status=400,
                )

            if not verified_email:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "구글 계정의 이메일이 인증되지 않았습니다.",
                    },
                    status=400,
                )

            # 사용자 생성 또는 조회
            defaults = {
                "activity_name": name or email.split("@")[0],
                "auth_provider": "google",
            }
            user, created = User.objects.get_or_create(email=email, defaults=defaults)
            if created:
                user.set_unusable_password()
                user.save()
            else:
                update_fields = []
                if not user.auth_provider:
                    user.auth_provider = "google"
                    update_fields.append("auth_provider")
                if name and user.activity_name != name:
                    user.activity_name = name
                    update_fields.append("activity_name")
                if update_fields:
                    user.save(update_fields=update_fields)

            # 프로필 처리
            profile_defaults = {}
            profile_obj, created_profile = UserProfile.objects.get_or_create(
                user=user, defaults=profile_defaults
            )

            update_fields = set()
            if not created_profile:
                for field, value in profile_defaults.items():
                    if value and getattr(profile_obj, field) != value:
                        setattr(profile_obj, field, value)
                        update_fields.add(field)

            if picture:
                try:
                    image_response = requests.get(picture, timeout=5)
                    image_response.raise_for_status()
                    file_name = f"google_{user.id}.jpg"
                    storage = profile_obj.profile_image.field.storage
                    save_path = f"images/userprofile/{file_name}"
                    stored_path = storage.save(save_path, ContentFile(image_response.content))
                    if profile_obj.profile_image.name != stored_path:
                        profile_obj.profile_image.name = stored_path
                        update_fields.add("profile_image")
                except requests.RequestException:
                    pass

            if update_fields:
                profile_obj.save(update_fields=list(update_fields))

            # 로그인 처리
            auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            response_data = {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "activity_name": user.activity_name,
                    "profile_image_url": request.build_absolute_uri(
                        profile_obj.profile_image.url
                    )
                    if profile_obj.profile_image
                    else None,
                },
                "session_id": request.session.session_key,
                "requires_real_name": not bool(profile_obj.name),
            }

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "success": False,
                    "error": "잘못된 JSON 형식입니다.",
                },
                status=400,
            )
        except Exception as e:
            logger.error(f"모바일 구글 로그인 오류: {str(e)}", exc_info=True)
            return JsonResponse(
                {
                    "success": False,
                    "error": f"로그인 처리 중 오류가 발생했습니다: {str(e)}",
                },
                status=500,
            )


# 설정 및 기타 페이지 뷰들
@login_required
def notification_settings(request):
    """알림 설정 (준비중)"""
    return render(request, "accounts/notification_settings.html")


def privacy_policy(request):
    """개인정보 처리방침 (비회원도 접근 가능)"""
    return render(request, "accounts/privacy_policy.html")


def terms_of_service(request):
    """이용약관 (비회원도 접근 가능)"""
    return render(request, "accounts/terms_of_service.html")


@login_required
def inquiry_create(request):
    """문의하기"""
    if request.method == "POST":
        form = InquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.user = request.user
            inquiry.save()
            messages.success(request, "문의가 접수되었습니다. 빠른 시일 내에 답변드리겠습니다.")
            return redirect("accounts:inquiry_list")
    else:
        form = InquiryForm()
    
    return render(request, "accounts/inquiry_create.html", {
        "form": form,
    })


@login_required
def inquiry_list(request):
    """문의 내역"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    inquiries = Inquiry.objects.filter(user=user).order_by("-created_at")
    paginator = Paginator(inquiries, per_page)
    inquiries_page = paginator.get_page(page)
    
    return render(request, "accounts/inquiry_list.html", {
        "inquiries_page": inquiries_page,
    })


@login_required
def blocked_users(request):
    """차단한 사용자 목록"""
    user = request.user
    
    # 차단 해제 처리
    if request.method == "POST" and "block_id" in request.POST:
        try:
            block_id = int(request.POST.get("block_id"))
            block = UserBlock.objects.get(id=block_id, blocker=user)
            block.delete()
            messages.success(request, "차단이 해제되었습니다.")
            return redirect("accounts:blocked_users")
        except (ValueError, UserBlock.DoesNotExist):
            messages.error(request, "차단 해제에 실패했습니다.")
    
    per_page = 20
    page = request.GET.get('page', 1)
    
    blocked_users_list = UserBlock.objects.filter(blocker=user).select_related('blocked').order_by("-created_at")
    paginator = Paginator(blocked_users_list, per_page)
    blocked_page = paginator.get_page(page)
    
    return render(request, "accounts/blocked_users.html", {
        "blocked_page": blocked_page,
    })


@login_required
def report_list(request):
    """신고 내역"""
    user = request.user
    per_page = 20
    page = request.GET.get('page', 1)
    
    reports = Report.objects.filter(reporter=user).order_by("-created_at")
    paginator = Paginator(reports, per_page)
    reports_page = paginator.get_page(page)
    
    return render(request, "accounts/report_list.html", {
        "reports_page": reports_page,
    })


@login_required
def password_change(request):
    """비밀번호 변경"""
    if request.method == "POST":
        form = PasswordChangeFormCustom(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "비밀번호가 성공적으로 변경되었습니다.")
            return redirect("accounts:profile_edit")
    else:
        form = PasswordChangeFormCustom(request.user)
    
    return render(request, "accounts/password_change.html", {
        "form": form,
    })


@login_required
def enter_real_name(request):
    """실명 입력 페이지 (소셜 로그인 후)"""
    user = request.user
    
    # 이미 실명이 있으면 마이페이지로 리다이렉트
    try:
        profile = user.profile
        if profile.name:
            messages.info(request, "이미 실명이 등록되어 있습니다.")
            return redirect("accounts:mypage")
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    if request.method == "POST":
        form = RealNameForm(request.POST, user=user)
        if form.is_valid():
            # 실명과 급수 저장
            profile.name = form.cleaned_data["name"]
            profile.badminton_level = form.cleaned_data["badminton_level"]
            profile.save()
            
            # 활동명 저장
            if form.cleaned_data.get("activity_name"):
                user.activity_name = form.cleaned_data["activity_name"]
                user.save()
            
            messages.success(request, "실명이 등록되었습니다.")
            redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
            return redirect(redirect_to)
    else:
        form = RealNameForm(user=user)
    
    return render(request, "accounts/enter_real_name.html", {
        "form": form,
    })


@login_required
def account_delete(request):
    """계정 탈퇴"""
    if request.method == "POST":
        user = request.user
        user.is_active = False
        user.save()
        messages.success(request, "계정이 탈퇴 처리되었습니다.")
        from django.contrib.auth import logout
        logout(request)
        return redirect("home")

    return render(request, "accounts/account_delete.html")


@method_decorator(csrf_exempt, name="dispatch")
class ProfileAPIView(View):
    """
    프로필 REST API
    GET: 프로필 조회
    PUT: 프로필 수정
    """

    def get(self, request):
        """프로필 조회"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        # 프로필 이미지 URL 생성
        profile_image_url = None
        if profile.profile_image:
            profile_image_url = request.build_absolute_uri(profile.profile_image.url)

        return JsonResponse({
            "success": True,
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "activity_name": user.activity_name,
                    "auth_provider": user.auth_provider or "",
                    "is_social_auth": user.is_social_auth,
                    "date_joined": user.date_joined.isoformat(),
                },
                "profile": {
                    "name": profile.name,
                    "profile_image_url": profile_image_url,
                    "badminton_level": profile.badminton_level,
                    "badminton_level_display": profile.get_badminton_level_display() if profile.badminton_level else "",
                    "gender": profile.gender,
                    "gender_display": profile.get_gender_display(),
                    "age_range": profile.age_range,
                    "birthday": profile.birthday.isoformat() if profile.birthday else None,
                    "birth_year": profile.birth_year,
                    "phone_number": profile.phone_number,
                    "shipping_receiver": profile.shipping_receiver,
                    "shipping_phone_number": profile.shipping_phone_number,
                    "shipping_address": profile.shipping_address,
                    "created_at": profile.created_at.isoformat(),
                    "updated_at": profile.updated_at.isoformat(),
                }
            }
        })

    def put(self, request):
        """프로필 수정"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        # JSON 또는 multipart/form-data 처리
        content_type = request.content_type or ""
        if "application/json" in content_type:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse(
                    {"success": False, "error": "잘못된 JSON 형식입니다"},
                    status=400
                )
        else:
            data = request.POST.dict()

        # User 모델 필드 업데이트
        user_updated = False
        if "activity_name" in data and data["activity_name"]:
            user.activity_name = data["activity_name"]
            user_updated = True

        if user_updated:
            user.save()

        # Profile 모델 필드 업데이트
        profile_fields = [
            "name", "badminton_level", "gender", "age_range",
            "phone_number", "shipping_receiver", "shipping_phone_number", "shipping_address"
        ]

        update_fields = []
        for field in profile_fields:
            if field in data:
                setattr(profile, field, data[field])
                update_fields.append(field)

        # 날짜 필드 처리
        if "birthday" in data:
            if data["birthday"]:
                try:
                    profile.birthday = datetime.datetime.strptime(data["birthday"], "%Y-%m-%d").date()
                    update_fields.append("birthday")
                except ValueError:
                    return JsonResponse(
                        {"success": False, "error": "생일 형식이 올바르지 않습니다 (YYYY-MM-DD)"},
                        status=400
                    )
            else:
                profile.birthday = None
                update_fields.append("birthday")

        if "birth_year" in data:
            if data["birth_year"]:
                try:
                    profile.birth_year = int(data["birth_year"])
                    update_fields.append("birth_year")
                except (ValueError, TypeError):
                    return JsonResponse(
                        {"success": False, "error": "출생연도는 숫자여야 합니다"},
                        status=400
                    )
            else:
                profile.birth_year = None
                update_fields.append("birth_year")

        # 프로필 이미지 처리 (multipart/form-data인 경우)
        if request.FILES.get("profile_image"):
            profile.profile_image = request.FILES["profile_image"]
            update_fields.append("profile_image")

        if update_fields:
            profile.save(update_fields=update_fields + ["updated_at"])

        # 업데이트된 프로필 반환
        profile_image_url = None
        if profile.profile_image:
            profile_image_url = request.build_absolute_uri(profile.profile_image.url)

        return JsonResponse({
            "success": True,
            "message": "프로필이 수정되었습니다",
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "activity_name": user.activity_name,
                },
                "profile": {
                    "name": profile.name,
                    "profile_image_url": profile_image_url,
                    "badminton_level": profile.badminton_level,
                    "badminton_level_display": profile.get_badminton_level_display() if profile.badminton_level else "",
                    "gender": profile.gender,
                    "gender_display": profile.get_gender_display(),
                    "age_range": profile.age_range,
                    "birthday": profile.birthday.isoformat() if profile.birthday else None,
                    "birth_year": profile.birth_year,
                    "phone_number": profile.phone_number,
                    "shipping_receiver": profile.shipping_receiver,
                    "shipping_phone_number": profile.shipping_phone_number,
                    "shipping_address": profile.shipping_address,
                    "updated_at": profile.updated_at.isoformat(),
                }
            }
        })


@method_decorator(csrf_exempt, name="dispatch")
class UserBlockAPIView(View):
    """
    사용자 차단 REST API
    GET: 차단 목록 조회
    POST: 사용자 차단
    DELETE: 차단 해제
    """

    def get(self, request):
        """차단 목록 조회"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        blocks = UserBlock.objects.filter(blocker=request.user).select_related("blocked", "blocked__profile")
        block_list = []
        for block in blocks:
            blocked_user = block.blocked
            profile_image_url = None
            if hasattr(blocked_user, 'profile') and blocked_user.profile.profile_image:
                profile_image_url = request.build_absolute_uri(blocked_user.profile.profile_image.url)

            block_list.append({
                "id": block.id,
                "blocked_user": {
                    "id": blocked_user.id,
                    "activity_name": blocked_user.activity_name,
                    "profile_image_url": profile_image_url,
                },
                "created_at": block.created_at.isoformat(),
            })

        return JsonResponse({
            "success": True,
            "data": block_list
        })

    def post(self, request):
        """사용자 차단"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "잘못된 JSON 형식입니다"},
                status=400
            )

        user_id = data.get("user_id")
        if not user_id:
            return JsonResponse(
                {"success": False, "error": "user_id가 필요합니다"},
                status=400
            )

        if user_id == request.user.id:
            return JsonResponse(
                {"success": False, "error": "자기 자신을 차단할 수 없습니다"},
                status=400
            )

        try:
            blocked_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "사용자를 찾을 수 없습니다"},
                status=404
            )

        block, created = UserBlock.objects.get_or_create(
            blocker=request.user,
            blocked=blocked_user
        )

        if not created:
            return JsonResponse(
                {"success": False, "error": "이미 차단한 사용자입니다"},
                status=400
            )

        return JsonResponse({
            "success": True,
            "message": f"{blocked_user.activity_name}님을 차단했습니다",
            "data": {
                "id": block.id,
                "blocked_user_id": blocked_user.id,
                "created_at": block.created_at.isoformat(),
            }
        }, status=201)

    def delete(self, request):
        """차단 해제"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "잘못된 JSON 형식입니다"},
                status=400
            )

        user_id = data.get("user_id")
        if not user_id:
            return JsonResponse(
                {"success": False, "error": "user_id가 필요합니다"},
                status=400
            )

        try:
            block = UserBlock.objects.get(blocker=request.user, blocked_id=user_id)
            blocked_name = block.blocked.activity_name
            block.delete()
            return JsonResponse({
                "success": True,
                "message": f"{blocked_name}님의 차단을 해제했습니다"
            })
        except UserBlock.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "차단 정보를 찾을 수 없습니다"},
                status=404
            )


@method_decorator(csrf_exempt, name="dispatch")
class ReportAPIView(View):
    """
    신고 REST API
    GET: 내 신고 목록 조회
    POST: 신고 생성
    """

    def get(self, request):
        """내 신고 목록 조회"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        reports = Report.objects.filter(reporter=request.user).order_by("-created_at")
        report_list = []
        for report in reports:
            report_list.append({
                "id": report.id,
                "report_type": report.report_type,
                "report_type_display": report.get_report_type_display(),
                "target_id": report.target_id,
                "reason": report.reason,
                "status": report.status,
                "status_display": report.get_status_display(),
                "created_at": report.created_at.isoformat(),
            })

        return JsonResponse({
            "success": True,
            "data": report_list
        })

    def post(self, request):
        """신고 생성"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "잘못된 JSON 형식입니다"},
                status=400
            )

        report_type = data.get("report_type")
        target_id = data.get("target_id")
        reason = data.get("reason")

        if not all([report_type, target_id, reason]):
            return JsonResponse(
                {"success": False, "error": "report_type, target_id, reason이 필요합니다"},
                status=400
            )

        valid_types = [choice[0] for choice in Report.ReportType.choices]
        if report_type not in valid_types:
            return JsonResponse(
                {"success": False, "error": f"유효하지 않은 신고 유형입니다. 유효한 값: {valid_types}"},
                status=400
            )

        report = Report.objects.create(
            reporter=request.user,
            report_type=report_type,
            target_id=target_id,
            reason=reason
        )

        return JsonResponse({
            "success": True,
            "message": "신고가 접수되었습니다",
            "data": {
                "id": report.id,
                "report_type": report.report_type,
                "target_id": report.target_id,
                "status": report.status,
                "created_at": report.created_at.isoformat(),
            }
        }, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class InquiryAPIView(View):
    """
    문의 REST API
    GET: 내 문의 목록 조회
    POST: 문의 생성
    """

    def get(self, request):
        """내 문의 목록 조회"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        inquiry_id = request.GET.get("id")

        if inquiry_id:
            # 단일 문의 상세 조회
            try:
                inquiry = Inquiry.objects.get(id=inquiry_id, user=request.user)
                return JsonResponse({
                    "success": True,
                    "data": {
                        "id": inquiry.id,
                        "category": inquiry.category,
                        "category_display": inquiry.get_category_display(),
                        "title": inquiry.title,
                        "content": inquiry.content,
                        "status": inquiry.status,
                        "status_display": inquiry.get_status_display(),
                        "admin_response": inquiry.admin_response,
                        "created_at": inquiry.created_at.isoformat(),
                        "answered_at": inquiry.answered_at.isoformat() if inquiry.answered_at else None,
                    }
                })
            except Inquiry.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "문의를 찾을 수 없습니다"},
                    status=404
                )

        # 문의 목록 조회
        inquiries = Inquiry.objects.filter(user=request.user).order_by("-created_at")
        inquiry_list = []
        for inquiry in inquiries:
            inquiry_list.append({
                "id": inquiry.id,
                "category": inquiry.category,
                "category_display": inquiry.get_category_display(),
                "title": inquiry.title,
                "status": inquiry.status,
                "status_display": inquiry.get_status_display(),
                "created_at": inquiry.created_at.isoformat(),
                "answered_at": inquiry.answered_at.isoformat() if inquiry.answered_at else None,
            })

        return JsonResponse({
            "success": True,
            "data": inquiry_list
        })

    def post(self, request):
        """문의 생성"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "잘못된 JSON 형식입니다"},
                status=400
            )

        category = data.get("category", "general")
        title = data.get("title")
        content = data.get("content")

        if not all([title, content]):
            return JsonResponse(
                {"success": False, "error": "title과 content가 필요합니다"},
                status=400
            )

        valid_categories = [choice[0] for choice in Inquiry.Category.choices]
        if category not in valid_categories:
            return JsonResponse(
                {"success": False, "error": f"유효하지 않은 카테고리입니다. 유효한 값: {valid_categories}"},
                status=400
            )

        inquiry = Inquiry.objects.create(
            user=request.user,
            category=category,
            title=title,
            content=content
        )

        return JsonResponse({
            "success": True,
            "message": "문의가 등록되었습니다",
            "data": {
                "id": inquiry.id,
                "category": inquiry.category,
                "title": inquiry.title,
                "status": inquiry.status,
                "created_at": inquiry.created_at.isoformat(),
            }
        }, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class MypageSummaryAPIView(View):
    """
    마이페이지 요약 REST API
    GET: 마이페이지 요약 정보 조회
    """

    def get(self, request):
        """마이페이지 요약 정보"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        user = request.user

        # 프로필 정보
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        profile_image_url = None
        if profile.profile_image:
            profile_image_url = request.build_absolute_uri(profile.profile_image.url)

        # 각 섹션별 카운트
        my_bands_count = Band.objects.filter(
            members__user=user,
            members__status="active"
        ).count()
        created_bands_count = Band.objects.filter(created_by=user).count()
        bookmarked_bands_count = BandBookmark.objects.filter(user=user).count()
        band_posts_count = BandPost.objects.filter(author=user).count()
        band_comments_count = BandComment.objects.filter(author=user).count()
        liked_band_posts_count = BandPost.objects.filter(likes__user=user).distinct().count()
        schedule_applications_count = BandScheduleApplication.objects.filter(user=user).count()
        vote_choices_count = BandVoteChoice.objects.filter(user=user).count()
        community_posts_count = Post.objects.filter(author=user).count()
        liked_posts_count = Post.objects.filter(likes=user).distinct().count()
        comments_count = Comment.objects.filter(author=user).count()
        shared_posts_count = Post.objects.filter(shares__user=user).distinct().count()
        liked_contests_count = Contest.objects.filter(likes=user).distinct().count()

        return JsonResponse({
            "success": True,
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "activity_name": user.activity_name,
                    "profile_image_url": profile_image_url,
                },
                "counts": {
                    "my_bands": my_bands_count,
                    "created_bands": created_bands_count,
                    "bookmarked_bands": bookmarked_bands_count,
                    "band_posts": band_posts_count,
                    "band_comments": band_comments_count,
                    "liked_band_posts": liked_band_posts_count,
                    "schedule_applications": schedule_applications_count,
                    "vote_choices": vote_choices_count,
                    "community_posts": community_posts_count,
                    "liked_posts": liked_posts_count,
                    "comments": comments_count,
                    "shared_posts": shared_posts_count,
                    "liked_contests": liked_contests_count,
                }
            }
        })


@method_decorator(csrf_exempt, name="dispatch")
class AccountDeleteAPIView(View):
    """
    계정 삭제 REST API
    POST: 계정 비활성화 (탈퇴)
    """

    def post(self, request):
        """계정 탈퇴"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "로그인이 필요합니다"},
                status=401
            )

        user = request.user
        user.is_active = False
        user.save()

        # 세션 무효화
        from django.contrib.auth import logout
        logout(request)

        return JsonResponse({
            "success": True,
            "message": "계정이 탈퇴 처리되었습니다"
        })
