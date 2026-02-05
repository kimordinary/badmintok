from rest_framework import serializers
from contests.models import Contest, ContestCategory, ContestSchedule, ContestImage, Sponsor
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'email', 'activity_name']
        read_only_fields = ['id', 'email', 'activity_name']


class ContestCategorySerializer(serializers.ModelSerializer):
    """대회 분류 시리얼라이저"""
    class Meta:
        model = ContestCategory
        fields = ['id', 'name', 'color', 'description']
        read_only_fields = fields


class SponsorSerializer(serializers.ModelSerializer):
    """스폰서 시리얼라이저"""
    class Meta:
        model = Sponsor
        fields = ['id', 'name']
        read_only_fields = fields


class ContestScheduleSerializer(serializers.ModelSerializer):
    """경기 일정 시리얼라이저"""
    events_display = serializers.CharField(source='get_events_display', read_only=True)
    age_display = serializers.CharField(source='get_age_display', read_only=True)

    class Meta:
        model = ContestSchedule
        fields = ['id', 'date', 'events', 'ages', 'events_display', 'age_display']
        read_only_fields = fields


class ContestImageSerializer(serializers.ModelSerializer):
    """대회 이미지 시리얼라이저"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ContestImage
        fields = ['id', 'image_url', 'order']
        read_only_fields = fields

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ContestListSerializer(serializers.ModelSerializer):
    """대회 목록 시리얼라이저"""
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    registration_period_display = serializers.CharField(source='get_registration_period_display', read_only=True)
    d_day = serializers.IntegerField(source='get_d_day', read_only=True)
    d_day_display = serializers.CharField(source='get_d_day_display', read_only=True)
    is_liked = serializers.SerializerMethodField()
    first_image = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'category_name', 'is_qualifying',
            'schedule_start', 'schedule_end', 'period_display',
            'registration_start', 'registration_end', 'registration_period_display',
            'region', 'region_detail',
            'd_day', 'd_day_display', 'view_count', 'is_liked', 'first_image',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_first_image(self, obj):
        request = self.context.get('request')
        first_image = obj.images.first()
        if first_image and first_image.image:
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None


class ContestDetailSerializer(serializers.ModelSerializer):
    """대회 상세 시리얼라이저"""
    category = ContestCategorySerializer(read_only=True)
    sponsor = SponsorSerializer(read_only=True)
    schedules = ContestScheduleSerializer(many=True, read_only=True)
    images = ContestImageSerializer(many=True, read_only=True)
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    registration_period_display = serializers.CharField(source='get_registration_period_display', read_only=True)
    d_day = serializers.IntegerField(source='get_d_day', read_only=True)
    d_day_display = serializers.CharField(source='get_d_day_display', read_only=True)
    is_liked = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'category', 'is_qualifying',
            'schedule_start', 'schedule_end', 'period_display',
            'registration_start', 'registration_end', 'registration_period_display',
            'region', 'region_detail', 'entry_fee', 'competition_type',
            'sponsor', 'award_reward_text',
            'registration_name', 'registration_link', 'description', 'pdf_url',
            'participant_target', 'participant_events', 'participant_ages', 'participant_grades',
            'd_day', 'd_day_display',
            'view_count', 'like_count', 'is_liked',
            'schedules', 'images', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None

    def get_like_count(self, obj):
        return obj.likes.count()
