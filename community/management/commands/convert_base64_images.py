"""
기존 게시글의 base64 이미지를 실제 파일로 변환하는 관리 명령어
"""
import base64
import json
import os
import re
import uuid
from datetime import datetime

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from community.models import Post


class Command(BaseCommand):
    help = '게시글 content에 포함된 base64 이미지를 실제 파일로 변환합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 변환 없이 영향 받을 게시글 수만 확인합니다.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='처리할 게시글 수 제한',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            default=True,
            help='변환 전 백업 파일 생성 (기본값: True)',
        )
        parser.add_argument(
            '--no-backup',
            action='store_true',
            help='백업 없이 변환 (주의: 복구 불가)',
        )
        parser.add_argument(
            '--restore',
            type=str,
            default=None,
            help='백업 파일에서 복원 (예: --restore=backup_20240101_120000.json)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        no_backup = options['no_backup']
        restore_file = options['restore']

        # 복원 모드
        if restore_file:
            self.restore_from_backup(restore_file)
            return

        # base64 이미지 패턴: data:image/xxx;base64,xxxxx
        base64_pattern = re.compile(
            r'<img[^>]+src=["\']'
            r'(data:image/([a-zA-Z+]+);base64,([A-Za-z0-9+/=]+))'
            r'["\'][^>]*>',
            re.IGNORECASE
        )

        # base64 이미지가 포함된 게시글 찾기
        posts_with_base64 = Post.objects.filter(
            content__contains='data:image'
        ).filter(
            content__contains='base64'
        )

        if limit:
            posts_with_base64 = posts_with_base64[:limit]

        total_posts = posts_with_base64.count()
        self.stdout.write(f'base64 이미지가 포함된 게시글: {total_posts}개')

        if total_posts == 0:
            self.stdout.write(self.style.SUCCESS('변환할 게시글이 없습니다.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run 모드 - 실제 변환은 수행하지 않습니다.'))
            for post in posts_with_base64:
                matches = base64_pattern.findall(post.content)
                self.stdout.write(f'  - 게시글 #{post.id} "{post.title[:30]}...": {len(matches)}개 이미지')
            return

        # 백업 생성
        backup_data = []
        if not no_backup:
            self.stdout.write('백업 생성 중...')
            for post in posts_with_base64:
                backup_data.append({
                    'id': post.id,
                    'title': post.title,
                    'content': post.content,
                })

            backup_filename = f'base64_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            backup_path = os.path.join('backups', backup_filename)

            # backups 디렉토리 생성
            os.makedirs('backups', exist_ok=True)

            with open(os.path.join('backups', backup_filename), 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)

            self.stdout.write(self.style.SUCCESS(f'백업 완료: backups/{backup_filename}'))
            self.stdout.write(self.style.WARNING(f'문제 발생 시 복원: python manage.py convert_base64_images --restore={backup_filename}'))
            self.stdout.write('')

        converted_posts = 0
        converted_images = 0
        failed_posts = []

        for post in posts_with_base64:
            try:
                with transaction.atomic():
                    new_content = post.content
                    matches = base64_pattern.findall(post.content)

                    if not matches:
                        continue

                    post_converted = 0
                    for full_match, img_format, base64_data in matches:
                        try:
                            # base64 디코딩
                            image_data = base64.b64decode(base64_data)

                            # 파일 확장자 결정
                            ext_map = {
                                'jpeg': '.jpg',
                                'jpg': '.jpg',
                                'png': '.png',
                                'gif': '.gif',
                                'webp': '.webp',
                                'svg+xml': '.svg',
                            }
                            # svg+xml 같은 경우 처리
                            img_format_clean = img_format.lower().replace('+', '+')
                            file_ext = ext_map.get(img_format_clean, '.png')

                            # 고유 파일명 생성
                            unique_filename = f"{uuid.uuid4()}{file_ext}"
                            file_path = os.path.join('community', 'posts', unique_filename)

                            # 파일 저장
                            saved_path = default_storage.save(
                                file_path,
                                ContentFile(image_data)
                            )
                            file_url = default_storage.url(saved_path)

                            # content에서 base64를 파일 URL로 교체
                            new_content = new_content.replace(full_match, file_url)

                            post_converted += 1
                            converted_images += 1

                            self.stdout.write(
                                f'  게시글 #{post.id}: 이미지 변환 완료 -> {file_url}'
                            )

                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  게시글 #{post.id}: 이미지 변환 실패 - {str(e)}'
                                )
                            )
                            raise  # 트랜잭션 롤백을 위해 예외 발생

                    if post_converted > 0:
                        post.content = new_content
                        post.save(update_fields=['content'])
                        converted_posts += 1

            except Exception as e:
                failed_posts.append((post.id, str(e)))
                self.stdout.write(
                    self.style.ERROR(f'게시글 #{post.id} 처리 실패 (롤백됨): {str(e)}')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'변환 완료!'))
        self.stdout.write(f'  - 처리된 게시글: {converted_posts}개')
        self.stdout.write(f'  - 변환된 이미지: {converted_images}개')
        if failed_posts:
            self.stdout.write(
                self.style.WARNING(f'  - 실패한 게시글: {len(failed_posts)}개 (원본 유지됨)')
            )
            for post_id, error in failed_posts:
                self.stdout.write(f'    - #{post_id}: {error}')

    def restore_from_backup(self, backup_filename):
        """백업 파일에서 게시글 content 복원"""
        backup_path = os.path.join('backups', backup_filename)

        if not os.path.exists(backup_path):
            self.stdout.write(self.style.ERROR(f'백업 파일을 찾을 수 없습니다: {backup_path}'))
            return

        self.stdout.write(f'백업 파일에서 복원 중: {backup_path}')

        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        restored = 0
        failed = 0

        for item in backup_data:
            try:
                post = Post.objects.get(id=item['id'])
                post.content = item['content']
                post.save(update_fields=['content'])
                restored += 1
                self.stdout.write(f'  게시글 #{item["id"]} 복원 완료')
            except Post.DoesNotExist:
                failed += 1
                self.stdout.write(
                    self.style.WARNING(f'  게시글 #{item["id"]} 찾을 수 없음 (삭제됨?)')
                )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  게시글 #{item["id"]} 복원 실패: {str(e)}')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'복원 완료!'))
        self.stdout.write(f'  - 복원된 게시글: {restored}개')
        if failed > 0:
            self.stdout.write(self.style.WARNING(f'  - 실패: {failed}개'))
