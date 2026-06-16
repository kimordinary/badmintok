from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestSchedule, ContestPrize

User = get_user_model()


def auth(user):
    return {'HTTP_AUTHORIZATION': 'Bearer ' + str(RefreshToken.for_user(user).access_token)}


class ContestDeleteAPITests(TestCase):
    def setUp(self):
        self.bot = User.objects.create(email='uploader-bot@badmintok.com', is_staff=True)
        self.public = User.objects.create(email='normal@example.com', is_staff=False)

    def _make(self, slug):
        c = Contest.objects.create(title=f'대회-{slug}', slug=slug, schedule_start='2026-07-01')
        ContestSchedule.objects.create(contest=c, date='2026-07-01')
        ContestPrize.objects.create(contest=c, division='A조')
        return c

    def test_public_cannot_delete(self):
        self._make('dup-x')
        r = self.client.delete('/api/contests/dup-x/', **auth(self.public))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Contest.objects.filter(slug='dup-x').exists())

    def test_missing_slug_returns_404(self):
        r = self.client.delete('/api/contests/no-such/', **auth(self.bot))
        self.assertEqual(r.status_code, 404)

    def test_bot_delete_detail_cascades(self):
        c = self._make('dup-y')
        r = self.client.delete('/api/contests/dup-y/', **auth(self.bot))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'ok': True, 'deleted': True, 'slug': 'dup-y'})
        self.assertFalse(Contest.objects.filter(slug='dup-y').exists())
        self.assertEqual(ContestSchedule.objects.filter(contest_id=c.id).count(), 0)
        self.assertEqual(ContestPrize.objects.filter(contest_id=c.id).count(), 0)

    def test_bot_delete_via_post_path(self):
        self._make('dup-z')
        r = self.client.post('/api/contests/dup-z/delete/', **auth(self.bot))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Contest.objects.filter(slug='dup-z').exists())

    def test_post_delete_forbidden_for_public(self):
        self._make('dup-w')
        r = self.client.post('/api/contests/dup-w/delete/', **auth(self.public))
        self.assertEqual(r.status_code, 403)

    def test_options_allows_delete(self):
        self._make('dup-opt')
        r = self.client.options('/api/contests/dup-opt/')
        self.assertIn('DELETE', r.get('Allow', ''))
