"""FCM 푸시 알림 발송 유틸.

Firebase Admin SDK를 lazy-init 방식으로 초기화한다.
- FIREBASE_CREDENTIALS_PATH 가 가리키는 JSON 파일이 없거나 firebase_admin
  패키지가 설치되어 있지 않으면 발송은 silent no-op 처리되어 서버 정상 동작에는
  영향을 주지 않는다.
- 발송 실패 시 invalid 토큰은 자동 비활성화하여 다음 발송 사이클에서 제외된다.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

from django.conf import settings

logger = logging.getLogger(__name__)

_initialized = False
_messaging = None


def _init_firebase():
    """첫 호출 시점에 Firebase Admin SDK를 초기화한다."""
    global _initialized, _messaging
    if _initialized:
        return

    _initialized = True

    cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
    if not cred_path or not os.path.exists(cred_path):
        logger.info("FCM 비활성: 서비스 계정 JSON(%s)이 존재하지 않음", cred_path)
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except ImportError:
        logger.warning("FCM 비활성: firebase-admin 패키지가 설치되어 있지 않음")
        return

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        _messaging = messaging
        logger.info("FCM 초기화 완료")
    except Exception as exc:
        logger.exception("FCM 초기화 실패: %s", exc)
        _messaging = None


def _active_tokens(user_ids: Iterable[int]) -> list[tuple[int, str]]:
    """주어진 user_id 들에 대해 활성 디바이스 토큰을 (user_id, token) 튜플로 반환."""
    from notifications.models import DeviceToken

    qs = DeviceToken.objects.filter(
        user_id__in=list(user_ids), is_active=True
    ).values_list("token", "user_id")
    return [(uid, tok) for tok, uid in qs]


def send_to_user(user_id: int, *, title: str, body: str = "", data: dict | None = None) -> int:
    """특정 사용자에게 푸시 발송. 발송된 토큰 수 반환."""
    return send_to_users([user_id], title=title, body=body, data=data)


def send_to_users(
    user_ids: Iterable[int],
    *,
    title: str,
    body: str = "",
    data: dict | None = None,
) -> int:
    """여러 사용자에게 푸시 발송. 토큰 단위로 send_each 호출.

    반환값: 성공적으로 발송된 토큰 수.
    """
    _init_firebase()
    if _messaging is None:
        return 0

    rows = _active_tokens(user_ids)
    if not rows:
        return 0

    # FCM data payload는 모든 값이 문자열이어야 한다.
    data_payload = {k: str(v) for k, v in (data or {}).items() if v is not None}

    messages = []
    token_list = []
    for _uid, token in rows:
        token_list.append(token)
        messages.append(
            _messaging.Message(
                token=token,
                notification=_messaging.Notification(title=title, body=body or None),
                data=data_payload or None,
            )
        )

    try:
        response = _messaging.send_each(messages)
    except Exception as exc:
        logger.exception("FCM 발송 중 예외: %s", exc)
        return 0

    invalid_tokens: list[str] = []
    success = 0
    for idx, resp in enumerate(response.responses):
        if resp.success:
            success += 1
        else:
            err_code = getattr(getattr(resp, "exception", None), "code", "")
            if err_code in ("registration-token-not-registered", "invalid-argument", "invalid-registration-token"):
                invalid_tokens.append(token_list[idx])
            else:
                logger.warning("FCM 발송 실패 (%s): %s", token_list[idx][:16], resp.exception)

    if invalid_tokens:
        from notifications.models import DeviceToken
        DeviceToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
        logger.info("FCM invalid 토큰 %d개 비활성화", len(invalid_tokens))

    return success
