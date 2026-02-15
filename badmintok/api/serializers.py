from rest_framework import serializers
from badmintok.models import BadmintokBanner, Banner, Notice
from community.models import Post, PostImage
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 Serializer"""
    class Meta:
        model = User
        fields = ['id', 'activity_name', 'email']


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
    is_liked = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author', 'category_name', 'source',
            'created_at', 'updated_at', 'view_count', 'like_count', 'comment_count',
            'is_pinned', 'first_image', 'excerpt', 'is_liked', 'thumbnail_url'
        ]

    def get_first_image(self, obj):
        request = self.context.get('request')
        first_image = obj.images.first()
        if first_image and first_image.image:
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        # HTML 콘텐츠에서 첫 번째 이미지 URL 추출
        if obj.content:
            import re
            match = re.search(r'<img\s+[^>]*src="([^"]*)"', obj.content)
            if match:
                img_url = match.group(1)
                if request and img_url.startswith('/'):
                    return request.build_absolute_uri(img_url)
                return img_url
        return None

    def get_excerpt(self, obj):
        """본문에서 발췌문 생성 (100자)"""
        if obj.content:
            import re, json
            content = obj.content.strip()
            # Editor.js JSON 형식인 경우 텍스트 추출
            if content.startswith('{') and '"blocks"' in content:
                try:
                    data = json.loads(content)
                    blocks = data.get('blocks', [])
                    parts = []
                    for block in blocks:
                        btype = block.get('type', '')
                        bdata = block.get('data', {})
                        if btype in ('paragraph', 'header', 'h2', 'h3', 'h4', 'quote'):
                            t = re.sub(r'<[^>]+>', '', bdata.get('text', '')).replace('&nbsp;', ' ').strip()
                            if t:
                                parts.append(t)
                        elif btype == 'list':
                            for item in bdata.get('items', []):
                                t = re.sub(r'<[^>]+>', '', str(item)).strip()
                                if t:
                                    parts.append(t)
                    text = ' '.join(parts)
                except (json.JSONDecodeError, KeyError):
                    text = re.sub(r'<[^>]+>', '', content)
            else:
                text = re.sub(r'<[^>]+>', '', content)
            text = text.strip()
            return text[:100] + '...' if len(text) > 100 else text
        return ''

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


class PostDetailSerializer(serializers.ModelSerializer):
    """게시물 상세 Serializer"""
    author = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='get_category_display', read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'author', 'category_name',
            'source', 'created_at', 'updated_at',
            'view_count', 'like_count', 'comment_count', 'is_pinned',
            'published_at', 'images', 'is_liked', 'thumbnail_url'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


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


class AppBannerSerializer(serializers.ModelSerializer):
    """앱/웹 메인 배너 Serializer"""
    mobile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ['id', 'title', 'mobile_image_url', 'link_url', 'order']

    def get_mobile_image_url(self, obj):
        request = self.context.get('request')
        if obj.mobile_image and hasattr(obj.mobile_image, 'url'):
            if request:
                return request.build_absolute_uri(obj.mobile_image.url)
            return obj.mobile_image.url
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
