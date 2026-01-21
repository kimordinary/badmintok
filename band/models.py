from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from PIL import Image
import os


class Band(models.Model):
    """밴드(소모임) 모델"""
    class BandType(models.TextChoices):
        FLASH = "flash", _("번개")
        GROUP = "group", _("모임")
        CLUB = "club", _("동호회")
    
    class Region(models.TextChoices):
        ALL = "all", _("전체")
        CAPITAL = "capital", _("수도권")
        # 'busan' 코드는 영남권(부산/대구/울산/경북/경남) 전체를 의미
        BUSAN = "busan", _("영남권")
        DAEGU = "daegu", _("대구권")
        # 'gwangju' 코드는 호남권(광주/전북/전남) 전체를 의미
        GWANGJU = "gwangju", _("호남권")
        # 'daejeon' 코드는 충청권(대전/세종/충북/충남) 전체를 의미
        DAEJEON = "daejeon", _("충청권")
        ULSAN = "ulsan", _("울산권")
        JEJU = "jeju", _("제주권")
    
    # 분류 코드 → 라벨 매핑 (모델 레벨에서 공통 사용)
    CATEGORY_LABELS = {
        "flash": _("번개"),
        "group": _("모임"),
        "club": _("동호회"),
    }

    name = models.CharField(_("모임 이름"), max_length=200)
    description = models.CharField(_("모임 한줄 소개"), max_length=500, blank=True, help_text="짧은 한줄 소개를 입력하세요.")
    detailed_description = models.TextField(_("모임 설명"), blank=True, help_text="모임에 대한 상세한 설명을 입력하세요.")
    band_type = models.CharField(_("주요 유형"), max_length=20, choices=BandType.choices, default=BandType.GROUP)
    region = models.CharField(_("지역"), max_length=20, choices=Region.choices, default=Region.ALL)
    # 쉼표로 구분된 분류 코드 목록 (flash, group, club 등)
    categories = models.CharField(_("분류 코드"), max_length=100, blank=True, help_text="쉼표로 구분된 분류 코드 (flash,group,club)")
    flash_region_detail = models.CharField(_("번개 구체 지역"), max_length=20, blank=True, help_text="번개 생성 시 선택한 구체 지역 (서울, 경기, 인천 등)")
    cover_image = models.ImageField(_("커버 이미지"), upload_to="band/covers/", blank=True, null=True)
    profile_image = models.ImageField(_("프로필 이미지"), upload_to="band/profiles/", blank=True, null=True)
    is_public = models.BooleanField(_("공개 여부"), default=True)
    join_approval_required = models.BooleanField(_("가입 승인 필요"), default=False)
    # 관리자 승인 관련 필드 (모임/동호회만 사용)
    is_approved = models.BooleanField(_("관리자 승인"), default=True, help_text="모임/동호회 생성 시 관리자 승인이 필요합니다.")
    rejection_reason = models.TextField(_("거부 사유"), blank=True, help_text="승인 거부 시 사유를 입력합니다.")
    approved_at = models.DateTimeField(_("승인 일시"), blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_bands",
        blank=True,
        null=True,
        verbose_name=_("승인자")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_bands",
        verbose_name=_("생성자")
    )
    # 삭제 신청 관련 필드
    deletion_requested = models.BooleanField(_("삭제 신청"), default=False, help_text="모임 삭제 신청 여부")
    deletion_reason = models.TextField(_("삭제 사유"), blank=True, help_text="모임 삭제 신청 시 사유를 입력합니다.")
    deletion_requested_at = models.DateTimeField(_("삭제 신청 일시"), blank=True, null=True)
    deletion_approved_at = models.DateTimeField(_("삭제 승인 일시"), blank=True, null=True)
    deletion_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="deletion_approved_bands",
        blank=True,
        null=True,
        verbose_name=_("삭제 승인자")
    )
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    class Meta:
        verbose_name = _("밴드")
        verbose_name_plural = _("밴드")
        indexes = [
            models.Index(fields=["created_by"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.filter(status="active").count()

    @property
    def bookmark_count(self):
        return self.bookmarks.count()

    @property
    def post_count(self):
        return self.posts.count()

    @property
    def category_codes(self):
        """쉼표로 구분된 categories 문자열을 코드 리스트로 변환"""
        if not self.categories:
            return []
        return [code.strip() for code in self.categories.split(",") if code.strip()]

    @property
    def category_labels(self):
        """카테고리 라벨 리스트 (번개/모임/동호회 등)"""
        return [label for code, label in self.category_items]

    @property
    def category_items(self):
        """(코드, 라벨) 튜플 리스트 - 템플릿에서 색상/텍스트 모두 사용"""
        items = []
        for code in self.category_codes:
            label = self.CATEGORY_LABELS.get(code, code)
            items.append((code, label))
        return items

    def save(self, *args, **kwargs):
        """이미지 자동 리사이즈 처리"""
        # cover_image가 변경되었는지 확인
        cover_image_changed = False
        if self.pk:
            try:
                old_instance = Band.objects.get(pk=self.pk)
                if old_instance.cover_image != self.cover_image:
                    cover_image_changed = True
            except Band.DoesNotExist:
                cover_image_changed = True
        else:
            # 새 인스턴스인 경우
            cover_image_changed = bool(self.cover_image)
        
        super().save(*args, **kwargs)
        
        # 커버 이미지 리사이즈 (1200x450px, 8:3 비율) - 변경된 경우에만
        if cover_image_changed and self.cover_image:
            try:
                # 이미지 파일이 실제로 존재하는지 확인
                if not os.path.exists(self.cover_image.path):
                    return
                
                img = Image.open(self.cover_image.path)
                # RGB 모드로 변환 (JPEG 저장을 위해)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 목표 크기: 1200x450px (8:3 비율)
                target_width = 1200
                target_height = 450
                
                # 현재 이미지 크기
                current_width, current_height = img.size
                
                # 이미 목표 크기와 같으면 스킵
                if current_width == target_width and current_height == target_height:
                    return
                
                # 비율 유지하며 리사이즈
                # 8:3 비율로 크롭하거나 리사이즈
                target_ratio = target_width / target_height  # 8:3 = 2.666...
                current_ratio = current_width / current_height
                
                if current_ratio > target_ratio:
                    # 너무 넓은 경우: 높이 기준으로 리사이즈 후 가로 크롭
                    new_height = target_height
                    new_width = int(current_width * (target_height / current_height))
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # 가운데 기준으로 크롭
                    left = (new_width - target_width) // 2
                    img = img.crop((left, 0, left + target_width, target_height))
                else:
                    # 너무 좁은 경우: 너비 기준으로 리사이즈 후 세로 크롭
                    new_width = target_width
                    new_height = int(current_height * (target_width / current_width))
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # 가운데 기준으로 크롭
                    top = (new_height - target_height) // 2
                    img = img.crop((0, top, target_width, top + target_height))
                
                # 최종 크기 확인 및 리사이즈
                if img.size != (target_width, target_height):
                    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # 이미지 저장 (품질 85%)
                img.save(self.cover_image.path, 'JPEG', quality=85, optimize=True)
            except Exception as e:
                # 이미지 처리 실패 시에도 저장은 진행 (기존 이미지 유지)
                # 로깅은 필요시 추가 가능
                pass


class BandMember(models.Model):
    """밴드 멤버 모델"""
    class Role(models.TextChoices):
        OWNER = "owner", _("모임장")
        ADMIN = "admin", _("관리자")
        MEMBER = "member", _("멤버")

    class Status(models.TextChoices):
        ACTIVE = "active", _("활성")
        PENDING = "pending", _("대기중")
        BANNED = "banned", _("차단됨")

    band = models.ForeignKey(
        Band,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name=_("밴드")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="band_memberships",
        verbose_name=_("사용자")
    )
    role = models.CharField(_("역할"), max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(_("상태"), max_length=20, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(_("가입일"), auto_now_add=True)
    last_visited_at = models.DateTimeField(_("마지막 방문일"), auto_now=True)

    class Meta:
        verbose_name = _("밴드 멤버")
        verbose_name_plural = _("밴드 멤버")
        unique_together = [["band", "user"]]
        indexes = [
            models.Index(fields=["band"]),
            models.Index(fields=["user"]),
            models.Index(fields=["role"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.band.name} - {self.user.activity_name}"


class BandPost(models.Model):
    """밴드 게시글 모델"""
    class PostType(models.TextChoices):
        GENERAL = "general", _("일반")
        ANNOUNCEMENT = "announcement", _("공지")
        SCHEDULE = "schedule", _("일정")
        VOTE = "vote", _("투표")
        QUESTION = "question", _("질문")

    band = models.ForeignKey(
        Band,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name=_("밴드")
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="band_posts",
        verbose_name=_("작성자")
    )
    title = models.CharField(_("제목"), max_length=200, blank=True)
    content = models.TextField(_("내용"))
    post_type = models.CharField(_("글 유형"), max_length=20, choices=PostType.choices, default=PostType.GENERAL)
    is_pinned = models.BooleanField(_("고정"), default=False)
    is_notice = models.BooleanField(_("공지"), default=False)
    view_count = models.IntegerField(_("조회수"), default=0)
    like_count = models.IntegerField(_("좋아요 수"), default=0)
    comment_count = models.IntegerField(_("댓글 수"), default=0)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    class Meta:
        verbose_name = _("밴드 게시글")
        verbose_name_plural = _("밴드 게시글")
        ordering = ["-is_pinned", "-is_notice", "-created_at"]
        indexes = [
            models.Index(fields=["band"]),
            models.Index(fields=["author"]),
            models.Index(fields=["post_type"]),
            models.Index(fields=["is_pinned"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.band.name} - {self.title or self.content[:50]}"


class BandPostImage(models.Model):
    """밴드 게시글 이미지 모델"""
    post = models.ForeignKey(
        BandPost,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("게시글"),
        null=True,
        blank=True
    )
    image = models.ImageField(_("이미지"), upload_to="band/posts/")
    order_index = models.IntegerField(_("순서"), default=0)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        verbose_name = _("밴드 게시글 이미지")
        verbose_name_plural = _("밴드 게시글 이미지")
        ordering = ["order_index"]
        indexes = [
            models.Index(fields=["post"]),
            models.Index(fields=["post", "order_index"]),
        ]

    def __str__(self):
        return f"{self.post} - 이미지 {self.order_index + 1}"


class BandComment(models.Model):
    """밴드 댓글 모델"""
    post = models.ForeignKey(
        BandPost,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("게시글")
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="band_comments",
        verbose_name=_("작성자")
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
        verbose_name=_("부모 댓글")
    )
    content = models.TextField(_("내용"))
    like_count = models.IntegerField(_("좋아요 수"), default=0)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    class Meta:
        verbose_name = _("밴드 댓글")
        verbose_name_plural = _("밴드 댓글")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post"]),
            models.Index(fields=["author"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.post} - {self.content[:50]}"


class BandPostLike(models.Model):
    """밴드 게시글 좋아요 모델"""
    post = models.ForeignKey(
        BandPost,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name=_("게시글")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="band_post_likes",
        verbose_name=_("사용자")
    )
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        verbose_name = _("밴드 게시글 좋아요")
        verbose_name_plural = _("밴드 게시글 좋아요")
        unique_together = [["post", "user"]]
        indexes = [
            models.Index(fields=["post"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.post} - {self.user.activity_name}"


class BandCommentLike(models.Model):
    """밴드 댓글 좋아요 모델"""
    comment = models.ForeignKey(
        BandComment,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name=_("댓글")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="band_comment_likes",
        verbose_name=_("사용자")
    )
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        verbose_name = _("밴드 댓글 좋아요")
        verbose_name_plural = _("밴드 댓글 좋아요")
        unique_together = [["comment", "user"]]
        indexes = [
            models.Index(fields=["comment"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.comment} - {self.user.activity_name}"


class BandVote(models.Model):
    """밴드 투표 모델"""
    post = models.OneToOneField(
        BandPost,
        on_delete=models.CASCADE,
        related_name="vote",
        verbose_name=_("게시글")
    )
    title = models.CharField(_("투표 제목"), max_length=200)
    is_multiple_choice = models.BooleanField(_("복수 선택"), default=False)
    end_datetime = models.DateTimeField(_("종료 일시"), null=True, blank=True)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        verbose_name = _("밴드 투표")
        verbose_name_plural = _("밴드 투표")
        indexes = [
            models.Index(fields=["post"]),
            models.Index(fields=["end_datetime"]),
        ]

    def __str__(self):
        return f"{self.post} - {self.title}"


class BandVoteOption(models.Model):
    """밴드 투표 옵션 모델"""
    vote = models.ForeignKey(
        BandVote,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name=_("투표")
    )
    option_text = models.CharField(_("옵션 텍스트"), max_length=200)
    vote_count = models.IntegerField(_("투표 수"), default=0)
    order_index = models.IntegerField(_("순서"), default=0)

    class Meta:
        verbose_name = _("밴드 투표 옵션")
        verbose_name_plural = _("밴드 투표 옵션")
        ordering = ["order_index"]
        indexes = [
            models.Index(fields=["vote"]),
            models.Index(fields=["vote", "order_index"]),
        ]

    def __str__(self):
        return f"{self.vote} - {self.option_text}"


class BandVoteChoice(models.Model):
    """밴드 투표 선택 모델"""
    vote = models.ForeignKey(
        BandVote,
        on_delete=models.CASCADE,
        related_name="choices",
        verbose_name=_("투표")
    )
    option = models.ForeignKey(
        BandVoteOption,
        on_delete=models.CASCADE,
        related_name="choices",
        verbose_name=_("옵션")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="band_vote_choices",
        verbose_name=_("사용자")
    )
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        verbose_name = _("밴드 투표 선택")
        verbose_name_plural = _("밴드 투표 선택")
        unique_together = [["vote", "user", "option"]]
        indexes = [
            models.Index(fields=["vote"]),
            models.Index(fields=["option"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.vote} - {self.user.activity_name} - {self.option.option_text}"


class BandSchedule(models.Model):
    """밴드 일정 모델"""
    band = models.ForeignKey(
        Band,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name=_("밴드")
    )
    post = models.ForeignKey(
        BandPost,
        on_delete=models.SET_NULL,
        related_name="schedule",
        null=True,
        blank=True,
        verbose_name=_("게시글")
    )
    title = models.CharField(_("제목"), max_length=200)
    description = models.TextField(_("모임 참가 조건"), blank=True)
    start_datetime = models.DateTimeField(_("시작 일시"))
    end_datetime = models.DateTimeField(_("종료 일시"), null=True, blank=True)
    location = models.CharField(_("장소"), max_length=200, blank=True)
    max_participants = models.IntegerField(_("최대 참가 인원"), null=True, blank=True)
    current_participants = models.IntegerField(_("현재 참가 인원"), default=0)
    requires_approval = models.BooleanField(_("승인 필요"), default=False)
    application_deadline = models.DateTimeField(_("신청 마감일"), null=True, blank=True)
    bank_account = models.CharField(_("입금 계좌"), max_length=100, blank=True, help_text="참가비 입금 계좌 (예: 카카오뱅크 3333-00-0000000 홍길동)")
    is_closed = models.BooleanField(_("모집 마감"), default=False, help_text="수동으로 모집을 마감합니다")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_schedules",
        verbose_name=_("생성자")
    )
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    class Meta:
        verbose_name = _("밴드 일정")
        verbose_name_plural = _("밴드 일정")
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["band"]),
            models.Index(fields=["post"]),
            models.Index(fields=["start_datetime"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["application_deadline"]),
        ]

    def __str__(self):
        return f"{self.band.name} - {self.title}"


class BandScheduleApplication(models.Model):
    """밴드 일정 신청 모델"""
    class Status(models.TextChoices):
        PENDING = "pending", _("대기중")
        APPROVED = "approved", _("승인됨")
        REJECTED = "rejected", _("거부됨")
        CANCELLED = "cancelled", _("취소됨")

    schedule = models.ForeignKey(
        BandSchedule,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name=_("일정")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="schedule_applications",
        verbose_name=_("사용자")
    )
    status = models.CharField(_("상태"), max_length=20, choices=Status.choices, default=Status.PENDING)
    applied_at = models.DateTimeField(_("신청일"), auto_now_add=True)
    reviewed_at = models.DateTimeField(_("검토일"), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_applications",
        null=True,
        blank=True,
        verbose_name=_("검토자")
    )
    rejection_reason = models.TextField(_("거부 사유"), blank=True)
    notes = models.TextField(_("신청 메모"), blank=True)

    class Meta:
        verbose_name = _("밴드 일정 신청")
        verbose_name_plural = _("밴드 일정 신청")
        unique_together = [["schedule", "user"]]
        indexes = [
            models.Index(fields=["schedule"]),
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-applied_at"]),
            models.Index(fields=["reviewed_by"]),
        ]

    def __str__(self):
        return f"{self.schedule.title} - {self.user.activity_name} ({self.get_status_display()})"


def schedule_image_upload_to(instance, filename):
    """일정 이미지 파일명 생성 함수 - 파일명을 짧게 생성"""
    import uuid
    import os
    # 파일 확장자 추출
    ext = filename.split('.')[-1].lower()
    # UUID를 사용하여 짧은 고유 파일명 생성
    unique_filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    return f"band/schedules/images/{unique_filename}"


class BandScheduleImage(models.Model):
    """밴드 일정 이미지 모델"""
    schedule = models.ForeignKey(
        BandSchedule,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("일정")
    )
    image = models.ImageField(
        _("이미지"),
        upload_to=schedule_image_upload_to,
        help_text="번개 이미지 (3:4 비율 권장)"
    )
    order = models.IntegerField(_("순서"), default=0, help_text="이미지 표시 순서")
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        verbose_name = _("밴드 일정 이미지")
        verbose_name_plural = _("밴드 일정 이미지")
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["schedule", "order"]),
        ]

    def __str__(self):
        return f"{self.schedule.title} - 이미지 {self.order + 1}"


class BandBookmark(models.Model):
    """밴드 북마크 (관심 모임) 모델"""
    band = models.ForeignKey(
        Band,
        on_delete=models.CASCADE,
        related_name="bookmarks",
        verbose_name=_("밴드")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="band_bookmarks",
        verbose_name=_("사용자")
    )
    created_at = models.DateTimeField(_("북마크 일시"), auto_now_add=True)

    class Meta:
        verbose_name = _("밴드 북마크")
        verbose_name_plural = _("밴드 북마크")
        unique_together = [["band", "user"]]
        indexes = [
            models.Index(fields=["band"]),
            models.Index(fields=["user"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.activity_name} - {self.band.name}"

