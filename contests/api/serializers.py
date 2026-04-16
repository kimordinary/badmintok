from rest_framework import serializers
from django.db.models import Prefetch
from django.utils.text import slugify
from contests.models import Contest, ContestCategory, ContestPrize, ContestSchedule, ContestImage, Sponsor
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
    date = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()
    events_display = serializers.CharField(source='get_events_display', read_only=True)
    age_display = serializers.CharField(source='get_age_display', read_only=True)

    description = serializers.CharField(read_only=True, allow_blank=True)

    class Meta:
        model = ContestSchedule
        fields = ['id', 'date', 'events', 'ages', 'events_display', 'age_display', 'description']
        read_only_fields = fields

    def get_date(self, obj):
        """날짜를 '3/14(토)' 형식으로 반환"""
        if not obj.date:
            return None
        weekdays = ['월', '화', '수', '목', '금', '토', '일']
        return f"{obj.date.month}/{obj.date.day}({weekdays[obj.date.weekday()]})"

    def get_events(self, obj):
        """events를 배열로 반환"""
        return obj.get_events_display() or []


class ContestPrizeSerializer(serializers.ModelSerializer):
    """조별 입상상품 시리얼라이저"""
    class Meta:
        model = ContestPrize
        fields = ['id', 'division', 'first_prize', 'second_prize', 'third_prize']
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
    sponsor = serializers.CharField(source='sponsor.name', read_only=True, allow_null=True)
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
            'region', 'region_detail', 'sponsor',
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
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    sponsor = serializers.CharField(source='sponsor.name', read_only=True, allow_null=True)
    schedules = ContestScheduleSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    registration_period_display = serializers.CharField(source='get_registration_period_display', read_only=True)
    d_day = serializers.IntegerField(source='get_d_day', read_only=True)
    d_day_display = serializers.CharField(source='get_d_day_display', read_only=True)
    is_liked = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    # 앱 호환 필드명
    registration_url = serializers.URLField(source='registration_link', read_only=True)
    registration_office = serializers.CharField(source='registration_name', read_only=True)
    prizes = ContestPrizeSerializer(many=True, read_only=True)
    award_reward_text = serializers.CharField(read_only=True)
    ai_summary = serializers.CharField(source='description', read_only=True)
    participant_info = serializers.SerializerMethodField()
    same_week_contests = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'category', 'category_name', 'is_qualifying',
            'schedule_start', 'schedule_end', 'period_display',
            'registration_start', 'registration_end', 'registration_period_display',
            'region', 'region_detail', 'entry_fee', 'competition_type',
            'sponsor', 'prizes', 'award_reward_text', 'participation_prize',
            'registration_office', 'registration_url', 'registration_link',
            'ai_summary', 'description', 'pdf_url',
            'participant_info', 'participant_target', 'participant_events', 'participant_ages', 'participant_grades',
            'd_day', 'd_day_display',
            'view_count', 'like_count', 'is_liked',
            'schedules', 'images', 'same_week_contests',
            'created_at', 'updated_at'
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

    def get_images(self, obj):
        """이미지 URL 문자열 배열로 반환"""
        request = self.context.get('request')
        urls = []
        for img in obj.images.all():
            if img.image and hasattr(img.image, 'url'):
                if request:
                    urls.append(request.build_absolute_uri(img.image.url))
                else:
                    urls.append(img.image.url)
        return urls

    def get_participant_info(self, obj):
        return {
            'events': obj.participant_events,
            'ages': obj.participant_ages,
            'grades': obj.participant_grades,
        }

    def get_same_week_contests(self, obj):
        """같은 주 대회 목록"""
        if not obj.schedule_start:
            return []
        from datetime import timedelta
        week_start = obj.schedule_start - timedelta(days=obj.schedule_start.weekday())
        week_end = week_start + timedelta(days=6)
        same_week = Contest.objects.filter(
            schedule_start__gte=week_start,
            schedule_start__lte=week_end,
        ).exclude(id=obj.id).select_related('category', 'sponsor').prefetch_related(
            Prefetch('images', queryset=ContestImage.objects.order_by('order'))
        )[:10]
        return ContestListSerializer(same_week, many=True, context=self.context).data


class ContestWriteSerializer(serializers.ModelSerializer):
    """대회 생성/수정 시리얼라이저 (업로더 API 전용)

    - category: 이름(string) 입력 시 매칭, 없으면 null 저장
    - sponsor: 이름(string) 입력 시 get_or_create
    - region: 17개 시도 외 값은 '기타'로 자동 매핑
    """
    category = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    sponsor = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    slug = serializers.SlugField(required=False, allow_unicode=True, max_length=100)

    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'category', 'is_qualifying',
            'schedule_start', 'schedule_end',
            'region', 'region_detail',
            'registration_start', 'registration_end',
            'entry_fee', 'competition_type', 'shuttlecock',
            'sponsor', 'registration_name', 'registration_link',
            'description',
            'participant_target', 'participant_events', 'participant_ages', 'participant_grades',
            'award_reward_text', 'participation_prize', 'raffle_prize',
            'is_test',
        ]
        read_only_fields = ['id']

    def validate_region(self, value):
        valid = {c.value for c in Contest.Region}
        if value not in valid:
            return Contest.Region.ETC.value
        return value

    def _resolve_category(self, name):
        if not name:
            return None
        try:
            return ContestCategory.objects.get(name=name)
        except ContestCategory.DoesNotExist:
            return None

    def _resolve_sponsor(self, name):
        if not name:
            return None
        sponsor, _ = Sponsor.objects.get_or_create(name=name.strip())
        return sponsor

    def create(self, validated_data):
        category_name = validated_data.pop('category', None)
        sponsor_name = validated_data.pop('sponsor', None)
        validated_data['category'] = self._resolve_category(category_name)
        validated_data['sponsor'] = self._resolve_sponsor(sponsor_name)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'category' in validated_data:
            instance.category = self._resolve_category(validated_data.pop('category'))
        if 'sponsor' in validated_data:
            instance.sponsor = self._resolve_sponsor(validated_data.pop('sponsor'))
        return super().update(instance, validated_data)


class ContestImageWriteSerializer(serializers.ModelSerializer):
    """대회 이미지 업로드 시리얼라이저"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ContestImage
        fields = ['id', 'image', 'image_url', 'order']
        extra_kwargs = {'image': {'write_only': True}}

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ContestScheduleWriteSerializer(serializers.ModelSerializer):
    """대회 일정 생성 시리얼라이저"""
    class Meta:
        model = ContestSchedule
        fields = ['id', 'date', 'events', 'ages', 'description']


class ContestPrizeWriteSerializer(serializers.ModelSerializer):
    """대회 조별 입상상품 시리얼라이저"""
    class Meta:
        model = ContestPrize
        fields = ['id', 'division', 'first_prize', 'second_prize', 'third_prize']
