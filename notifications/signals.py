from django.db.models.signals import post_save
from django.dispatch import receiver

from band.models import BandComment, BandSchedule, BandScheduleApplication, BandMember, BandPostLike, BandBookmark
from community.models import Comment as CommunityComment
from badmintok.models import Notice
from notifications.models import Notification


# ─── FCM 푸시 자동 발송 ───
@receiver(post_save, sender=Notification)
def send_fcm_on_notification(sender, instance, created, **kwargs):
    """Notification 생성 시점마다 FCM 푸시 자동 발송.

    - 토큰이 없거나 Firebase 미설정이면 silent no-op
    - 알림 데이터에 type/notification_id/related_* id를 함께 실어 앱 라우팅용으로 사용
    """
    if not created:
        return
    from notifications.push import send_to_user

    data = {
        "type": instance.type,
        "notification_id": instance.id,
        "related_band_id": instance.related_band_id,
        "related_band_schedule_id": instance.related_band_schedule_id,
        "related_band_post_id": instance.related_band_post_id,
        "related_community_post_id": instance.related_community_post_id,
        "related_notice_id": instance.related_notice_id,
    }
    send_to_user(
        instance.user_id,
        title=instance.title,
        body=instance.message or "",
        data=data,
    )


# ─── 밴드 댓글/답글 ───

@receiver(post_save, sender=BandComment)
def notify_on_band_comment(sender, instance, created, **kwargs):
    """밴드 댓글/답글 생성 시 알림"""
    if not created:
        return

    comment = instance
    post = comment.post
    author = comment.author

    if comment.parent:
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


# ─── 공지사항 ───

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


# ─── 번개/일정 등록 ───

@receiver(post_save, sender=BandSchedule)
def notify_on_schedule_created(sender, instance, created, **kwargs):
    """번개/일정 등록 시 북마크한 사용자에게 알림"""
    if not created:
        return

    schedule = instance
    band = schedule.band
    creator = schedule.created_by

    # 해당 모임을 북마크한 사용자 + 활성 멤버
    bookmark_user_ids = BandBookmark.objects.filter(band=band).values_list('user_id', flat=True)
    member_user_ids = BandMember.objects.filter(band=band, status='active').values_list('user_id', flat=True)
    recipient_ids = set(bookmark_user_ids) | set(member_user_ids)
    recipient_ids.discard(creator.id)

    if not recipient_ids:
        return

    notifications = [
        Notification(
            user_id=uid,
            type=Notification.Type.SCHEDULE,
            title=f"[{band.name}] 새 일정: {schedule.title}",
            message="",
            related_band_schedule=schedule,
            related_band=band,
            actor=creator,
        )
        for uid in recipient_ids
    ]
    Notification.objects.bulk_create(notifications)


# ─── 일정 참가 신청/승인/거절 ───

@receiver(post_save, sender=BandScheduleApplication)
def notify_on_schedule_application(sender, instance, created, **kwargs):
    """일정 참가 신청/승인/거절 알림"""
    app = instance
    schedule = app.schedule
    band = schedule.band
    applicant = app.user

    if created:
        # 참가 신청 → 모임장/관리자에게 알림
        managers = BandMember.objects.filter(
            band=band, role__in=['owner', 'admin'], status='active'
        ).exclude(user=applicant).values_list('user_id', flat=True)

        notifications = [
            Notification(
                user_id=uid,
                type=Notification.Type.APPLICATION,
                title=f"{applicant.activity_name}님이 [{schedule.title}]에 참가 신청했습니다.",
                message="",
                related_band_schedule=schedule,
                related_band=band,
                actor=applicant,
            )
            for uid in managers
        ]
        Notification.objects.bulk_create(notifications)
    else:
        # 승인/거절 → 신청자에게 알림
        if app.status == 'approved':
            Notification.objects.create(
                user=applicant,
                type=Notification.Type.APPLICATION,
                title=f"[{band.name}] {schedule.title} 참가가 승인되었습니다.",
                message="",
                related_band_schedule=schedule,
                related_band=band,
                actor=app.reviewed_by,
            )
        elif app.status == 'rejected':
            Notification.objects.create(
                user=applicant,
                type=Notification.Type.APPLICATION,
                title=f"[{band.name}] {schedule.title} 참가가 거절되었습니다.",
                message=app.rejection_reason or "",
                related_band_schedule=schedule,
                related_band=band,
                actor=app.reviewed_by,
            )


# ─── 모임 가입 신청/승인 ───

@receiver(post_save, sender=BandMember)
def notify_on_membership(sender, instance, created, **kwargs):
    """모임 가입 신청/승인 알림"""
    member = instance
    band = member.band
    user = member.user

    if created and member.status == 'pending':
        # 가입 신청 → 모임장/관리자에게 알림
        managers = BandMember.objects.filter(
            band=band, role__in=['owner', 'admin'], status='active'
        ).exclude(user=user).values_list('user_id', flat=True)

        notifications = [
            Notification(
                user_id=uid,
                type=Notification.Type.MEMBERSHIP,
                title=f"{user.activity_name}님이 [{band.name}] 가입을 신청했습니다.",
                message="",
                related_band=band,
                actor=user,
            )
            for uid in managers
        ]
        Notification.objects.bulk_create(notifications)

    elif not created and member.status == 'active':
        # 승인 → 신청자에게 알림
        Notification.objects.create(
            user=user,
            type=Notification.Type.MEMBERSHIP,
            title=f"[{band.name}] 가입이 승인되었습니다.",
            message="",
            related_band=band,
        )


# ─── 커뮤니티(배드민톡) 댓글/답글 ───

@receiver(post_save, sender=CommunityComment)
def notify_on_community_comment(sender, instance, created, **kwargs):
    """커뮤니티 댓글/답글 생성 시 알림"""
    if not created:
        return

    comment = instance
    post = comment.post
    author = comment.author

    if comment.parent:
        recipient = comment.parent.author
        if recipient == author:
            return
        Notification.objects.create(
            user=recipient,
            type=Notification.Type.REPLY,
            title=f"{author.activity_name}님이 회원님의 댓글에 답글을 남겼습니다.",
            message=comment.content[:100],
            related_community_post=post,
            actor=author,
        )
    else:
        recipient = post.author
        if recipient == author:
            return
        Notification.objects.create(
            user=recipient,
            type=Notification.Type.COMMENT,
            title=f"{author.activity_name}님이 회원님의 글에 댓글을 남겼습니다.",
            message=comment.content[:100],
            related_community_post=post,
            actor=author,
        )


# ─── 좋아요 (밴드 게시글) ───

@receiver(post_save, sender=BandPostLike)
def notify_on_band_post_like(sender, instance, created, **kwargs):
    """밴드 게시글 좋아요 알림"""
    if not created:
        return

    post = instance.post
    liker = instance.user
    recipient = post.author

    if recipient == liker:
        return

    Notification.objects.create(
        user=recipient,
        type=Notification.Type.LIKE,
        title=f"{liker.activity_name}님이 회원님의 글을 좋아합니다.",
        message=post.title[:100],
        related_band_post=post,
        actor=liker,
    )
