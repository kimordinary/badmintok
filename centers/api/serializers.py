from rest_framework import serializers

from accounts.permissions import is_site_admin
from band.api.serializers import UserSerializer
from centers.models import Center, CenterBookmark


CENTER_WRITE_FIELDS = [
    "name", "region", "address", "address_detail",
    "phone", "description",
    "operating_hours", "pricing", "court_count", "amenities",
    "latitude", "longitude", "cover_image",
]


class CenterSerializer(serializers.ModelSerializer):
    """배드민턴 센터 시리얼라이저 (목록/상세 공용)."""
    region_display = serializers.CharField(source="get_region_display", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    can_manage = serializers.SerializerMethodField()
    is_site_admin = serializers.SerializerMethodField()

    class Meta:
        model = Center
        fields = [
            "id", "name", "region", "region_display",
            "address", "address_detail", "phone", "description",
            "operating_hours", "pricing", "court_count", "amenities",
            "cover_image_url", "latitude", "longitude",
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

    def get_bookmark_count(self, obj):
        if hasattr(obj, "bookmark_count_annotated"):
            return obj.bookmark_count_annotated
        return obj.bookmarks.count()

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return CenterBookmark.objects.filter(center=obj, user=request.user).exists()

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
    """센터 등록/수정 시리얼라이저 (POST / PATCH 공용)."""

    class Meta:
        model = Center
        fields = CENTER_WRITE_FIELDS
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "region": {"required": True},
            "address": {"required": True, "allow_blank": False},
        }
