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

from .forms import UserSignupForm
from .models import User, UserProfile


class SignupView(CreateView):
    template_name = "accounts/signup.html"
    form_class = UserSignupForm
    success_url = reverse_lazy("accounts:signup_success")


class SignupSuccessView(TemplateView):
    template_name = "accounts/signup_success.html"


class KakaoLoginView(View):
    def get(self, request):
        client_id = settings.KAKAO_CLIENT_ID
        redirect_uri = settings.KAKAO_REDIRECT_URI
        state = uuid.uuid4().hex
        request.session["kakao_oauth_state"] = state
        scope = "account_email profile_nickname"
        kakao_authorize_url = (
            "https://kauth.kakao.com/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
            f"&scope={scope}"
        )
        return redirect(kakao_authorize_url)


class KakaoCallbackView(View):
    def get(self, request):
        state = request.GET.get("state")
        code = request.GET.get("code")
        error = request.GET.get("error")

        session_state = request.session.pop("kakao_oauth_state", None)

        if not any([state, code, error]):
            return render(request, "accounts/kakao_callback.html")

        if error or not code or session_state != state:
            messages.error(request, "카카오 로그인에 실패했습니다. 다시 시도해주세요.")
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
            token_response = requests.post(
                "https://kauth.kakao.com/oauth/token", data=token_data, timeout=5
            )
            token_response.raise_for_status()
            token_json = token_response.json()
        except requests.RequestException:
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

        defaults = {"activity_name": nickname or email.split("@")[0]}
        user, created = User.objects.get_or_create(email=email, defaults=defaults)
        if created:
            user.set_unusable_password()
            user.save()
        elif nickname and user.activity_name != nickname:
            user.activity_name = nickname
            user.save(update_fields=["activity_name"])

        profile_defaults = {}
        if nickname:
            profile_defaults["name"] = nickname

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
        redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_to)
