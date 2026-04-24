def is_site_admin(user):
    """사이트 관리자 여부. 모임/동호회 운영에 한해 owner와 동급으로 취급."""
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_staff or user.is_superuser)
