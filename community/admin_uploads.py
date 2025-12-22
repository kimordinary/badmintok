from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.admin.views.decorators import staff_member_required
from PIL import Image
import os


@staff_member_required
@require_POST
@csrf_exempt
def quill_image_upload(request):
    """Admin에서 Quill 에디터용 이미지 업로드 엔드포인트.

    업로드된 파일을 MEDIA_ROOT 하위에 저장하고 URL을 JSON으로 반환합니다.
    응답 형식: {"url": "..."}
    """
    upload = request.FILES.get("image")
    if not upload:
        return JsonResponse({"error": "No image file provided."}, status=400)

    # 저장 경로: community/quill/YYYY/MM/DD/filename
    today = timezone.now()
    subdir = today.strftime("community/quill/%Y/%m/%d")
    filename = upload.name
    path = f"{subdir}/{filename}"

    saved_path = default_storage.save(path, upload)
    url = default_storage.url(saved_path)

    return JsonResponse({"url": url})


@staff_member_required
@require_POST
@csrf_exempt
def editorjs_image_upload(request):
    """Admin에서 Editor.js용 이미지 업로드 엔드포인트.

    업로드된 파일을 MEDIA_ROOT 하위에 저장하고 Editor.js 형식으로 반환합니다.
    응답 형식: {"success": 1, "file": {"url": "...", "width": ..., "height": ...}}
    """
    upload = request.FILES.get("image")
    if not upload:
        return JsonResponse({"success": 0, "message": "No image file provided."}, status=400)

    try:
        # 저장 경로: community/editorjs/YYYY/MM/DD/filename
        today = timezone.now()
        subdir = today.strftime("community/editorjs/%Y/%m/%d")
        filename = upload.name
        path = f"{subdir}/{filename}"

        saved_path = default_storage.save(path, upload)
        url = default_storage.url(saved_path)

        # 이미지 크기 정보 가져오기
        width = 0
        height = 0
        try:
            # 저장된 파일 열기
            full_path = default_storage.path(saved_path)
            with Image.open(full_path) as img:
                width, height = img.size
        except Exception as e:
            # 이미지 크기를 가져오지 못해도 업로드는 성공으로 처리
            pass

        return JsonResponse({
            "success": 1,
            "file": {
                "url": url,
                "width": width,
                "height": height
            }
        })
    except Exception as e:
        return JsonResponse({"success": 0, "message": str(e)}, status=500)
