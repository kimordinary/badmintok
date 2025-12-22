from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth import password_validation

from .models import User, UserProfile, Inquiry


class UserSignupForm(UserCreationForm):
    error_messages = {
        "password_mismatch": "비밀번호와 비밀번호 확인이 일치하지 않습니다.",
    }

    email = forms.EmailField(label="이메일", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    activity_name = forms.CharField(label="활동명", max_length=150)
    terms_agreed = forms.BooleanField(
        label="",
        required=True,
        error_messages={"required": "이용약관에 동의해주세요."}
    )
    privacy_agreed = forms.BooleanField(
        label="",
        required=True,
        error_messages={"required": "개인정보처리방침에 동의해주세요."}
    )

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


class UserProfileForm(forms.ModelForm):
    """프로필 편집 폼"""
    activity_name = forms.CharField(
        label="활동명",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "활동명을 입력하세요"})
    )

    class Meta:
        model = UserProfile
        fields = [
            "profile_image", "name", "gender", "age_range", "birthday",
            "birth_year", "phone_number",
            "shipping_receiver", "shipping_phone_number", "shipping_address"
        ]
        widgets = {
            "profile_image": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "이름을 입력하세요"}),
            "gender": forms.Select(attrs={"class": "form-input"}),
            "age_range": forms.TextInput(attrs={"class": "form-input", "placeholder": "연령대를 입력하세요"}),
            "birthday": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "birth_year": forms.NumberInput(attrs={"class": "form-input", "placeholder": "출생연도"}),
            "phone_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "전화번호를 입력하세요"}),
            "shipping_receiver": forms.TextInput(attrs={"class": "form-input", "placeholder": "수령인명을 입력하세요"}),
            "shipping_phone_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "배송지 전화번호를 입력하세요"}),
            "shipping_address": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "배송지 주소를 입력하세요"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # 기존 활동명 설정
        if self.user and self.instance.pk:
            self.fields["activity_name"].initial = self.user.activity_name
        elif self.user:
            self.fields["activity_name"].initial = self.user.activity_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # 활동명 업데이트
        if self.user and "activity_name" in self.cleaned_data:
            self.user.activity_name = self.cleaned_data["activity_name"]
            if commit:
                self.user.save()
        
        if commit:
            profile.save()
        return profile


class PasswordChangeFormCustom(PasswordChangeForm):
    """비밀번호 변경 폼"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-input"})
        
        self.fields["old_password"].label = "현재 비밀번호"
        self.fields["new_password1"].label = "새 비밀번호"
        self.fields["new_password2"].label = "새 비밀번호 확인"


class InquiryForm(forms.ModelForm):
    """문의하기 폼"""
    class Meta:
        model = Inquiry
        fields = ["category", "title", "content"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "문의 제목을 입력하세요"}),
            "content": forms.Textarea(attrs={"class": "form-input", "rows": 8, "placeholder": "문의 내용을 입력하세요"}),
        }
