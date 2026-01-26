from rest_framework import serializers
from django.utils import timezone
from community.models import Post, Comment, Category, PostImage
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'email', 'activity_name']
        read_only_fields = ['id', 'email', 'activity_name']


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 시리얼라이저"""
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)
    full_path = serializers.CharField(source='get_full_path', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'source', 'parent', 'parent_name', 'full_path', 'display_order', 'is_active']
        read_only_fields = ['id']


class PostImageSerializer(serializers.ModelSerializer):
    """게시글 이미지 시리얼라이저"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PostImage
        fields = ['id', 'image_url', 'order']
        read_only_fields = ['id']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CommunityPostListSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 목록 시리얼라이저"""
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
        read_only_fields = fields

    def get_first_image(self, obj):
        request = self.context.get('request')
        first_image = obj.images.first()
        if first_image and first_image.image:
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None

    def get_excerpt(self, obj):
        """본문에서 발췌문 생성 (100자)"""
        if obj.content:
            # HTML 태그 제거
            import re
            text = re.sub(r'<[^>]+>', '', obj.content)
            text = text.strip()
            return text[:100] + '...' if len(text) > 100 else text
        return ''

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지 확인"""
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


class CommunityPostDetailSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 상세 시리얼라이저"""
    author = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='get_category_display', read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    categories_list = CategorySerializer(source='categories', many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'author', 'category', 'category_name',
            'categories_list', 'source', 'created_at', 'updated_at',
            'view_count', 'like_count', 'comment_count', 'is_pinned', 'is_draft',
            'published_at', 'images', 'is_liked', 'thumbnail_url', 'thumbnail_alt',
            'focus_keyword', 'meta_description'
        ]
        read_only_fields = fields

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지 확인"""
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


class CommunityPostCreateSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 생성 시리얼라이저"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Post
        fields = [
            'title', 'content', 'category', 'category_ids', 'source',
            'is_draft', 'published_at', 'images', 'thumbnail', 'thumbnail_alt',
            'focus_keyword', 'meta_description'
        ]

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        category_ids = validated_data.pop('category_ids', [])

        # 작성자 설정
        request = self.context.get('request')
        validated_data['author'] = request.user

        # source가 없으면 기본값 설정
        if 'source' not in validated_data:
            validated_data['source'] = Post.Source.COMMUNITY

        # 게시글 생성
        post = Post.objects.create(**validated_data)

        # 슬러그 생성
        if not post.slug:
            post.slug = post.generate_slug()
            post.save(update_fields=['slug'])

        # 카테고리 설정
        if category_ids:
            categories = Category.objects.filter(id__in=category_ids)
            post.categories.set(categories)

        # 이미지 추가
        for idx, image in enumerate(images):
            PostImage.objects.create(post=post, image=image, order=idx)

        return post


class CommunityPostUpdateSerializer(serializers.ModelSerializer):
    """동호인톡 게시글 수정 시리얼라이저"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Post
        fields = [
            'title', 'content', 'category', 'category_ids',
            'is_draft', 'published_at', 'images', 'thumbnail', 'thumbnail_alt',
            'focus_keyword', 'meta_description'
        ]

    def update(self, instance, validated_data):
        images = validated_data.pop('images', None)
        category_ids = validated_data.pop('category_ids', None)

        # 기본 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # 카테고리 업데이트
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids)
            instance.categories.set(categories)

        # 이미지 업데이트 (기존 이미지 삭제 후 새로 추가)
        if images is not None:
            instance.images.all().delete()
            for idx, image in enumerate(images):
                PostImage.objects.create(post=instance, image=image, order=idx)

        return instance


class CommentSerializer(serializers.ModelSerializer):
    """댓글 시리얼라이저"""
    author = UserSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'parent', 'content',
            'created_at', 'updated_at', 'like_count', 'is_liked', 'replies'
        ]
        read_only_fields = ['id', 'post', 'author', 'created_at', 'updated_at', 'like_count']

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_replies(self, obj):
        """대댓글 목록"""
        if hasattr(obj, 'replies_list'):
            # views.py에서 prefetch한 replies_list 사용
            replies = obj.replies_list
        else:
            replies = obj.replies.filter(is_deleted=False).order_by('created_at')

        # 재귀 호출하지 않고 한 레벨만 직렬화
        return CommentSerializer(replies, many=True, context=self.context).data


class CommentCreateSerializer(serializers.ModelSerializer):
    """댓글 생성 시리얼라이저"""
    parent_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Comment
        fields = ['content', 'parent_id']

    def create(self, validated_data):
        parent_id = validated_data.pop('parent_id', None)

        # 작성자 및 게시글 설정
        request = self.context.get('request')
        post = self.context.get('post')

        validated_data['author'] = request.user
        validated_data['post'] = post

        # 부모 댓글 설정
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id, is_deleted=False)
                validated_data['parent'] = parent
            except Comment.DoesNotExist:
                raise serializers.ValidationError({'parent_id': '존재하지 않는 댓글입니다.'})

        comment = Comment.objects.create(**validated_data)

        # 게시글 댓글 수 업데이트
        post.update_comment_count()

        return comment


class CommentUpdateSerializer(serializers.ModelSerializer):
    """댓글 수정 시리얼라이저"""

    class Meta:
        model = Comment
        fields = ['content']

    def update(self, instance, validated_data):
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance
