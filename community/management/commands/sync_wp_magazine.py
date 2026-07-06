"""워드프레스 매거진 글 → 배드민톡(BadmintokPost) 동기화 커맨드.

사용:
  python manage.py sync_wp_magazine --post-id 50269   # 특정 글 하나
  python manage.py sync_wp_magazine                    # 발행/임시 글 일괄

인증(임시저장 글까지 가져오려면) 환경변수:
  WP_APP_USER, WP_APP_PASS  (WP Application Password)
  WP_MAGAZINE_API           (기본: https://badmintok.com/magazine/wp-json/wp/v2)
"""
import os
from django.core.management.base import BaseCommand, CommandError

from community.wp_sync import (
    fetch_wp_posts, build_category_map, build_tag_map,
    get_system_author, sync_wp_post, prune_deleted_posts,
)

# 헤드리스: WP는 임시도메인 직접 접속(프록시 제거됨). 필요 시 WP_MAGAZINE_API로 덮어씀.
DEFAULT_WP_BASE = "https://wordpress-1477303-5774521.cloudwaysapps.com/wp-json/wp/v2"


class Command(BaseCommand):
    help = "워드프레스 매거진 글을 배드민톡(BadmintokPost)으로 동기화한다."

    def add_arguments(self, parser):
        parser.add_argument("--post-id", type=int, default=None,
                            help="특정 WP 글 하나만 동기화")
        parser.add_argument("--status", default="publish,draft",
                            help="가져올 WP 글 상태 (기본: publish,draft)")
        parser.add_argument("--prune", action="store_true",
                            help="WP에서 삭제된 글을 배드민톡에서도 숨김 (전체 동기화 시에만)")

    def handle(self, *args, **opts):
        wp_base = os.environ.get("WP_MAGAZINE_API", DEFAULT_WP_BASE)
        user = os.environ.get("WP_APP_USER")
        pw = os.environ.get("WP_APP_PASS")
        auth = (user, pw) if user and pw else None

        try:
            author = get_system_author()
            cat_map = build_category_map(wp_base, auth=auth)
            tag_map = build_tag_map(wp_base, auth=auth)
            self.stdout.write(
                f"카테고리 매핑: {len(cat_map)}개 / 태그 매핑: {len(tag_map)}개 (WP→배드민톡)"
            )

            posts = fetch_wp_posts(
                wp_base, auth=auth,
                post_id=opts["post_id"], status=opts["status"],
            )
        except Exception as e:
            raise CommandError(f"WP 조회 실패: {e}")

        self.stdout.write(f"WP 글 {len(posts)}개 가져옴\n")

        created_n = updated_n = 0
        for wp in posts:
            obj, created = sync_wp_post(wp, cat_map, author, tag_map=tag_map)
            created_n += created
            updated_n += (not created)
            tag = "생성" if created else "갱신"
            draft = " (임시)" if obj.is_draft else ""
            self.stdout.write(
                f"  [{tag}]{draft} {obj.title[:40]} "
                f"(slug={obj.slug}, cat={obj.category})"
            )

        # WP에서 삭제된 글 정리 (전체 동기화 + --prune 일 때만)
        if opts["prune"] and not opts["post_id"]:
            try:
                pruned = prune_deleted_posts(
                    wp_base, author, auth=auth, status=opts["status"],
                )
                if pruned:
                    self.stdout.write(f"숨김 처리(WP에서 삭제됨): {pruned}")
                else:
                    self.stdout.write("숨김 대상 없음 (WP와 일치)")
            except Exception as e:
                self.stderr.write(f"prune 건너뜀(WP 조회 실패): {e}")

        self.stdout.write(self.style.SUCCESS(
            f"\n동기화 완료 — 생성 {created_n} / 갱신 {updated_n}"
        ))
