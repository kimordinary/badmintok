from rest_framework import serializers
from band.models import (
    Band, BandMember, BandPost, BandPostImage, BandComment,
    BandPostLike, BandCommentLike,
    BandVote, BandVoteOption, BandVoteChoice,
    BandSchedule, BandScheduleApplication, BandScheduleImage, BandBookmark
)
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'email', 'activity_name']
        read_only_fields = ['id', 'email', 'activity_name']


class BandListSerializer(serializers.ModelSerializer):
    """밴드 목록 시리얼라이저"""
    created_by = UserSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    bookmark_count = serializers.IntegerField(read_only=True)
    post_count = serializers.IntegerField(read_only=True)
    category_labels = serializers.ListField(read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Band
        fields = [
            'id', 'name', 'description', 'band_type', 'region',
            'flash_region_detail', 'is_public', 'join_approval_required',
            'is_approved', 'created_by', 'member_count', 'bookmark_count',
            'post_count', 'category_labels', 'cover_image_url', 'profile_image_url',
            'is_bookmarked', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_cover_image_url(self, obj):
        request = self.context.get('request')
        if obj.cover_image and hasattr(obj.cover_image, 'url'):
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None

    def get_profile_image_url(self, obj):
        request = self.context.get('request')
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return BandBookmark.objects.filter(band=obj, user=request.user).exists()
        return False


class BandDetailSerializer(serializers.ModelSerializer):
    """밴드 상세 시리얼라이저"""
    created_by = UserSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    bookmark_count = serializers.IntegerField(read_only=True)
    post_count = serializers.IntegerField(read_only=True)
    category_labels = serializers.ListField(read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Band
        fields = [
            'id', 'name', 'description', 'detailed_description',
            'band_type', 'region', 'flash_region_detail', 'categories',
            'is_public', 'join_approval_required', 'is_approved',
            'created_by', 'member_count', 'bookmark_count', 'post_count',
            'category_labels', 'cover_image_url', 'profile_image_url',
            'is_bookmarked', 'is_member', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_cover_image_url(self, obj):
        request = self.context.get('request')
        if obj.cover_image and hasattr(obj.cover_image, 'url'):
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None

    def get_profile_image_url(self, obj):
        request = self.context.get('request')
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return BandBookmark.objects.filter(band=obj, user=request.user).exists()
        return False

    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return BandMember.objects.filter(
                band=obj, user=request.user, status='active'
            ).exists()
        return False


class BandPostImageSerializer(serializers.ModelSerializer):
    """밴드 게시글 이미지 시리얼라이저"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BandPostImage
        fields = ['id', 'image_url', 'order_index']
        read_only_fields = fields

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class BandPostListSerializer(serializers.ModelSerializer):
    """밴드 게시글 목록 시리얼라이저"""
    author = UserSerializer(read_only=True)
    band_name = serializers.CharField(source='band.name', read_only=True)
    first_image = serializers.SerializerMethodField()

    class Meta:
        model = BandPost
        fields = [
            'id', 'band', 'band_name', 'author', 'title', 'content',
            'post_type', 'is_pinned', 'is_notice', 'view_count',
            'like_count', 'comment_count', 'first_image',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_first_image(self, obj):
        request = self.context.get('request')
        first_image = obj.images.first()
        if first_image and first_image.image:
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None


class BandVoteOptionSerializer(serializers.ModelSerializer):
    """투표 옵션 시리얼라이저"""
    class Meta:
        model = BandVoteOption
        fields = ['id', 'option_text', 'vote_count', 'order_index']
        read_only_fields = fields


class BandVoteSerializer(serializers.ModelSerializer):
    """투표 시리얼라이저"""
    options = BandVoteOptionSerializer(many=True, read_only=True)
    user_choices = serializers.SerializerMethodField()

    class Meta:
        model = BandVote
        fields = ['id', 'title', 'is_multiple_choice', 'end_datetime', 'options', 'user_choices', 'created_at']
        read_only_fields = fields

    def get_user_choices(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return list(
                BandVoteChoice.objects.filter(
                    vote=obj, user=request.user
                ).values_list('option_id', flat=True)
            )
        return []


class BandPostDetailSerializer(serializers.ModelSerializer):
    """밴드 게시글 상세 시리얼라이저"""
    author = UserSerializer(read_only=True)
    band_name = serializers.CharField(source='band.name', read_only=True)
    images = BandPostImageSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    vote = serializers.SerializerMethodField()

    class Meta:
        model = BandPost
        fields = [
            'id', 'band', 'band_name', 'author', 'title', 'content',
            'post_type', 'is_pinned', 'is_notice', 'view_count',
            'like_count', 'comment_count', 'images', 'is_liked', 'vote',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return BandPostLike.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_vote(self, obj):
        if obj.post_type == 'vote' and hasattr(obj, 'vote'):
            try:
                return BandVoteSerializer(obj.vote, context=self.context).data
            except BandVote.DoesNotExist:
                pass
        return None


class BandScheduleImageSerializer(serializers.ModelSerializer):
    """일정 이미지 시리얼라이저"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BandScheduleImage
        fields = ['id', 'image_url', 'order']
        read_only_fields = fields

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class BandScheduleListSerializer(serializers.ModelSerializer):
    """밴드 일정 목록 시리얼라이저"""
    band_name = serializers.CharField(source='band.name', read_only=True)
    created_by = UserSerializer(read_only=True)
    is_full = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()

    class Meta:
        model = BandSchedule
        fields = [
            'id', 'band', 'band_name', 'title', 'description',
            'start_datetime', 'end_datetime', 'location',
            'max_participants', 'current_participants',
            'requires_approval', 'application_deadline',
            'bank_account', 'is_closed', 'created_by',
            'is_full', 'is_applied', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_is_full(self, obj):
        if obj.max_participants:
            return obj.current_participants >= obj.max_participants
        return False

    def get_is_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return BandScheduleApplication.objects.filter(
                schedule=obj, user=request.user
            ).exclude(status='cancelled').exists()
        return False


class BandScheduleDetailSerializer(serializers.ModelSerializer):
    """밴드 일정 상세 시리얼라이저"""
    band_name = serializers.CharField(source='band.name', read_only=True)
    created_by = UserSerializer(read_only=True)
    images = BandScheduleImageSerializer(many=True, read_only=True)
    is_full = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()
    applications = serializers.SerializerMethodField()

    class Meta:
        model = BandSchedule
        fields = [
            'id', 'band', 'band_name', 'title', 'description',
            'start_datetime', 'end_datetime', 'location',
            'max_participants', 'current_participants',
            'requires_approval', 'application_deadline',
            'bank_account', 'is_closed', 'created_by',
            'images', 'is_full', 'is_applied', 'applications',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_is_full(self, obj):
        if obj.max_participants:
            return obj.current_participants >= obj.max_participants
        return False

    def get_is_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return BandScheduleApplication.objects.filter(
                schedule=obj, user=request.user
            ).exclude(status='cancelled').exists()
        return False

    def get_applications(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # owner/admin만 전체 신청 목록 확인 가능
            is_manager = BandMember.objects.filter(
                band=obj.band, user=request.user,
                role__in=['owner', 'admin'], status='active'
            ).exists()
            if is_manager:
                apps = obj.applications.select_related('user').exclude(status='cancelled')
                return BandScheduleApplicationSerializer(apps, many=True).data
        return []


# ========== 생성/수정용 시리얼라이저 ==========

class BandCreateSerializer(serializers.ModelSerializer):
    """밴드 생성 시리얼라이저"""
    class Meta:
        model = Band
        fields = [
            'name', 'description', 'detailed_description', 'band_type',
            'region', 'flash_region_detail', 'categories', 'cover_image',
            'profile_image', 'is_public', 'join_approval_required'
        ]


class BandUpdateSerializer(serializers.ModelSerializer):
    """밴드 수정 시리얼라이저"""
    class Meta:
        model = Band
        fields = [
            'name', 'description', 'detailed_description', 'region',
            'categories', 'cover_image', 'profile_image',
            'is_public', 'join_approval_required'
        ]


class BandMemberSerializer(serializers.ModelSerializer):
    """밴드 멤버 시리얼라이저"""
    user = UserSerializer(read_only=True)

    class Meta:
        model = BandMember
        fields = ['id', 'user', 'role', 'status', 'joined_at']
        read_only_fields = fields


class BandPostCreateSerializer(serializers.ModelSerializer):
    """게시글 생성 시리얼라이저"""
    image_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = BandPost
        fields = ['title', 'content', 'post_type', 'is_pinned', 'is_notice', 'image_ids']


class BandPostUpdateSerializer(serializers.ModelSerializer):
    """게시글 수정 시리얼라이저"""
    image_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = BandPost
        fields = ['title', 'content', 'image_ids']


class BandCommentSerializer(serializers.ModelSerializer):
    """댓글 시리얼라이저"""
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = BandComment
        fields = [
            'id', 'author', 'content', 'parent', 'like_count',
            'is_liked', 'replies', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_replies(self, obj):
        if obj.parent is None:
            replies = obj.replies.select_related('author').all()
            return BandCommentSerializer(
                replies, many=True, context=self.context
            ).data
        return []

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return BandCommentLike.objects.filter(comment=obj, user=request.user).exists()
        return False


class BandCommentCreateSerializer(serializers.Serializer):
    """댓글 생성 시리얼라이저"""
    content = serializers.CharField()
    parent_id = serializers.IntegerField(required=False, allow_null=True)


class BandScheduleCreateSerializer(serializers.ModelSerializer):
    """일정 생성 시리얼라이저"""
    class Meta:
        model = BandSchedule
        fields = [
            'title', 'description', 'start_datetime', 'end_datetime',
            'location', 'max_participants', 'requires_approval',
            'application_deadline', 'bank_account'
        ]


class BandScheduleApplicationSerializer(serializers.ModelSerializer):
    """일정 신청 시리얼라이저"""
    user = UserSerializer(read_only=True)

    class Meta:
        model = BandScheduleApplication
        fields = ['id', 'user', 'status', 'notes', 'applied_at', 'reviewed_at']
        read_only_fields = fields
