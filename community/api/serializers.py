from rest_framework import serializers
from community.models import Post, Comment, Category, PostImage
from accounts.api.serializers import UserSerializer


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 Serializer"""
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent']
        read_only_fields = ['id']


class PostImageSerializer(serializers.ModelSerializer):
    """게시글 이미지 Serializer"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PostImage
        fields = ['id', 'image_url', 'order']
        read_only_fields = ['id']
    
    def get_image_url(self, obj):
        """이미지 URL 반환"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CommunityPostListSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 목록 Serializer"""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    content_image_url = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'category', 'categories', 'author',
            'thumbnail_url', 'content_image_url', 'excerpt',
            'view_count', 'like_count', 'comment_count', 'is_pinned',
            'created_at', 'published_at', 'is_liked'
        ]
        read_only_fields = ['id', 'slug', 'view_count', 'like_count', 'comment_count', 'created_at']
    
    def get_thumbnail_url(self, obj):
        """썸네일 이미지 URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_excerpt(self, obj):
        """본문 요약"""
        import re
        if obj.content:
            clean_text = re.sub(r'<[^>]+>', '', obj.content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            return clean_text[:100] + '...' if len(clean_text) > 100 else clean_text
        return ""
    
    def get_content_image_url(self, obj):
        """본문 첫 번째 이미지 URL"""
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class CommunityPostDetailSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 상세 Serializer"""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'category', 'categories', 'author',
            'thumbnail_url', 'thumbnail_alt', 'images',
            'view_count', 'like_count', 'comment_count', 'is_pinned',
            'created_at', 'updated_at', 'published_at', 'is_liked', 'source'
        ]
        read_only_fields = ['id', 'slug', 'view_count', 'like_count', 'comment_count', 'created_at', 'updated_at']
    
    def get_thumbnail_url(self, obj):
        """썸네일 이미지 URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class CommunityPostCreateSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 생성 Serializer"""
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Post
        fields = [
            'title', 'content', 'category_id', 'category_ids',
            'thumbnail', 'thumbnail_alt', 'slug', 'published_at',
            'is_pinned', 'is_draft'
        ]
    
    def create(self, validated_data):
        category_id = validated_data.pop('category_id', None)
        category_ids = validated_data.pop('category_ids', [])
        
        validated_data['author'] = self.context['request'].user
        validated_data['source'] = Post.Source.COMMUNITY
        
        post = Post.objects.create(**validated_data)
        
        # 메인 카테고리 설정
        if category_id:
            try:
                category = Category.objects.get(id=category_id, source=Category.Source.COMMUNITY)
                post.category = category
                post.save()
            except Category.DoesNotExist:
                pass
        
        # 복수 카테고리 설정
        if category_ids:
            categories = Category.objects.filter(id__in=category_ids, source=Category.Source.COMMUNITY)
            post.categories.set(categories)
        
        return post


class CommunityPostUpdateSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 수정 Serializer"""
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Post
        fields = [
            'title', 'content', 'category_id', 'category_ids',
            'thumbnail', 'thumbnail_alt', 'slug', 'published_at',
            'is_pinned', 'is_draft'
        ]
    
    def update(self, instance, validated_data):
        category_id = validated_data.pop('category_id', None)
        category_ids = validated_data.pop('category_ids', None)
        
        # 기본 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 메인 카테고리 업데이트
        if category_id is not None:
            if category_id:
                try:
                    category = Category.objects.get(id=category_id, source=Category.Source.COMMUNITY)
                    instance.category = category
                    instance.save()
                except Category.DoesNotExist:
                    pass
            else:
                instance.category = None
                instance.save()
        
        # 복수 카테고리 업데이트
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids, source=Category.Source.COMMUNITY)
            instance.categories.set(categories)
        
        return instance


class CommentSerializer(serializers.ModelSerializer):
    """댓글 Serializer"""
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'content', 'author', 'parent', 'replies',
            'like_count', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'like_count', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        """대댓글 목록"""
        if hasattr(obj, 'replies_list'):
            return CommentSerializer(obj.replies_list, many=True, context=self.context).data
        return []
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class CommentCreateSerializer(serializers.ModelSerializer):
    """댓글 생성 Serializer"""
    
    class Meta:
        model = Comment
        fields = ['content', 'parent']
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['post'] = self.context['post']
        
        comment = Comment.objects.create(**validated_data)
        
        # 게시글 댓글 수 업데이트
        comment.post.comment_count = comment.post.comments.filter(is_deleted=False).count()
        comment.post.save(update_fields=['comment_count'])
        
        return comment


class CommentUpdateSerializer(serializers.ModelSerializer):
    """댓글 수정 Serializer"""
    
    class Meta:
        model = Comment
        fields = ['content']
