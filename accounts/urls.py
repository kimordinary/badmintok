from django.urls import path
from django.contrib.auth import views as auth_views

from .forms import UserLoginForm
from .views import (
    KakaoCallbackView, KakaoLoginView, KakaoMobileLoginView,
    NaverCallbackView, NaverLoginView,
    GoogleCallbackView, GoogleLoginView,
    SignupSuccessView, SignupView,
    mypage, profile_edit, enter_real_name,
    mypage_bands, mypage_created_bands, mypage_bookmarked_bands, mypage_band_posts, mypage_band_comments,
    mypage_liked_band_posts, mypage_schedule_applications, mypage_vote_choices,
    mypage_community_posts, mypage_liked_posts, mypage_comments, mypage_shared_posts,
    mypage_liked_contests,
    notification_settings, privacy_policy, terms_of_service,
    inquiry_create, inquiry_list, blocked_users, report_list,
    password_change, account_delete
)


app_name = "accounts"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("signup/success/", SignupSuccessView.as_view(), name="signup_success"),
    path("login/", auth_views.LoginView.as_view(authentication_form=UserLoginForm), name="login"),
    path("login/kakao/", KakaoLoginView.as_view(), name="kakao_login"),
    path("kakao/", KakaoCallbackView.as_view(), name="kakao_callback"),
    path("kakao", KakaoCallbackView.as_view(), name="kakao_callback_no_slash"),
    # 모바일 앱을 위한 카카오 로그인 API
    path("api/kakao/mobile/", KakaoMobileLoginView.as_view(), name="kakao_mobile_login"),
    path("login/naver/", NaverLoginView.as_view(), name="naver_login"),
    path("naver/", NaverCallbackView.as_view(), name="naver_callback"),
    path("naver", NaverCallbackView.as_view(), name="naver_callback_no_slash"),
    path("login/google/", GoogleLoginView.as_view(), name="google_login"),
    path("google/", GoogleCallbackView.as_view(), name="google_callback"),
    path("google", GoogleCallbackView.as_view(), name="google_callback_no_slash"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("enter-real-name/", enter_real_name, name="enter_real_name"),
    path("mypage/", mypage, name="mypage"),
    path("profile/edit/", profile_edit, name="profile_edit"),
    # 마이페이지 섹션별 상세 페이지
    path("mypage/bands/", mypage_bands, name="mypage_bands"),
    path("mypage/created-bands/", mypage_created_bands, name="mypage_created_bands"),
    path("mypage/bookmarked-bands/", mypage_bookmarked_bands, name="mypage_bookmarked_bands"),
    path("mypage/band-posts/", mypage_band_posts, name="mypage_band_posts"),
    path("mypage/band-comments/", mypage_band_comments, name="mypage_band_comments"),
    path("mypage/liked-band-posts/", mypage_liked_band_posts, name="mypage_liked_band_posts"),
    path("mypage/schedule-applications/", mypage_schedule_applications, name="mypage_schedule_applications"),
    path("mypage/vote-choices/", mypage_vote_choices, name="mypage_vote_choices"),
    path("mypage/community-posts/", mypage_community_posts, name="mypage_community_posts"),
    path("mypage/liked-posts/", mypage_liked_posts, name="mypage_liked_posts"),
    path("mypage/comments/", mypage_comments, name="mypage_comments"),
    path("mypage/shared-posts/", mypage_shared_posts, name="mypage_shared_posts"),
    path("mypage/liked-contests/", mypage_liked_contests, name="mypage_liked_contests"),
    # 설정 및 기타
    path("mypage/notifications/", notification_settings, name="notification_settings"),
    path("mypage/privacy-policy/", privacy_policy, name="privacy_policy"),
    path("mypage/terms/", terms_of_service, name="terms_of_service"),
    path("mypage/inquiry/", inquiry_create, name="inquiry_create"),
    path("mypage/inquiries/", inquiry_list, name="inquiry_list"),
    path("mypage/blocked-users/", blocked_users, name="blocked_users"),
    path("mypage/reports/", report_list, name="report_list"),
    path("mypage/password-change/", password_change, name="password_change"),
    path("mypage/account-delete/", account_delete, name="account_delete"),
]
