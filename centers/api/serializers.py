from rest_framework import serializers

from centers.models import Center, CenterBookmark


class CenterSerializer(serializers.ModelSerializer):
    """배드민턴 센터 시리얼라이저 (목록/상세 공용)."""
    region_display = serializers.CharField(source="get_region_display", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Center
        fields = [
            "id", "name", "region", "region_display",
            "address", "phone", "description",
            "operating_hours", "pricing", "court_count", "amenities",
            "cover_image_url", "latitude", "longitude",
            "bookmark_count", "is_bookmarked",
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
        # annotated 값 우선 (목록 쿼리에서 prefetch로 주입)
        if hasattr(obj, "bookmark_count_annotated"):
            return obj.bookmark_count_annotated
        return obj.bookmarks.count()

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return CenterBookmark.objects.filter(center=obj, user=request.user).exists()
