from django.db.models.signals import post_save
from django.dispatch import receiver

from band.models import BandComment
from badmintok.models import Notice
from notifications.models import Notification


@receiver(post_save, sender=BandComment)
def notify_on_band_comment(sender, instance, created, **kwargs):
    """밴드 댓글/답글 생성 시 알림"""
    if not created:
        return

    comment = instance
    post = comment.post
    author = comment.author

    if comment.parent:
        # 답글 → 부모 댓글 작성자에게 알림
        recipient = comment.parent.author
        if recipient == author:
            return
        Notification.objects.create(
            user=recipient,
            type=Notification.Type.REPLY,
            title=f"{author.activity_name}님이 회원님의 댓글에 답글을 남겼습니다.",
            message=comment.content[:100],
            related_band_post=post,
            actor=author,
        )
    else:
        # 댓글 → 게시글 작성자에게 알림
        recipient = post.author
        if recipient == author:
            return
        Notification.objects.create(
            user=recipient,
            type=Notification.Type.COMMENT,
            title=f"{author.activity_name}님이 회원님의 글에 댓글을 남겼습니다.",
            message=comment.content[:100],
            related_band_post=post,
            actor=author,
        )


@receiver(post_save, sender=Notice)
def notify_on_notice(sender, instance, created, **kwargs):
    """공지사항 등록 시 전체 사용자에게 알림"""
    if not created:
        return

    from accounts.models import User

    users = User.objects.filter(is_active=True).exclude(id=instance.author_id)
    notifications = [
        Notification(
            user=user,
            type=Notification.Type.NOTICE,
            title=f"[공지] {instance.title}",
            message="",
            related_notice=instance,
            actor=instance.author,
        )
        for user in users
    ]
    Notification.objects.bulk_create(notifications)
