import base64
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.api.serializers import ContestListSerializer
from contests.models import Contest, ContestImage


class ContestImageRoleTests(TestCase):
    def setUp(self):
        self.contest = Contest.objects.create(
            title="이미지 역할 테스트 대회",
            slug="image-role-test",
            schedule_start=date(2026, 11, 22),
        )
        self.guide = ContestImage.objects.create(
            contest=self.contest,
            image="contest_images/guide-page.webp",
            order=0,
            image_type=ContestImage.ImageType.GUIDE,
        )
        self.poster = ContestImage.objects.create(
            contest=self.contest,
            image="contest_images/official-poster.webp",
            order=1,
            image_type=ContestImage.ImageType.POSTER,
        )

    def test_poster_is_used_for_listing_and_detail_context_before_guides(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        data = ContestListSerializer(self.contest, context={"request": request}).data

        self.assertTrue(data["first_image"].endswith("contest_images/official-poster.webp"))

        response = self.client.get(f"/badminton-tournament/{self.contest.slug}/")

        self.assertEqual(response.context["poster_image"].pk, self.poster.pk)
        self.assertEqual(list(response.context["guide_images"]), [self.guide])

    def test_upload_api_persists_the_supplied_image_role(self):
        admin = get_user_model().objects.create(
            email="image-role-admin@example.com",
            is_staff=True,
        )
        token = str(RefreshToken.for_user(admin).access_token)
        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )

        response = self.client.post(
            f"/api/contests/{self.contest.slug}/images/",
            {
                "image": SimpleUploadedFile("guide.png", image_bytes, content_type="image/png"),
                "image_type": ContestImage.ImageType.GUIDE,
                "order": 2,
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["image_type"], ContestImage.ImageType.GUIDE)
        self.assertTrue(
            ContestImage.objects.filter(
                contest=self.contest,
                image_type=ContestImage.ImageType.GUIDE,
                order=2,
            ).exists()
        )

    def test_replace_api_always_creates_a_poster(self):
        admin = get_user_model().objects.create(
            email="replace-role-admin@example.com",
            is_staff=True,
        )
        token = str(RefreshToken.for_user(admin).access_token)
        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )

        response = self.client.post(
            f"/api/contests/{self.contest.slug}/images/replace/",
            {
                "image": SimpleUploadedFile("poster.png", image_bytes, content_type="image/png"),
                "image_type": ContestImage.ImageType.GUIDE,
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["image"]["image_type"], ContestImage.ImageType.POSTER)
        self.assertEqual(
            ContestImage.objects.get(contest=self.contest).image_type,
            ContestImage.ImageType.POSTER,
        )
