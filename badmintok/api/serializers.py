from rest_framework import serializers
from badmintok.models import BadmintokBanner, Notice
from community.models import Post
from accounts.api.serializers import UserSerializer
import re


class BannerSerializer(serializers.ModelSerializer):
    """배너 Serializer"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BadmintokBanner
        fields = ['id', 'title', 'image_url', 'link_url', 'alt_text', 'display_order']
        read_only_fields = ['id']
    
    def get_image_url(self, obj):
        """이미지 URL 반환"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class NoticeSerializer(serializers.ModelSerializer):
    """공지사항 Serializer"""
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'content', 'author_name', 
            'is_pinned', 'view_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author_name', 'view_count', 'created_at', 'updated_at']
    
    def get_author_name(self, obj):
        """작성자 이름 반환"""
        return obj.author.activity_name


class NoticeListSerializer(serializers.ModelSerializer):
    """공지사항 목록 Serializer (간단한 정보)"""
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = ['id', 'title', 'author_name', 'is_pinned', 'view_count', 'created_at']
        read_only_fields = ['id', 'author_name', 'view_count', 'created_at']
    
    def get_author_name(self, obj):
        """작성자 이름 반환"""
        return obj.author.activity_name


class PostImageSerializer(serializers.Serializer):
    """게시글 이미지 Serializer"""
    image_url = serializers.SerializerMethodField()
    order = serializers.IntegerField()
    
    def get_image_url(self, obj):
        """이미지 URL 반환"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CategorySerializer(serializers.Serializer):
    """카테고리 Serializer"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()


class PostListSerializer(serializers.ModelSerializer):
    """게시글 목록 Serializer"""
    author_name = serializers.SerializerMethodField()
    author_image_url = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    content_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author_name', 'author_image_url',
            'category_name', 'category_slug', 'thumbnail_url',
            'excerpt', 'content_image_url', 'view_count', 
            'like_count', 'comment_count', 'is_pinned', 
            'created_at', 'published_at'
        ]
        read_only_fields = ['id', 'slug', 'author_name', 'author_image_url',
                           'category_name', 'category_slug', 'view_count',
                           'like_count', 'comment_count', 'created_at']
    
    def get_author_name(self, obj):
        """작성자 이름 반환"""
        return obj.author.activity_name
    
    def get_author_image_url(self, obj):
        """작성자 프로필 이미지 URL 반환"""
        return obj.author.profile_image_url
    
    def get_category_name(self, obj):
        """카테고리 이름 반환"""
        return obj.category.name if obj.category else None
    
    def get_category_slug(self, obj):
        """카테고리 slug 반환"""
        return obj.category.slug if obj.category else None
    
    def get_thumbnail_url(self, obj):
        """썸네일 URL 반환"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_excerpt(self, obj):
        """발췌문 생성 (HTML 태그 제거)"""
        if obj.content:
            clean_text = re.sub(r'<[^>]+>', '', obj.content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            return clean_text[:80] + '...' if len(clean_text) > 80 else clean_text
        return ""
    
    def get_content_image_url(self, obj):
        """본문에서 첫 번째 이미지 URL 추출"""
        if obj.content:
            pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
            match = re.search(pattern, obj.content, re.IGNORECASE)
            if match:
                image_url = match.group(1)
                # 상대 경로인 경우 절대 경로로 변환
                request = self.context.get('request')
                if request and not image_url.startswith('http'):
                    return request.build_absolute_uri(image_url)
                return image_url
        return None


class PostDetailSerializer(serializers.ModelSerializer):
    """게시글 상세 Serializer"""
    author = UserSerializer(read_only=True)
    category_name = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()
    categories = CategorySerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'author',
            'category_name', 'category_slug', 'categories',
            'thumbnail_url', 'images', 'view_count',
            'like_count', 'comment_count', 'is_pinned',
            'is_liked', 'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = ['id', 'slug', 'author', 'view_count',
                           'like_count', 'comment_count', 'created_at',
                           'updated_at']
    
    def get_category_name(self, obj):
        """카테고리 이름 반환"""
        return obj.category.name if obj.category else None
    
    def get_category_slug(self, obj):
        """카테고리 slug 반환"""
        return obj.category.slug if obj.category else None
    
    def get_images(self, obj):
        """게시글 이미지 목록 반환"""
        images = obj.images.all().order_by('order')
        return PostImageSerializer(images, many=True, context=self.context).data
    
    def get_thumbnail_url(self, obj):
        """썸네일 URL 반환"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요 했는지 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

