from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    actor_name = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "type_display",
            "title",
            "message",
            "actor_name",
            "link",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.activity_name or obj.actor.email
        return None

    def get_link(self, obj):
        """앱에서 이동할 딥링크 정보"""
        if obj.related_band_post:
            return {
                "type": "band_post",
                "band_id": obj.related_band_post.band_id,
                "post_id": obj.related_band_post.id,
            }
        if obj.related_band_schedule:
            return {
                "type": "band_schedule",
                "band_id": obj.related_band_schedule.band_id,
                "schedule_id": obj.related_band_schedule.id,
            }
        if obj.related_band:
            return {
                "type": "band",
                "band_id": obj.related_band.id,
            }
        if obj.related_community_post:
            return {
                "type": "community_post",
                "post_id": obj.related_community_post.id,
                "slug": obj.related_community_post.slug,
            }
        if obj.related_notice:
            return {
                "type": "notice",
                "notice_id": obj.related_notice.id,
            }
        return None
