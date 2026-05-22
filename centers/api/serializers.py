"""센터 API 시리얼라이저.

내부적으로 Band 모델(band_type='center')을 사용한다.
응답 형식은 기존 Center API와 호환되도록 유지 (앱 영향 없음).
"""
from rest_framework import serializers

from accounts.permissions import is_site_admin
from band.api.serializers import UserSerializer
from band.models import Band, BandBookmark


CENTER_WRITE_FIELDS = [
    "name", "region", "facility_address", "facility_address_detail",
    "facility_phone", "description",
    "facility_operating_hours", "facility_pricing", "facility_court_count", "facility_amenities",
    "facility_latitude", "facility_longitude", "cover_image", "profile_image",
]


class CenterSerializer(serializers.ModelSerializer):
    """배드민턴 센터 응답 (Band 모델 기반).

    필드명은 기존 Center API와 호환되도록 alias 처리.
    """
    region_display = serializers.CharField(source="get_region_display", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    can_manage = serializers.SerializerMethodField()
    is_site_admin = serializers.SerializerMethodField()

    # Band 모델 필드 → Center API 필드명 alias
    address = serializers.CharField(source="facility_address", read_only=True)
    address_detail = serializers.CharField(source="facility_address_detail", read_only=True)
    phone = serializers.CharField(source="facility_phone", read_only=True)
    operating_hours = serializers.CharField(source="facility_operating_hours", read_only=True)
    pricing = serializers.CharField(source="facility_pricing", read_only=True)
    court_count = serializers.IntegerField(source="facility_court_count", read_only=True)
    amenities = serializers.CharField(source="facility_amenities", read_only=True)
    latitude = serializers.FloatField(source="facility_latitude", read_only=True)
    longitude = serializers.FloatField(source="facility_longitude", read_only=True)

    class Meta:
        model = Band
        fields = [
            "id", "name", "region", "region_display",
            "address", "address_detail", "phone", "description",
            "operating_hours", "pricing", "court_count", "amenities",
            "cover_image_url", "profile_image_url", "latitude", "longitude",
            "bookmark_count", "is_bookmarked",
            "created_by", "can_manage", "is_site_admin",
            "created_at",
        ]
        read_only_fields = fields

    def get_cover_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image and hasattr(obj.cover_image, "url"):
            url = obj.cover_image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_profile_image_url(self, obj):
        request = self.context.get("request")
        if obj.profile_image and hasattr(obj.profile_image, "url"):
            url = obj.profile_image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_bookmark_count(self, obj):
        if hasattr(obj, "bookmark_count_annotated"):
            return obj.bookmark_count_annotated
        return obj.bookmarks.count()

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return BandBookmark.objects.filter(band=obj, user=request.user).exists()

    def get_can_manage(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if is_site_admin(request.user):
            return True
        return obj.created_by_id == request.user.id

    def get_is_site_admin(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return is_site_admin(request.user)


class CenterWriteSerializer(serializers.ModelSerializer):
    """센터 등록/수정 입력 (외부 API 입력 필드는 Center 시절 그대로).

    내부적으로는 Band 모델에 저장.
    """
    # 입력 필드명은 외부 호환을 위해 Center 시절 그대로 (address, phone, court_count 등)
    address = serializers.CharField(source="facility_address", required=True, allow_blank=False)
    address_detail = serializers.CharField(source="facility_address_detail", required=False, allow_blank=True)
    phone = serializers.CharField(source="facility_phone", required=False, allow_blank=True)
    operating_hours = serializers.CharField(source="facility_operating_hours", required=False, allow_blank=True)
    pricing = serializers.CharField(source="facility_pricing", required=False, allow_blank=True)
    court_count = serializers.IntegerField(source="facility_court_count", required=False)
    amenities = serializers.CharField(source="facility_amenities", required=False, allow_blank=True)
    latitude = serializers.FloatField(source="facility_latitude", required=False)
    longitude = serializers.FloatField(source="facility_longitude", required=False)

    # 등록자(담당자)가 운영진에게 남기는 연락처 — 운영진 admin에서만 확인
    applicant_contact_phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Band
        fields = [
            "name", "description", "region",
            "address", "address_detail", "phone",
            "operating_hours", "pricing", "court_count", "amenities",
            "latitude", "longitude", "cover_image", "profile_image",
            "applicant_contact_phone",
        ]
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "region": {"required": True},
            "description": {"required": False, "allow_blank": True},
        }
