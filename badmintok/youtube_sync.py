import requests
import isodate
import logging
from django.conf import settings
from badmintok.models import YoutubeVideo

logger = logging.getLogger(__name__)


def sync_youtube_playlist():
    """YouTube Data API를 사용하여 플레이리스트 영상을 동기화"""
    api_key = settings.YOUTUBE_API_KEY
    playlist_id = settings.YOUTUBE_PLAYLIST_ID

    if not api_key or not playlist_id:
        logger.error("YOUTUBE_API_KEY 또는 YOUTUBE_PLAYLIST_ID가 설정되지 않았습니다.")
        return {"created": 0, "updated": 0, "error": "API 키 또는 플레이리스트 ID 미설정"}

    created_count = 0
    updated_count = 0
    skipped_count = 0
    next_page_token = None

    while True:
        # 1. 플레이리스트 아이템 조회
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": api_key,
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params=params,
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(f"YouTube API 오류: {response.status_code} - {response.text}")
            return {"created": created_count, "updated": updated_count, "error": response.text}

        data = response.json()
        items = data.get("items", [])

        if not items:
            break

        # 2. 각 영상의 video_id 수집
        video_ids = []
        video_snippets = {}
        for item in items:
            snippet = item.get("snippet", {})
            vid = snippet.get("resourceId", {}).get("videoId", "")
            if vid:
                video_ids.append(vid)
                video_snippets[vid] = snippet

        # 3. videos API로 상세 정보 (duration 등) 조회
        video_details = {}
        if video_ids:
            detail_response = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "contentDetails,snippet",
                    "id": ",".join(video_ids),
                    "key": api_key,
                },
                timeout=30,
            )
            if detail_response.status_code == 200:
                for v in detail_response.json().get("items", []):
                    video_details[v["id"]] = v

        # 4. DB에 저장/업데이트 (60초 이하 숏폼 필터링)
        for idx, vid in enumerate(video_ids):
            snippet = video_snippets.get(vid, {})
            detail = video_details.get(vid, {})

            # duration 필터링: 60초 이하면 숏폼으로 판단
            duration_str = detail.get("contentDetails", {}).get("duration", "")
            if duration_str:
                try:
                    duration_seconds = isodate.parse_duration(duration_str).total_seconds()
                except Exception:
                    duration_seconds = 0

                if duration_seconds <= 60:
                    # 기존 DB에 있으면 비활성화
                    YoutubeVideo.objects.filter(video_id=vid).update(is_active=False)
                    skipped_count += 1
                    logger.info(f"숏폼 제외: {snippet.get('title', '')} ({int(duration_seconds)}초)")
                    continue

            title = snippet.get("title", "")
            description = snippet.get("description", "")
            youtube_url = f"https://www.youtube.com/watch?v={vid}"
            thumbnail_url = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"

            # 고해상도 썸네일 우선
            thumbnails = snippet.get("thumbnails", {})
            for quality in ["maxres", "high", "medium", "default"]:
                if quality in thumbnails:
                    thumbnail_url = thumbnails[quality]["url"]
                    break

            # position을 order로 사용 (플레이리스트 순서)
            position = snippet.get("position", idx)

            obj, created = YoutubeVideo.objects.update_or_create(
                video_id=vid,
                defaults={
                    "title": title[:200],
                    "youtube_url": youtube_url,
                    "thumbnail_url": thumbnail_url,
                    "description": description[:500] if description else "",
                    "order": 1000 - position,  # 높을수록 먼저 표시
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                logger.info(f"새 영상 추가: {title}")
            else:
                updated_count += 1

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    result = {"created": created_count, "updated": updated_count, "skipped": skipped_count, "error": None}
    logger.info(f"YouTube 동기화 완료: {created_count}개 추가, {updated_count}개 업데이트, {skipped_count}개 숏폼 제외")
    return result
