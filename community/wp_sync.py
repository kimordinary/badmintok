"""워드프레스(매거진) → 배드민톡(BadmintokPost) 동기화.

WP는 글 작성 백오피스로만 쓰고, 여기서 글을 가져와 기존 배드민톡 글로 저장한다.
본문(content.rendered)은 flutter_html/웹 렌더에 맞게 최소 정제한다.
"""
import os
import re
import json
import hashlib
import requests
from urllib.parse import unquote
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
        defaults={"activity_name": "배드민톡", "is_active": True},
    )
    # 기존 유저 이름 보정 (동기화 시마다)
    if user.activity_name != "배드민톡":
        user.activity_name = "배드민톡"
        user.save(update_fields=["activity_name"])
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


def build_tag_map(wp_base, auth=None, create_missing=True):
    """WP 태그 id → Django Tag(source=badmintok). slug로 매칭, 없으면 생성."""
    from community.models import Tag
    r = requests.get(f"{wp_base}/tags", params={"per_page": 100},
                     auth=auth, timeout=30)
    r.raise_for_status()
    mapping = {}
    for t in r.json():
        dj = Tag.objects.filter(source="badmintok", slug=t["slug"]).first()
        if not dj and create_missing:
            dj = Tag.objects.create(
                source="badmintok", slug=t["slug"], name=t["name"]
            )
        if dj:
            mapping[t["id"]] = dj
    return mapping


def sync_wp_post(wp_post, category_map, author, tag_map=None):
    """WP 글 dict → BadmintokPost upsert. slug로 기존 글 매칭."""
    from community.models import Post

    title = wp_post["title"]["rendered"]
    content = clean_wp_content(wp_post["content"]["rendered"])
    content = download_content_images(content)  # 외부 이미지 → Django media
    # WP가 한글 slug를 %인코딩(post_name)으로 주므로 디코딩해서 사용
    slug = unquote(wp_post.get("slug") or "")[:45]

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
    obj._skip_sync_notify = True  # 동기화 글은 전체 푸시 발송 안 함
    obj.save()

    if dj_cats:
        obj.categories.set(dj_cats)

    if tag_map is not None:
        dj_tags = [tag_map[t] for t in wp_post.get("tags", []) if t in tag_map]
        obj.tags.set(dj_tags)

    return obj, created


def fetch_wp_posts(wp_base, auth=None, post_id=None, status="publish", per_page=20):
    """WP 글 목록/단건 조회.
    인증(auth)이 있으면 edit 컨텍스트로 임시저장(draft)까지, 없으면 발행글만(view).
    """
    common = {}
    if auth:
        common["context"] = "edit"  # 인증 시에만 (임시저장 포함 가능)
    if post_id:
        r = requests.get(f"{wp_base}/posts/{post_id}", params=common,
                         auth=auth, timeout=30)
        r.raise_for_status()
        return [r.json()]
    params = {"per_page": per_page, "status": status, **common}
    r = requests.get(f"{wp_base}/posts", params=params, auth=auth, timeout=30)
    r.raise_for_status()
    return r.json()


def prune_deleted_posts(wp_base, author, auth=None, status="publish,draft"):
    """WP에서 삭제된(더 이상 없는) 시스템 글을 배드민톡에서 숨김(soft delete).

    안전장치:
    - 시스템 작성자(author) 글만 대상 → 사용자 수동 글 보호
    - is_deleted=True (복구 가능)
    - WP 전체 slug를 페이지네이션으로 수집 → 부분 조회로 인한 오삭제 방지
    - WP 글이 0개면 스킵 → 조회 장애 시 전체 삭제 방지
    반환: 숨김 처리된 slug 목록
    """
    from community.models import Post

    common = {"context": "edit"} if auth else {}
    wp_slugs = set()
    page = 1
    while True:
        params = {"per_page": 100, "status": status, "page": page,
                  "_fields": "slug", **common}
        r = requests.get(f"{wp_base}/posts", params=params, auth=auth, timeout=30)
        if r.status_code == 400:  # 페이지 범위 초과 → 끝
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for w in batch:
            wp_slugs.add(unquote(w.get("slug") or "")[:45])
        if len(batch) < 100:
            break
        page += 1

    if not wp_slugs:  # 안전: WP 글 0개면 아무것도 안 함
        return []

    to_prune = Post.objects.filter(
        source="badmintok", author=author, is_deleted=False,
    ).exclude(slug__in=wp_slugs)

    pruned = []
    for p in to_prune:
        p.is_deleted = True
        p._skip_sync_notify = True
        p.save(update_fields=["is_deleted"])
        pruned.append(p.slug)
    return pruned


# ── 기존 글 이전: Editor.js JSON → HTML ─────────────────────

def editorjs_to_html(content, base_url="https://badmintok.com"):
    """기존 배드민톡 글(Editor.js JSON)을 HTML로 변환 (WP 이전용).
    JSON이 아니면(이미 HTML) 그대로 반환.
    """
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return content
    if not isinstance(data, dict) or "blocks" not in data:
        return content

    out = []
    for b in data.get("blocks", []):
        t = b.get("type")
        d = b.get("data", {}) or {}
        if t == "paragraph":
            out.append(f"<p>{d.get('text','')}</p>")
        elif t in ("header", "h2", "h3", "h4"):
            lv = d.get("level") or {"h2": 2, "h3": 3, "h4": 4}.get(t, 2)
            out.append(f"<h{lv}>{d.get('text','')}</h{lv}>")
        elif t == "list":
            tag = "ol" if d.get("style") == "ordered" else "ul"
            items = "".join(f"<li>{i}</li>" for i in d.get("items", []))
            out.append(f"<{tag}>{items}</{tag}>")
        elif t == "image":
            url = d.get("url", "")
            if url.startswith("/"):
                url = base_url + url
            alt = d.get("alt", "")
            cap = d.get("caption", "")
            fig = f'<figure class="wp-block-image"><img src="{url}" alt="{alt}"/>'
            if cap:
                fig += f'<figcaption>{cap}</figcaption>'
            fig += "</figure>"
            out.append(fig)
        elif t == "table":
            rows = d.get("content", [])
            head = d.get("withHeadings")
            th = '<figure class="wp-block-table"><table>'
            for ri, row in enumerate(rows):
                cell = "th" if (head and ri == 0) else "td"
                th += "<tr>" + "".join(f"<{cell}>{c}</{cell}>" for c in row) + "</tr>"
            th += "</table></figure>"
            out.append(th)
        elif t == "button":
            out.append(
                '<div class="wp-block-button">'
                f'<a class="wp-block-button__link" href="{d.get("url","")}">'
                f'{d.get("text","")}</a></div>')
        elif t == "youtube":
            vid = _extract_youtube_id(d.get("url", ""))
            if vid:
                out.append(
                    f'<iframe src="https://www.youtube.com/embed/{vid}" '
                    f'frameborder="0" allowfullscreen></iframe>')
        elif t == "quote":
            cap = d.get("caption", "")
            q = f'<blockquote>{d.get("text","")}'
            if cap:
                q += f'<cite>{cap}</cite>'
            q += "</blockquote>"
            out.append(q)
        elif t == "delimiter":
            out.append("<hr/>")
        else:
            if d.get("text"):
                out.append(f"<p>{d['text']}</p>")
    return "\n".join(out)
