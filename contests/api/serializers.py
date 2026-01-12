from rest_framework import serializers
from contests.models import Contest, ContestCategory, ContestSchedule, ContestImage, Sponsor
from accounts.api.serializers import UserSerializer


class ContestCategorySerializer(serializers.ModelSerializer):
    """대회 분류 Serializer"""
    
    class Meta:
        model = ContestCategory
        fields = ['id', 'name', 'color', 'description']
        read_only_fields = ['id']


class SponsorSerializer(serializers.ModelSerializer):
    """스폰서 Serializer"""
    
    class Meta:
        model = Sponsor
        fields = ['id', 'name']
        read_only_fields = ['id']


class ContestImageSerializer(serializers.ModelSerializer):
    """대회 이미지 Serializer"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ContestImage
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


class ContestScheduleSerializer(serializers.ModelSerializer):
    """대회 일정 Serializer"""
    events_display = serializers.SerializerMethodField()
    age_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ContestSchedule
        fields = [
            'id', 'date', 'events', 'ages', 'events_display', 'age_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_events_display(self, obj):
        """경기 종목 표시"""
        return obj.get_events_display()
    
    def get_age_display(self, obj):
        """연령대 표시"""
        return obj.get_age_display()


class ContestListSerializer(serializers.ModelSerializer):
    """대회 목록 Serializer"""
    category = ContestCategorySerializer(read_only=True)
    sponsor = SponsorSerializer(read_only=True)
    period_display = serializers.SerializerMethodField()
    registration_period_display = serializers.SerializerMethodField()
    d_day_display = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    thumbnail_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'slug', 'category', 'is_qualifying', 'schedule_start', 'schedule_end',
            'region', 'region_detail', 'period_display', 'registration_start', 'registration_end',
            'registration_period_display', 'd_day_display', 'location_display',
            'sponsor', 'like_count', 'is_liked', 'thumbnail_image_url', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']
    
    def get_period_display(self, obj):
        """대회 기간 표시"""
        return obj.get_period_display()
    
    def get_registration_period_display(self, obj):
        """접수 기간 표시"""
        return obj.get_registration_period_display()
    
    def get_d_day_display(self, obj):
        """D-day 표시"""
        return obj.get_d_day_display()
    
    def get_location_display(self, obj):
        """장소 표시"""
        return obj.get_location_display()
    
    def get_like_count(self, obj):
        """좋아요 개수"""
        return obj.like_count
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False
    
    def get_thumbnail_image_url(self, obj):
        """첫 번째 이미지 URL (썸네일)"""
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None


class ContestDetailSerializer(serializers.ModelSerializer):
    """대회 상세 Serializer"""
    category = ContestCategorySerializer(read_only=True)
    sponsor = SponsorSerializer(read_only=True)
    schedules = ContestScheduleSerializer(many=True, read_only=True)
    images = ContestImageSerializer(many=True, read_only=True)
    period_display = serializers.SerializerMethodField()
    registration_period_display = serializers.SerializerMethodField()
    d_day_display = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'slug', 'category', 'is_qualifying', 'schedule_start', 'schedule_end',
            'region', 'region_detail', 'event_division', 'period_display',
            'registration_start', 'registration_end', 'registration_period_display',
            'entry_fee', 'competition_type', 'participant_reward', 'sponsor',
            'award_reward', 'award_reward_text', 'registration_name', 'registration_link',
            'description', 'participant_target', 'd_day_display', 'location_display',
            'schedules', 'images', 'like_count', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def get_period_display(self, obj):
        """대회 기간 표시"""
        return obj.get_period_display()
    
    def get_registration_period_display(self, obj):
        """접수 기간 표시"""
        return obj.get_registration_period_display()
    
    def get_d_day_display(self, obj):
        """D-day 표시"""
        return obj.get_d_day_display()
    
    def get_location_display(self, obj):
        """장소 표시"""
        return obj.get_location_display()
    
    def get_like_count(self, obj):
        """좋아요 개수"""
        return obj.like_count
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False
