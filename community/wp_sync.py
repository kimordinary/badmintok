"""워드프레스(매거진) → 배드민톡(BadmintokPost) 동기화.

WP는 글 작성 백오피스로만 쓰고, 여기서 글을 가져와 기존 배드민톡 글로 저장한다.
본문(content.rendered)은 flutter_html/웹 렌더에 맞게 최소 정제한다.
"""
import os
import re
import hashlib
import requests
from django.utils.dateparse import parse_datetime
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


# ── HTML 정제 ──────────────────────────────────────────────

def _extract_youtube_id(url):
    m = re.search(r'(?:v=|youtu\.be/|embed/|/v/)([A-Za-z0-9_-]{11})', url or '')
    return m.group(1) if m else None


_YT_FIGURE = re.compile(
    r'<figure[^>]*wp-block-embed-youtube[^>]*>.*?'
    r'<div class="wp-block-embed__wrapper">\s*(https?://[^\s<]+?)\s*</div>.*?</figure>',
    re.DOTALL,
)


def _youtube_embed_to_iframe(html):
    """WP 유튜브 embed(생 URL) → 표준 iframe(embed 경로). 앱/웹 공통 계약."""
    def repl(m):
        vid = _extract_youtube_id(m.group(1))
        if vid:
            return (f'<iframe src="https://www.youtube.com/embed/{vid}" '
                    f'frameborder="0" allowfullscreen></iframe>')
        return m.group(0)
    return _YT_FIGURE.sub(repl, html)


def clean_wp_content(html, strip_wp_classes=False):
    """WP 렌더 HTML을 앱/웹이 쓰기 좋게 최소 정제.
    - (필수) 유튜브 embed → iframe
    - (선택) wp-* class 제거
    """
    if not html:
        return ''
    html = _youtube_embed_to_iframe(html)
    if strip_wp_classes:
        # class="...wp-...": wp- 로 시작하거나 wp- 를 포함한 class 속성 제거
        html = re.sub(r'\s+class="[^"]*\bwp-[^"]*"', '', html)
    return html.strip()


# ── 이미지 다운로드 (Cloudways 의존 제거) ──────────────────

_IMG_SRC = re.compile(r'(<img[^>]+\bsrc=")([^"]+)(")')
_ALLOWED_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def download_content_images(html, subdir="community/wp_images"):
    """본문의 외부 이미지(WP/Cloudways)를 Django media로 내려받고 src를 로컬 URL로 치환.
    이미 로컬(/media 등)인 이미지는 그대로 둔다. 실패 시 원본 URL 유지.
    """
    if not html:
        return html

    def repl(m):
        pre, url, post = m.group(1), m.group(2), m.group(3)
        if url.startswith("/") or "/media/" in url:
            return m.group(0)  # 이미 로컬
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            ext = os.path.splitext(url.split("?")[0])[1].lower()
            if ext not in _ALLOWED_EXT:
                ext = ".jpg"
            name = f"{subdir}/{hashlib.md5(url.encode()).hexdigest()}{ext}"
            if not default_storage.exists(name):
                default_storage.save(name, ContentFile(r.content))
            return pre + default_storage.url(name) + post
        except Exception:
            return m.group(0)  # 실패 시 원본 유지

    return _IMG_SRC.sub(repl, html)


# ── 동기화 ────────────────────────────────────────────────

SYSTEM_AUTHOR_EMAIL = "wp-magazine@badmintok.com"


def get_system_author():
    """WP 매거진 글의 작성자로 쓸 시스템 유저(없으면 생성)."""
    User = get_user_model()
    user, _created = User.objects.get_or_create(
        email=SYSTEM_AUTHOR_EMAIL,
        defaults={"activity_name": "배드민톡 매거진", "is_active": True},
    )
    return user


def build_category_map(wp_base, auth=None):
    """WP 카테고리 id → Django Category(source=badmintok). slug로 매칭."""
    from community.models import Category
    r = requests.get(f"{wp_base}/categories", params={"per_page": 100},
                     auth=auth, timeout=30)
    r.raise_for_status()
    mapping = {}
    for c in r.json():
        dj = Category.objects.filter(source="badmintok", slug=c["slug"]).first()
        if dj:
            mapping[c["id"]] = dj
    return mapping


def sync_wp_post(wp_post, category_map, author):
    """WP 글 dict → BadmintokPost upsert. slug로 기존 글 매칭."""
    from community.models import Post

    title = wp_post["title"]["rendered"]
    content = clean_wp_content(wp_post["content"]["rendered"])
    content = download_content_images(content)  # 외부 이미지 → Django media
    slug = (wp_post.get("slug") or "")[:45]

    dj_cats = [category_map[c] for c in wp_post.get("categories", []) if c in category_map]
    main_cat = dj_cats[0] if dj_cats else None

    date_str = wp_post.get("date_gmt") or wp_post.get("date")
    published = parse_datetime(date_str + "Z") if date_str and wp_post.get("date_gmt") else parse_datetime(date_str or "")

    # slug로 기존 글 찾기 (재동기화 시 갱신)
    obj = Post.objects.filter(slug=slug, source="badmintok").first() if slug else None
    created = obj is None
    if obj is None:
        obj = Post(source="badmintok", author=author)

    obj.title = title
    obj.content = content
    obj.source = "badmintok"
    if slug:
        obj.slug = slug
    obj.author = author
    if main_cat:
        obj.category = main_cat
    if published:
        obj.published_at = published
    obj.is_draft = wp_post.get("status") != "publish"
    obj.save()

    if dj_cats:
        obj.categories.set(dj_cats)

    return obj, created


def fetch_wp_posts(wp_base, auth=None, post_id=None, status="publish,draft", per_page=20):
    """WP 글 목록/단건 조회."""
    if post_id:
        r = requests.get(f"{wp_base}/posts/{post_id}", params={"context": "edit"},
                         auth=auth, timeout=30)
        r.raise_for_status()
        return [r.json()]
    r = requests.get(f"{wp_base}/posts",
                     params={"per_page": per_page, "status": status, "context": "edit"},
                     auth=auth, timeout=30)
    r.raise_for_status()
    return r.json()
