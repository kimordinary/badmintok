from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """게시글 카테고리 모델 (계층 구조 지원)"""

    class Source(models.TextChoices):
        COMMUNITY = "community", _("동호인톡")
        BADMINTOK = "badmintok", _("배드민톡")

    name = models.CharField(_("카테고리명"), max_length=50, unique=True)
    slug = models.SlugField(_("슬러그"), max_length=50, unique=True, help_text=_("URL에 사용될 고유 식별자"))
    source = models.CharField(
        _("출처"),
        max_length=20,
        choices=Source.choices,
        default=Source.COMMUNITY,
        help_text=_("배드민톡 또는 동호인톡")
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("상위 카테고리"),
        help_text=_("상위 카테고리를 선택하세요 (최상위인 경우 비워두세요)")
    )
    display_order = models.PositiveIntegerField(_("표시 순서"), default=0, help_text=_("작은 숫자일수록 먼저 표시됩니다"))
    is_active = models.BooleanField(_("활성화"), default=True)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    class Meta:
        verbose_name = _("카테고리")
        verbose_name_plural = _("카테고리")
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["source", "is_active", "display_order"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["source", "parent"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_full_path(self):
        """전체 경로 반환 (예: 뉴스 > 대회소식)"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return " > ".join(path)


class CategoryManager(models.Manager):
    """카테고리 기본 Manager"""
    pass


class BadmintokCategoryManager(models.Manager):
    """배드민톡 카테고리만 필터링하는 Manager"""
    def get_queryset(self):
        # 배드민톡 소스 카테고리들 (부모 + 자식 모두)
        return super().get_queryset().filter(source='badmintok')


class CommunityCategoryManager(models.Manager):
    """동호인톡 카테고리만 필터링하는 Manager"""
    def get_queryset(self):
        # 동호인톡 소스 카테고리들 (부모 + 자식 모두)
        return super().get_queryset().filter(source='community')


class Post(models.Model):
    """게시글 모델"""
    
    class Source(models.TextChoices):
        COMMUNITY = "community", _("동호인톡")
        BADMINTOK = "badmintok", _("배드민톡")
        MEMBER_REVIEWS = "member_reviews", _("동호인 리뷰")
    
    title = models.CharField(_("제목"), max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("메인 카테고리")
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="posts_multi",
        verbose_name=_("카테고리"),
        help_text=_("여러 카테고리 선택 가능")
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name=_("작성자")
    )
    content = models.TextField(_("내용"))
    source = models.CharField(
        _("출처"),
        max_length=20,
        choices=Source.choices,
        default=Source.COMMUNITY
    )
    
    # 날짜 정보
    created_at = models.DateTimeField(_("작성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)
    
    # 통계 정보
    view_count = models.PositiveIntegerField(_("조회수"), default=0)
    like_count = models.PositiveIntegerField(_("좋아요 수"), default=0)
    comment_count = models.PositiveIntegerField(_("댓글 수"), default=0)
    
    # 좋아요 (ManyToMany로 처리)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True,
        verbose_name=_("좋아요한 사용자")
    )
    
    # 메타 정보
    is_deleted = models.BooleanField(_("삭제 여부"), default=False)
    is_pinned = models.BooleanField(_("고정 여부"), default=False)  # 공지사항용
    is_draft = models.BooleanField(_("임시저장"), default=False, help_text=_("임시저장 글은 공개되지 않습니다"))

    # SEO 및 발행 관련
    slug = models.SlugField(_("슬러그"), max_length=45, blank=True, help_text=_("URL에 사용될 고유 식별자 (한글 가능)"))
    published_at = models.DateTimeField(_("발행 일시"), null=True, blank=True, help_text=_("예약 발행 시간 설정 (비어있으면 즉시 발행)"))
    thumbnail = models.ImageField(_("썸네일"), upload_to="community/thumbnails/%Y/%m/%d/", blank=True, null=True, help_text=_("게시글 썸네일 이미지"))
    thumbnail_alt = models.CharField(_("썸네일 대체 텍스트"), max_length=200, blank=True, help_text=_("썸네일 이미지의 Alt 텍스트"))
    focus_keyword = models.CharField(_("포커스 키워드"), max_length=100, blank=True, help_text=_("SEO 최적화를 위한 포커스 키워드"))
    meta_description = models.TextField(_("메타 설명"), max_length=160, blank=True, help_text=_("검색 엔진에 표시될 설명 (160자 이내 권장)"))

    class Meta:
        verbose_name = _("게시글")
        verbose_name_plural = _("게시글")
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["category", "-created_at"]),
            models.Index(fields=["author"]),
            models.Index(fields=["-view_count"]),  # hot 글 조회를 위한 인덱스
            models.Index(fields=["source", "-created_at"]),  # source별 조회를 위한 인덱스
            models.Index(fields=["slug"]),  # slug 조회를 위한 인덱스
            models.Index(fields=["published_at"]),  # 발행 시간 조회를 위한 인덱스
        ]
    
    def __str__(self):
        return f"{self.title} - {self.author.activity_name}"
    
    def get_category_display(self):
        """카테고리 표시명 반환 (하위 호환성)"""
        return self.category.name if self.category else ""
    
    def increase_view_count(self):
        """조회수 증가"""
        self.view_count += 1
        self.save(update_fields=["view_count"])
    
    def update_like_count(self):
        """좋아요 수 업데이트"""
        self.like_count = self.likes.count()
        self.save(update_fields=["like_count"])
    
    def update_comment_count(self):
        """댓글 수 업데이트"""
        self.comment_count = self.comments.filter(is_deleted=False).count()
        self.save(update_fields=["comment_count"])

    def generate_slug(self):
        """제목으로부터 슬러그 자동 생성 (한글 지원)"""
        from django.utils.text import slugify
        import re

        if not self.title:
            return ""

        # 한글, 영문, 숫자만 남기고 공백을 -로 변환
        slug_base = re.sub(r'[^\w\s가-힣-]', '', self.title)
        slug_base = re.sub(r'[-\s]+', '-', slug_base).strip('-')

        # 슬러그가 너무 길면 45자로 제한
        if len(slug_base) > 45:
            slug_base = slug_base[:45].rsplit('-', 1)[0]

        return slug_base.lower()

    def save(self, *args, **kwargs):
        """저장 시 슬러그 자동 생성 및 발행 시간 처리"""
        # 슬러그가 비어있으면 자동 생성
        if not self.slug and self.title:
            base_slug = self.generate_slug()
            
            # 슬러그 중복 방지: 같은 슬러그가 이미 존재하면 번호 추가
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk if self.pk else None).exists():
                # 슬러그 끝에 번호 추가 (예: "my-post-1", "my-post-2")
                suffix = f"-{counter}"
                # 슬러그 길이 제한 (45자) 고려
                max_base_length = 45 - len(suffix)
                if len(base_slug) > max_base_length:
                    truncated_base = base_slug[:max_base_length].rsplit('-', 1)[0]
                    slug = f"{truncated_base}{suffix}"
                else:
                    slug = f"{base_slug}{suffix}"
                counter += 1
            
            self.slug = slug

        # 발행 시간이 설정되지 않았으면 현재 시간으로 설정
        if not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()

        super().save(*args, **kwargs)


# Proxy 모델들 - Admin에서 분리 표시를 위함


class BadmintokCategory(Category):
    """배드민톡 카테고리 Proxy 모델"""
    objects = BadmintokCategoryManager()

    class Meta:
        proxy = True
        app_label = 'badmintok'
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        ordering = []  # Category의 기본 ordering 비활성화 - Admin의 get_queryset() 순서 사용


class CommunityCategory(Category):
    """동호인톡 카테고리 Proxy 모델"""
    objects = CommunityCategoryManager()

    class Meta:
        proxy = True
        app_label = 'community'
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        ordering = []  # Category의 기본 ordering 비활성화 - Admin의 get_queryset() 순서 사용


class BadmintokPost(Post):
    """배드민톡 게시글 Proxy 모델"""

    class Meta:
        proxy = True
        app_label = 'badmintok'
        verbose_name = "게시글"
        verbose_name_plural = "게시글"


class CommunityPost(Post):
    """동호인톡 게시글 Proxy 모델 (커뮤니티 + 동호인 리뷰)"""

    class Meta:
        proxy = True
        app_label = 'community'
        verbose_name = "게시글"
        verbose_name_plural = "게시글"


class PostImage(models.Model):
    """게시글 이미지 모델"""
    
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("게시글")
    )
    image = models.ImageField(
        _("이미지"),
        upload_to="community/post_images/%Y/%m/%d/",
    )
    order = models.PositiveIntegerField(_("순서"), default=0)  # 이미지 순서
    
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("게시글 이미지")
        verbose_name_plural = _("게시글 이미지")
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["post", "order"]),
        ]
    
    def __str__(self):
        return f"{self.post.title} - 이미지 {self.order + 1}"


class Comment(models.Model):
    """댓글 모델 (대댓글 지원)"""
    
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("게시글")
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("작성자")
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name=_("부모 댓글")
    )
    content = models.TextField(_("내용"))
    
    # 날짜 정보
    created_at = models.DateTimeField(_("작성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)
    
    # 통계 정보
    like_count = models.PositiveIntegerField(_("좋아요 수"), default=0)
    
    # 좋아요 (ManyToMany로 처리)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_comments",
        blank=True,
        verbose_name=_("좋아요한 사용자")
    )
    
    # 메타 정보
    is_deleted = models.BooleanField(_("삭제 여부"), default=False)
    
    class Meta:
        verbose_name = _("댓글")
        verbose_name_plural = _("댓글")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["author"]),
            models.Index(fields=["parent"]),
        ]
    
    def __str__(self):
        return f"{self.post.title} - {self.author.activity_name}의 댓글"
    
    def is_reply(self):
        """대댓글인지 확인"""
        return self.parent is not None
    
    def update_like_count(self):
        """좋아요 수 업데이트"""
        self.like_count = self.likes.count()
        self.save(update_fields=["like_count"])


class PostShare(models.Model):
    """게시글 공유 모델"""
    
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="shares",
        verbose_name=_("게시글")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shared_posts",
        verbose_name=_("공유한 사용자")
    )
    shared_at = models.DateTimeField(_("공유일"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("게시글 공유")
        verbose_name_plural = _("게시글 공유")
        unique_together = ["post", "user"]  # 같은 사용자가 같은 게시글을 중복 공유 방지
        indexes = [
            models.Index(fields=["post"]),
            models.Index(fields=["user"]),
        ]
    
    def __str__(self):
        return f"{self.post.title} - {self.user.activity_name}이 공유"


# Signal을 사용하여 자동으로 통계 업데이트
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=Comment)
def update_post_comment_count_on_save(sender, instance, **kwargs):
    """댓글 저장/수정 시 게시글 댓글 수 업데이트"""
    if not instance.is_deleted:
        instance.post.update_comment_count()


@receiver(post_delete, sender=Comment)
def update_post_comment_count_on_delete(sender, instance, **kwargs):
    """댓글 삭제 시 게시글 댓글 수 업데이트"""
    instance.post.update_comment_count()


@receiver(post_save, sender=Post.likes.through)
def update_post_like_count_on_save(sender, instance, **kwargs):
    """좋아요 추가 시 게시글 좋아요 수 업데이트"""
    instance.post.update_like_count()


@receiver(post_delete, sender=Post.likes.through)
def update_post_like_count_on_delete(sender, instance, **kwargs):
    """좋아요 제거 시 게시글 좋아요 수 업데이트"""
    instance.post.update_like_count()


@receiver(post_save, sender=Comment.likes.through)
def update_comment_like_count_on_save(sender, instance, **kwargs):
    """댓글 좋아요 추가 시 댓글 좋아요 수 업데이트"""
    instance.comment.update_like_count()


@receiver(post_delete, sender=Comment.likes.through)
def update_comment_like_count_on_delete(sender, instance, **kwargs):
    """댓글 좋아요 제거 시 댓글 좋아요 수 업데이트"""
    instance.comment.update_like_count()


