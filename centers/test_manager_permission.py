from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from band.models import Band, BandMember

User = get_user_model()


def auth(user):
    return {'HTTP_AUTHORIZATION': 'Bearer ' + str(RefreshToken.for_user(user).access_token)}


class CenterManagerPermissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create(email='owner@example.com', activity_name='owner')
        self.manager = User.objects.create(email='manager@example.com', activity_name='manager')
        self.stranger = User.objects.create(email='stranger@example.com', activity_name='stranger')
        self.staff = User.objects.create(email='staff@example.com', activity_name='staff', is_staff=True)

        self.center = Band.objects.create(
            name='테스트 센터', band_type='center', created_by=self.owner, is_public=True,
        )
        BandMember.objects.create(band=self.center, user=self.owner, role='owner', status='active')
        # 센터 관리자 = role='admin' 멤버로 지정
        BandMember.objects.create(band=self.center, user=self.manager, role='admin', status='active')

    def _patch(self, user):
        return self.client.patch(
            f'/api/centers/{self.center.id}/',
            data={'description': '수정됨'},
            content_type='application/json',
            **auth(user),
        )

    def test_admin_member_can_edit(self):
        r = self._patch(self.manager)
        self.assertEqual(r.status_code, 200)

    def test_owner_can_edit(self):
        self.assertEqual(self._patch(self.owner).status_code, 200)

    def test_site_admin_can_edit(self):
        self.assertEqual(self._patch(self.staff).status_code, 200)

    def test_stranger_forbidden(self):
        self.assertEqual(self._patch(self.stranger).status_code, 403)

    def test_can_manage_flag_in_serializer(self):
        r = self.client.get(f'/api/centers/{self.center.id}/', **auth(self.manager))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['can_manage'])

        r2 = self.client.get(f'/api/centers/{self.center.id}/', **auth(self.stranger))
        self.assertFalse(r2.json()['can_manage'])

    def test_is_managed_by_helper(self):
        self.assertTrue(self.center.is_managed_by(self.manager))
        self.assertTrue(self.center.is_managed_by(self.owner))
        self.assertTrue(self.center.is_managed_by(self.staff))
        self.assertFalse(self.center.is_managed_by(self.stranger))
