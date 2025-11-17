from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class UserSignupForm(UserCreationForm):
    error_messages = {
        "password_mismatch": "비밀번호와 비밀번호 확인이 일치하지 않습니다.",
    }

    email = forms.EmailField(label="이메일", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    activity_name = forms.CharField(label="활동명", max_length=150)

    class Meta:
        model = User
        fields = ("email", "activity_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_configs = {
            "email": {"placeholder": "이메일 주소를 입력하세요", "autofocus": True},
            "activity_name": {"placeholder": "활동명을 입력하세요"},
            "password1": {"placeholder": "비밀번호를 입력하세요"},
            "password2": {"placeholder": "비밀번호를 다시 입력하세요"},
        }

        for name, config in field_configs.items():
            if name in self.fields:
                attrs = {"class": "form-input"}
                attrs.update({k: v for k, v in config.items() if v is not None})
                self.fields[name].widget.attrs.update(attrs)

        if "password1" in self.fields:
            self.fields["password1"].label = "비밀번호"
            self.fields["password1"].help_text = (
                "비밀번호는 8자 이상이어야 하며 다른 개인정보와 너무 비슷하지 않아야 합니다. "
                "일반적으로 사용되는 비밀번호와 숫자로만 된 비밀번호는 사용할 수 없습니다."
            )
        if "password2" in self.fields:
            self.fields["password2"].label = "비밀번호 확인"
            self.fields["password2"].help_text = "비밀번호를 다시 입력하세요."

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("이미 사용 중인 이메일입니다.")
        return email


class UserLoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "이메일 또는 비밀번호가 올바르지 않습니다.",
        "inactive": "비활성화된 계정입니다. 관리자에게 문의하세요.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "username": "이메일 주소를 입력하세요",
            "password": "비밀번호를 입력하세요",
        }
        for name, field in self.fields.items():
            attrs = {"class": "form-input"}
            if name in placeholders:
                attrs["placeholder"] = placeholders[name]
            field.widget.attrs.update(attrs)

        if "username" in self.fields:
            self.fields["username"].label = "이메일"
        if "password" in self.fields:
            self.fields["password"].label = "비밀번호"
