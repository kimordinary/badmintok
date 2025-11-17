from django.urls import path
from django.contrib.auth import views as auth_views

from .forms import UserLoginForm
from .views import KakaoCallbackView, KakaoLoginView, SignupSuccessView, SignupView


app_name = "accounts"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("signup/success/", SignupSuccessView.as_view(), name="signup_success"),
    path("login/", auth_views.LoginView.as_view(authentication_form=UserLoginForm), name="login"),
    path("login/kakao/", KakaoLoginView.as_view(), name="kakao_login"),
    path("kakao/", KakaoCallbackView.as_view(), name="kakao_callback"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
