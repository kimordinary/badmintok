from rest_framework import serializers
from badmintok.models import BadmintokBanner, Notice
from community.models import Post, PostImage
from accounts.models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 Serializer"""
    class Meta:
        model = CustomUser
        fields = ['id', 'activity_name', 'profile_image']


class PostImageSerializer(serializers.ModelSerializer):
    """게시물 이미지 Serializer"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PostImage
        fields = ['id', 'image_url', 'display_order']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class PostListSerializer(serializers.ModelSerializer):
    """게시물 목록 Serializer"""
    author = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='get_category_display', read_only=True)
    first_image = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'slug', 'title', 'excerpt', 'author', 'category_name',
            'view_count', 'like_count', 'comment_count',
            'created_at', 'updated_at', 'published_at',
            'first_image', 'is_pinned'
        ]

    def get_first_image(self, obj):
        first_image = obj.images.first()
        if first_image:
            return PostImageSerializer(first_image, context=self.context).data
        return None

    def get_excerpt(self, obj):
        return obj.excerpt


class PostDetailSerializer(serializers.ModelSerializer):
    """게시물 상세 Serializer"""
    author = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='get_category_display', read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'slug', 'title', 'content', 'author', 'category_name',
            'view_count', 'like_count', 'comment_count',
            'created_at', 'updated_at', 'published_at',
            'images', 'is_liked', 'is_pinned'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class BannerSerializer(serializers.ModelSerializer):
    """배너 Serializer"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BadmintokBanner
        fields = ['id', 'title', 'image_url', 'link_url', 'display_order', 'is_active']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class NoticeListSerializer(serializers.ModelSerializer):
    """공지사항 목록 Serializer"""
    author = UserSerializer(read_only=True)

    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'author', 'view_count',
            'created_at', 'updated_at', 'is_pinned'
        ]


class NoticeSerializer(serializers.ModelSerializer):
    """공지사항 상세 Serializer"""
    author = UserSerializer(read_only=True)

    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'content', 'author', 'view_count',
            'created_at', 'updated_at', 'is_pinned'
        ]
