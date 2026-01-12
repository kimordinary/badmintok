from rest_framework import serializers
from band.models import (
    Band, BandMember, BandPost, BandPostImage, BandComment,
    BandPostLike, BandCommentLike
)
from accounts.api.serializers import UserSerializer


class BandListSerializer(serializers.ModelSerializer):
    """밴드 목록 Serializer"""
    created_by = UserSerializer(read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    post_count = serializers.SerializerMethodField()
    category_codes = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    
    class Meta:
        model = Band
        fields = [
            'id', 'name', 'description', 'band_type', 'region',
            'cover_image_url', 'profile_image_url', 'is_public',
            'member_count', 'post_count', 'category_codes',
            'created_by', 'created_at', 'is_member', 'is_approved'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_cover_image_url(self, obj):
        """커버 이미지 URL"""
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None
    
    def get_profile_image_url(self, obj):
        """프로필 이미지 URL"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None
    
    def get_member_count(self, obj):
        """멤버 수"""
        return obj.member_count
    
    def get_post_count(self, obj):
        """게시글 수"""
        return obj.post_count
    
    def get_category_codes(self, obj):
        """카테고리 코드 리스트"""
        return obj.category_codes
    
    def get_is_member(self, obj):
        """현재 사용자가 멤버인지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.members.filter(user=request.user, status=BandMember.Status.ACTIVE).exists()
        return False


class BandDetailSerializer(serializers.ModelSerializer):
    """밴드 상세 Serializer"""
    created_by = UserSerializer(read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    post_count = serializers.SerializerMethodField()
    category_codes = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    member_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Band
        fields = [
            'id', 'name', 'description', 'detailed_description', 'band_type', 'region',
            'cover_image_url', 'profile_image_url', 'is_public', 'join_approval_required',
            'member_count', 'post_count', 'category_codes', 'flash_region_detail',
            'created_by', 'created_at', 'updated_at', 'is_member', 'member_role',
            'is_approved', 'categories'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_cover_image_url(self, obj):
        """커버 이미지 URL"""
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None
    
    def get_profile_image_url(self, obj):
        """프로필 이미지 URL"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None
    
    def get_member_count(self, obj):
        """멤버 수"""
        return obj.member_count
    
    def get_post_count(self, obj):
        """게시글 수"""
        return obj.post_count
    
    def get_category_codes(self, obj):
        """카테고리 코드 리스트"""
        return obj.category_codes
    
    def get_is_member(self, obj):
        """현재 사용자가 멤버인지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.members.filter(user=request.user, status=BandMember.Status.ACTIVE).exists()
        return False
    
    def get_member_role(self, obj):
        """현재 사용자의 멤버 역할"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            member = obj.members.filter(user=request.user, status=BandMember.Status.ACTIVE).first()
            if member:
                return member.role
        return None


class BandCreateSerializer(serializers.ModelSerializer):
    """밴드 생성 Serializer"""
    category_codes = serializers.ListField(
        child=serializers.ChoiceField(choices=['flash', 'group', 'club']),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Band
        fields = [
            'name', 'description', 'detailed_description', 'band_type', 'region',
            'cover_image', 'profile_image', 'is_public', 'join_approval_required',
            'category_codes', 'flash_region_detail', 'categories'
        ]
    
    def create(self, validated_data):
        category_codes = validated_data.pop('category_codes', [])
        categories_str = validated_data.pop('categories', '')
        
        validated_data['created_by'] = self.context['request'].user
        
        # category_codes가 제공된 경우 categories 문자열 생성
        if category_codes:
            validated_data['categories'] = ','.join(category_codes)
        elif categories_str:
            validated_data['categories'] = categories_str
        
        band = Band.objects.create(**validated_data)
        
        # 생성자를 모임장으로 추가
        BandMember.objects.create(
            band=band,
            user=self.context['request'].user,
            role=BandMember.Role.OWNER,
            status=BandMember.Status.ACTIVE
        )
        
        return band


class BandUpdateSerializer(serializers.ModelSerializer):
    """밴드 수정 Serializer"""
    category_codes = serializers.ListField(
        child=serializers.ChoiceField(choices=['flash', 'group', 'club']),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Band
        fields = [
            'name', 'description', 'detailed_description', 'band_type', 'region',
            'cover_image', 'profile_image', 'is_public', 'join_approval_required',
            'category_codes', 'flash_region_detail', 'categories'
        ]
    
    def update(self, instance, validated_data):
        category_codes = validated_data.pop('category_codes', None)
        categories_str = validated_data.pop('categories', None)
        
        # category_codes가 제공된 경우 categories 문자열 생성
        if category_codes is not None:
            validated_data['categories'] = ','.join(category_codes) if category_codes else ''
        elif categories_str is not None:
            validated_data['categories'] = categories_str
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class BandPostImageSerializer(serializers.ModelSerializer):
    """밴드 게시글 이미지 Serializer"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BandPostImage
        fields = ['id', 'image_url', 'order_index']
        read_only_fields = ['id']
    
    def get_image_url(self, obj):
        """이미지 URL 반환"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class BandPostListSerializer(serializers.ModelSerializer):
    """밴드 게시글 목록 Serializer"""
    author = UserSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = BandPost
        fields = [
            'id', 'title', 'content', 'author', 'post_type', 'is_pinned',
            'is_notice', 'view_count', 'like_count', 'comment_count',
            'image_url', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'view_count', 'like_count', 'comment_count', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        """첫 번째 이미지 URL"""
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
            return obj.likes.filter(user=request.user).exists()
        return False


class BandPostDetailSerializer(serializers.ModelSerializer):
    """밴드 게시글 상세 Serializer"""
    author = UserSerializer(read_only=True)
    images = BandPostImageSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = BandPost
        fields = [
            'id', 'title', 'content', 'author', 'post_type', 'is_pinned',
            'is_notice', 'view_count', 'like_count', 'comment_count',
            'images', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'view_count', 'like_count', 'comment_count', 'created_at', 'updated_at']
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class BandPostCreateSerializer(serializers.ModelSerializer):
    """밴드 게시글 생성 Serializer"""
    
    class Meta:
        model = BandPost
        fields = [
            'title', 'content', 'post_type', 'is_pinned', 'is_notice'
        ]
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['band'] = self.context['band']
        return BandPost.objects.create(**validated_data)


class BandPostUpdateSerializer(serializers.ModelSerializer):
    """밴드 게시글 수정 Serializer"""
    
    class Meta:
        model = BandPost
        fields = [
            'title', 'content', 'post_type', 'is_pinned', 'is_notice'
        ]


class BandCommentSerializer(serializers.ModelSerializer):
    """밴드 댓글 Serializer"""
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = BandComment
        fields = [
            'id', 'content', 'author', 'parent', 'replies',
            'like_count', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'like_count', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        """대댓글 목록"""
        if hasattr(obj, 'replies_list'):
            return BandCommentSerializer(obj.replies_list, many=True, context=self.context).data
        return []
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class BandCommentCreateSerializer(serializers.ModelSerializer):
    """밴드 댓글 생성 Serializer"""
    
    class Meta:
        model = BandComment
        fields = ['content', 'parent']
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['post'] = self.context['post']
        return BandComment.objects.create(**validated_data)


class BandCommentUpdateSerializer(serializers.ModelSerializer):
    """밴드 댓글 수정 Serializer"""
    
    class Meta:
        model = BandComment
        fields = ['content']


class BandMemberSerializer(serializers.ModelSerializer):
    """밴드 멤버 Serializer"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = BandMember
        fields = [
            'id', 'user', 'role', 'status', 'joined_at', 'last_visited_at'
        ]
        read_only_fields = ['id', 'joined_at', 'last_visited_at']
