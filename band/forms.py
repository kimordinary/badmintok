from django import forms
from .models import (
    Band, BandPost, BandComment, BandVote, BandVoteOption,
    BandSchedule, BandScheduleApplication
)


class MultipleFileInput(forms.FileInput):
    """여러 파일 업로드를 지원하는 커스텀 위젯"""
    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        attrs['multiple'] = True
        self.attrs.update(attrs)


class BandForm(forms.ModelForm):
    """밴드 생성/수정 폼"""

    CATEGORY_CHOICES = [
        ("flash", "번개"),
        ("group", "모임"),
        ("club", "동호회"),
        ("center", "센터"),
    ]

    # 실제 모델 필드(categories, 쉼표 문자열)를 위한 UI - 다중 선택
    categories = forms.MultipleChoiceField(
        label="분류",
        required=False,
        choices=CATEGORY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text="여러 개를 선택할 수 있습니다.",
    )

    class Meta:
        model = Band
        fields = [
            "name", "description", "detailed_description", "band_type", "region",
            "cover_image", "profile_image", "is_public", "join_approval_required",
            # 센터(시설) 전용 필드 — band_type='center'일 때만 의미 있음
            "facility_address", "facility_address_detail", "facility_phone",
            "facility_operating_hours", "facility_pricing", "facility_court_count",
            "facility_amenities", "facility_latitude", "facility_longitude",
            "applicant_contact_phone",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "모임 이름을 입력하세요"}),
            "description": forms.TextInput(attrs={"class": "form-input", "placeholder": "모임 한줄 소개를 입력하세요", "maxlength": "500"}),
            "detailed_description": forms.Textarea(attrs={"class": "form-input", "rows": 8, "placeholder": "모임에 대한 상세한 설명을 작성하세요"}),
            # band_type는 주요 타입으로만 사용하고, UI에서는 분류 아코디언(체크박스)만 노출
            "band_type": forms.HiddenInput(),
            "region": forms.Select(attrs={"class": "form-input"}),
            "cover_image": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "profile_image": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "join_approval_required": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "facility_address": forms.TextInput(attrs={"class": "form-input", "placeholder": "예: 서울시 송파구 올림픽로 25"}),
            "facility_address_detail": forms.TextInput(attrs={"class": "form-input", "placeholder": "예: 지하 1층"}),
            "facility_phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "예: 02-1234-5678"}),
            "facility_operating_hours": forms.TextInput(attrs={"class": "form-input", "placeholder": "예: 평일 06:00-23:00 / 주말 08:00-22:00"}),
            "facility_pricing": forms.TextInput(attrs={"class": "form-input", "placeholder": "예: 1시간 ₩10,000"}),
            "facility_court_count": forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
            "facility_amenities": forms.TextInput(attrs={"class": "form-input", "placeholder": "예: 샤워실, 락커, 주차장 (쉼표 구분)"}),
            "facility_latitude": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "37.5142"}),
            "facility_longitude": forms.NumberInput(attrs={"class": "form-input", "step": "any", "placeholder": "127.1027"}),
            "applicant_contact_phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "예: 010-1234-5678"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 센터 전용 필드 — 일반 모임/동호회 생성 폼엔 렌더링되지 않으므로 필수 해제
        self.fields["facility_court_count"].required = False
        # 기존 밴드의 categories 값을 초기값으로 설정
        instance = getattr(self, "instance", None)
        if instance and instance.pk and instance.categories:
            self.fields["categories"].initial = instance.categories.split(",")
        elif instance and instance.pk:
            # categories가 비어 있으면 기본으로 주요 유형 하나를 넣어둠
            self.fields["categories"].initial = [instance.band_type]

    def clean_facility_court_count(self):
        # 빈 값으로 제출되면(비센터 생성) 0으로 보정 — 모델 필드는 NOT NULL
        return self.cleaned_data.get("facility_court_count") or 0


class BandPostForm(forms.ModelForm):
    """밴드 게시글 작성/수정 폼"""
    images = forms.ImageField(
        required=False,
        widget=MultipleFileInput(attrs={"accept": "image/*", "class": "form-input"}),
        help_text="여러 이미지를 선택할 수 있습니다."
    )

    class Meta:
        model = BandPost
        fields = ["title", "content", "post_type", "is_pinned", "is_notice"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "제목 (선택사항)"}),
            "content": forms.Textarea(attrs={"class": "form-input", "rows": 10, "placeholder": "내용을 작성하세요"}),
            "post_type": forms.Select(attrs={"class": "form-input"}),
            "is_pinned": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_notice": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # 일반 사용자는 고정/공지 설정 불가
        if user:
            member = None
            if self.instance and self.instance.pk:
                member = self.instance.band.members.filter(user=user).first()
            if not member or member.role == "member":
                self.fields["is_pinned"].widget.attrs["disabled"] = True
                self.fields["is_notice"].widget.attrs["disabled"] = True


class BandCommentForm(forms.ModelForm):
    """밴드 댓글 작성 폼"""
    class Meta:
        model = BandComment
        fields = ["content", "parent"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "댓글을 작성하세요"}),
            "parent": forms.HiddenInput(),
        }


class BandVoteForm(forms.ModelForm):
    """밴드 투표 생성 폼"""
    options = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 5, "placeholder": "각 줄에 하나씩 옵션을 입력하세요"}),
        help_text="각 줄에 하나씩 투표 옵션을 입력하세요."
    )

    class Meta:
        model = BandVote
        fields = ["title", "is_multiple_choice", "end_datetime"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "투표 제목"}),
            "is_multiple_choice": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "end_datetime": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
        }


class BandScheduleForm(forms.ModelForm):
    """밴드 일정 생성/수정 폼"""
    class Meta:
        model = BandSchedule
        fields = [
            "title", "description", "start_datetime", "end_datetime",
            "location", "max_participants", "requires_approval", "application_deadline", "bank_account"
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "일정 제목"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 5, "placeholder": "모임 참가 조건 및 설명"}),
            "start_datetime": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "end_datetime": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "장소"}),
            "max_participants": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "requires_approval": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "application_deadline": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "bank_account": forms.TextInput(attrs={"class": "form-input", "placeholder": "카카오뱅크 3333-00-0000000 홍길동"}),
        }


class BandScheduleApplicationForm(forms.ModelForm):
    """밴드 일정 신청 폼"""
    class Meta:
        model = BandScheduleApplication
        fields = ["notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "신청 메모 (선택사항)"}),
        }

