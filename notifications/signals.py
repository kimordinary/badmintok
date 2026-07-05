from django.db.models.signals import post_save
from django.dispatch import receiver

from band.models import BandComment, BandSchedule, BandScheduleApplication, BandMember, BandPostLike, BandBookmark
from band.match_models import PartnerRequest
from community.models import Comment as CommunityComment, Post as CommunityPost
from badmintok.models import Notice
from accounts.models import Inquiry
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
        "related_inquiry_id": instance.related_inquiry_id,
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
            related_band=post.band,
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
            related_band=post.band,
            actor=author,
        )


# ─── 공지사항 ───

@receiver(post_save, sender=Notice)
def notify_on_notice(sender, instance, created, **kwargs):
    """공지사항 등록 시 전체 사용자에게 알림"""
    if not created:
        return

    from accounts.models import User

    # 개별 create()로 post_save 시그널을 발화시켜 FCM 푸시 자동 발송
    users = User.objects.filter(is_active=True).exclude(id=instance.author_id)
    for user in users:
        Notification.objects.create(
            user=user,
            type=Notification.Type.NOTICE,
            title=f"[공지] {instance.title}",
            message="",
            related_notice=instance,
            actor=instance.author,
        )


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

    # 개별 create()로 post_save 시그널을 발화시켜 FCM 푸시 자동 발송
    for uid in recipient_ids:
        Notification.objects.create(
            user_id=uid,
            type=Notification.Type.SCHEDULE,
            title=f"[{band.name}] 새 일정: {schedule.title}",
            message="",
            related_band_schedule=schedule,
            related_band=band,
            actor=creator,
        )


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

        # 개별 create()로 post_save 시그널을 발화시켜 FCM 푸시 자동 발송
        for uid in managers:
            Notification.objects.create(
                user_id=uid,
                type=Notification.Type.APPLICATION,
                title=f"{applicant.activity_name}님이 [{schedule.title}]에 참가 신청했습니다.",
                message="",
                related_band_schedule=schedule,
                related_band=band,
                actor=applicant,
            )
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

        # 개별 create()로 post_save 시그널을 발화시켜 FCM 푸시 자동 발송
        for uid in managers:
            Notification.objects.create(
                user_id=uid,
                type=Notification.Type.MEMBERSHIP,
                title=f"{user.activity_name}님이 [{band.name}] 가입을 신청했습니다.",
                message="",
                related_band=band,
                actor=user,
            )

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
        related_band=post.band,
        actor=liker,
    )


# ─── 배드민톡 새 글 (사이트 관리자 칼럼) ───

@receiver(post_save, sender=CommunityPost)
def notify_on_badmintok_post(sender, instance, created, **kwargs):
    """배드민톡 카테고리(source='badmintok') 게시물 등록 시 전체 활성 사용자에게 알림.

    - 동호인톡 등 다른 source는 대상 외
    - 임시저장 / 삭제된 게시물은 대상 외
    - 작성자 본인은 수신자에서 제외
    - WP 매거진 동기화로 생성된 글은 전체 푸시 제외(대량 발송 방지)
    """
    if getattr(instance, "_skip_sync_notify", False):
        return
    if not created:
        return
    if instance.source != CommunityPost.Source.BADMINTOK:
        return
    if instance.is_draft or instance.is_deleted:
        return

    from accounts.models import User
    users = User.objects.filter(is_active=True).exclude(id=instance.author_id)
    for user in users:
        Notification.objects.create(
            user=user,
            type=Notification.Type.BADMINTOK_POST,
            title="📢 배드민톡 새 글",
            message=instance.title,
            related_community_post=instance,
            actor=instance.author,
        )


# ─── 문의 답변 ───

@receiver(post_save, sender=Inquiry)
def notify_on_inquiry_answer(sender, instance, created, **kwargs):
    """문의에 관리자 답변이 등록되면 문의 작성자에게 알림."""
    if created:
        return
    if instance.status != Inquiry.Status.ANSWERED or not instance.admin_response:
        return
    # 같은 문의에 대한 답변 알림이 이미 있으면 중복 발송 방지
    if Notification.objects.filter(
        user_id=instance.user_id,
        type=Notification.Type.INQUIRY,
        related_inquiry=instance,
    ).exists():
        return

    Notification.objects.create(
        user_id=instance.user_id,
        type=Notification.Type.INQUIRY,
        title="문의하신 내용의 답변이 도착했어요",
        message=instance.title,
        related_inquiry=instance,
    )


# ─── 좋아요 (동호인톡 게시글) ───

@receiver(post_save, sender=CommunityPost.likes.through)
def notify_on_community_post_like(sender, instance, created, **kwargs):
    """동호인톡(커뮤니티) 게시글 좋아요 알림"""
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
        related_community_post=post,
        actor=liker,
    )


# ─── 대진(번개 자동 대진) ───
# '다음 경기' 알림은 경기 선수(MatchPlayer)가 모두 채워진 뒤 보내야 하므로
# 시그널이 아니라 band/api/match_views._create_match 에서 직접 생성한다.

@receiver(post_save, sender=PartnerRequest)
def notify_on_partner_request(sender, instance, created, **kwargs):
    """파트너 신청 → 받은 사람에게 / 승인 → 양쪽에게."""
    req = instance
    schedule = req.session.schedule
    band = schedule.band
    from_user = req.from_participant.user
    to_user = req.to_participant.user

    if created:
        Notification.objects.create(
            user=to_user,
            type=Notification.Type.PARTNER_REQUEST,
            title=f"{from_user.activity_name}님이 파트너를 신청했어요",
            message=f"[{band.name}] {schedule.title}",
            related_band_schedule=schedule,
            related_band=band,
            actor=from_user,
        )
        return

    if req.status == PartnerRequest.Status.APPROVED:
        for me, mate in ((from_user, to_user), (to_user, from_user)):
            Notification.objects.create(
                user=me,
                type=Notification.Type.PARTNER_APPROVED,
                title=f"{mate.activity_name}님과 파트너가 됐어요",
                message=f"[{band.name}] {schedule.title} · 이제 같은 팀으로 들어갑니다",
                related_band_schedule=schedule,
                related_band=band,
            )
