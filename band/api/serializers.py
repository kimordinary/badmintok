from rest_framework import serializers
from band.models import (
    Band, BandMember, BandPost, BandPostImage, BandComment,
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


class BandPostDetailSerializer(serializers.ModelSerializer):
    """밴드 게시글 상세 시리얼라이저"""
    author = UserSerializer(read_only=True)
    band_name = serializers.CharField(source='band.name', read_only=True)
    images = BandPostImageSerializer(many=True, read_only=True)

    class Meta:
        model = BandPost
        fields = [
            'id', 'band', 'band_name', 'author', 'title', 'content',
            'post_type', 'is_pinned', 'is_notice', 'view_count',
            'like_count', 'comment_count', 'images',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class BandScheduleImageSerializer(serializers.ModelSerializer):
    """일정 이미지 시리얼라이저"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BandScheduleImage
        fields = ['id', 'image_url', 'order_index']
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

    class Meta:
        model = BandSchedule
        fields = [
            'id', 'band', 'band_name', 'title', 'description',
            'start_datetime', 'end_datetime', 'location',
            'max_participants', 'current_participants',
            'requires_approval', 'application_deadline',
            'bank_account', 'is_closed', 'created_by',
            'images', 'is_full', 'is_applied',
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
