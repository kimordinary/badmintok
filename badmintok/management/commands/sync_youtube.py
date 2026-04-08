from django.core.management.base import BaseCommand
from badmintok.youtube_sync import sync_youtube_playlist


class Command(BaseCommand):
    help = "YouTube 플레이리스트의 영상을 동기화합니다."

    def handle(self, *args, **options):
        self.stdout.write("YouTube 영상 동기화 시작...")
        result = sync_youtube_playlist()

        if result.get("error"):
            self.stderr.write(self.style.ERROR(f"오류: {result['error']}"))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"완료: {result['created']}개 추가, {result['updated']}개 업데이트, {result.get('skipped', 0)}개 숏폼 제외"
            ))
