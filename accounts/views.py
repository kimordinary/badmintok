import datetime
import os
import uuid
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.core.files.base import ContentFile
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView

from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count, Q
from django.core.paginator import Paginator

from .forms import UserSignupForm, UserProfileForm, PasswordChangeFormCustom, InquiryForm, RealNameForm
from .models import User, UserProfile, UserBlock, Report, Inquiry
from band.models import (
    Band, BandPost, BandComment, BandPostLike,
    BandScheduleApplication, BandVoteChoice
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
    
    return render(request, "accounts/mypage.html", {
        "profile": profile,
        "my_bands_count": my_bands_count,
        "created_bands_count": created_bands_count,
        "band_posts_count": band_posts_count,
        "band_comments_count": band_comments_count,
        "liked_band_posts_count": liked_band_posts_count,
        "schedule_applications_count": schedule_applications_count,
        "vote_choices_count": vote_choices_count,
        "community_posts_count": community_posts_count,
        "liked_posts_count": liked_posts_count,
        "comments_count": comments_count,
        "shared_posts_count": shared_posts_count,
        "liked_contests_count": liked_contests_count,
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
