import os
from io import BytesIO

from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import ImageField


# WebP 변환 대상이 아닌 확장자
WEBP_EXTENSION = '.webp'
CONVERTIBLE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}


def is_webp(filename):
    """파일이 WebP인지 확인"""
    if not filename:
        return True  # 파일이 없으면 변환 불필요
    return filename.lower().endswith(WEBP_EXTENSION)


def is_convertible(filename):
    """WebP로 변환 가능한 이미지인지 확인"""
    if not filename:
        return False
    ext = os.path.splitext(filename.lower())[1]
    return ext in CONVERTIBLE_EXTENSIONS


class WebPImageField(ImageField):
    """
    이미지를 자동으로 WebP 형식으로 변환하는 커스텀 ImageField.
    PNG, JPG, JPEG 등의 이미지가 업로드되면 WebP로 변환하여 저장합니다.
    """

    def __init__(self, *args, quality=85, **kwargs):
        """
        Args:
            quality: WebP 압축 품질 (1-100, 기본값 85)
        """
        self.quality = quality
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.quality != 85:
            kwargs['quality'] = self.quality
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        file = super().pre_save(model_instance, add)

        if not file:
            return file

        # 이미 WebP인 경우 변환하지 않음
        if file.name and file.name.lower().endswith('.webp'):
            return file

        # 새로 업로드된 파일인지 확인 (committed=False인 경우 새 파일)
        # FieldFile의 경우 _committed 속성으로 확인
        is_new_upload = hasattr(file, '_committed') and not file._committed

        # InMemoryUploadedFile 또는 TemporaryUploadedFile인 경우도 새 파일
        if not is_new_upload:
            from django.core.files.uploadedfile import UploadedFile
            is_new_upload = isinstance(file, UploadedFile)

        # 새 파일이 아니면 변환하지 않음 (이미 저장된 파일)
        if not is_new_upload:
            return file

        try:
            # 파일 포지션을 처음으로 이동
            if hasattr(file, 'seek'):
                file.seek(0)

            # 이미지 열기
            img = Image.open(file)
            img.load()  # 이미지 데이터를 메모리에 완전히 로드

            # 모드 변환: 팔레트 모드(P)는 RGBA로, 기타는 RGB로
            if img.mode == 'P':
                # 팔레트 모드: 투명도 정보가 있으면 RGBA로, 없으면 RGB로
                if 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            elif img.mode == 'LA':
                img = img.convert('RGBA')
            elif img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')

            # WebP로 변환
            output = BytesIO()
            img.save(output, format='WEBP', quality=self.quality, optimize=True)
            output.seek(0)

            # 파일명 변경 (.webp로)
            # 경로에서 파일명만 추출하여 처리
            basename = os.path.basename(file.name)
            name_without_ext = os.path.splitext(basename)[0]
            new_name = f"{name_without_ext}.webp"

            # 새 파일로 저장
            new_file = ContentFile(output.read(), name=new_name)
            setattr(model_instance, self.attname, new_file)

            return new_file
        except Exception as e:
            # 변환 실패 시 원본 그대로 저장
            import logging
            logging.getLogger(__name__).warning(f"WebP 변환 실패: {e}")
            return file

        return file


def convert_to_webp(image_file, quality=85):
    """
    이미지 파일을 WebP로 변환하는 유틸리티 함수.

    Args:
        image_file: 이미지 파일 객체
        quality: WebP 압축 품질 (1-100)

    Returns:
        ContentFile: WebP로 변환된 파일 객체
    """
    if not image_file:
        return None

    try:
        img = Image.open(image_file)

        # 모드 변환
        if img.mode in ('RGBA', 'LA', 'P'):
            pass
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # WebP로 변환
        output = BytesIO()
        img.save(output, format='WEBP', quality=quality, optimize=True)
        output.seek(0)

        # 파일명 변경
        original_name = getattr(image_file, 'name', 'image')
        new_name = os.path.splitext(original_name)[0] + '.webp'

        return ContentFile(output.read(), name=new_name)
    except Exception:
        return image_file


def convert_existing_image_to_webp(model_instance, field_name, quality=85, delete_original=True):
    """
    기존 모델 인스턴스의 이미지를 WebP로 변환.

    Args:
        model_instance: Django 모델 인스턴스
        field_name: 이미지 필드 이름
        quality: WebP 압축 품질 (1-100)
        delete_original: 원본 파일 삭제 여부

    Returns:
        dict: 변환 결과 {'success': bool, 'message': str, 'old_size': int, 'new_size': int}
    """
    field = getattr(model_instance, field_name, None)

    if not field or not field.name:
        return {'success': False, 'message': '이미지가 없습니다.', 'old_size': 0, 'new_size': 0}

    if is_webp(field.name):
        return {'success': False, 'message': '이미 WebP 형식입니다.', 'old_size': 0, 'new_size': 0}

    if not is_convertible(field.name):
        return {'success': False, 'message': '변환할 수 없는 형식입니다.', 'old_size': 0, 'new_size': 0}

    try:
        # 원본 파일 정보
        original_path = field.name
        original_size = field.size if hasattr(field, 'size') else 0

        # 이미지 열기
        field.open('rb')
        img = Image.open(field)

        # 모드 변환
        if img.mode in ('RGBA', 'LA', 'P'):
            # PNG 투명도 유지
            if img.mode == 'P':
                img = img.convert('RGBA')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # WebP로 변환
        output = BytesIO()
        img.save(output, format='WEBP', quality=quality, optimize=True)
        output.seek(0)

        # 새 파일명 생성
        new_name = os.path.splitext(original_path)[0] + '.webp'

        # 새 파일 저장
        new_file = ContentFile(output.read(), name=os.path.basename(new_name))

        # 필드에 새 파일 설정
        field.save(os.path.basename(new_name), new_file, save=False)
        model_instance.save(update_fields=[field_name])

        # 새 파일 크기
        new_size = field.size if hasattr(field, 'size') else 0

        # 원본 파일 삭제
        if delete_original and original_path != field.name:
            try:
                if default_storage.exists(original_path):
                    default_storage.delete(original_path)
            except Exception:
                pass  # 삭제 실패해도 변환은 성공

        return {
            'success': True,
            'message': f'변환 완료: {os.path.basename(original_path)} → {os.path.basename(field.name)}',
            'old_size': original_size,
            'new_size': new_size
        }

    except Exception as e:
        return {'success': False, 'message': f'변환 실패: {str(e)}', 'old_size': 0, 'new_size': 0}


def get_all_image_fields_info():
    """
    프로젝트의 모든 이미지 필드 정보를 반환.

    Returns:
        list: [{'app': str, 'model': str, 'field': str, 'model_class': Model}]
    """
    from django.apps import apps

    image_fields = []

    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, ImageField):
                image_fields.append({
                    'app': model._meta.app_label,
                    'model': model._meta.model_name,
                    'model_verbose': model._meta.verbose_name,
                    'field': field.name,
                    'field_verbose': getattr(field, 'verbose_name', field.name),
                    'model_class': model,
                })

    return image_fields


def get_unconverted_images_stats():
    """
    WebP로 변환되지 않은 이미지 통계를 반환.

    Returns:
        dict: 모델별 미변환 이미지 수
    """
    stats = {}
    image_fields = get_all_image_fields_info()

    for info in image_fields:
        model_class = info['model_class']
        field_name = info['field']
        key = f"{info['app']}.{info['model']}.{field_name}"

        try:
            # 해당 필드에 값이 있는 모든 레코드 조회
            queryset = model_class.objects.exclude(**{f"{field_name}__exact": ''})
            queryset = queryset.exclude(**{f"{field_name}__isnull": True})

            total_count = queryset.count()
            unconverted_count = 0

            for obj in queryset.iterator():
                field_value = getattr(obj, field_name)
                if field_value and field_value.name and is_convertible(field_value.name):
                    unconverted_count += 1

            if total_count > 0:
                stats[key] = {
                    'app': info['app'],
                    'model': info['model'],
                    'model_verbose': info['model_verbose'],
                    'field': field_name,
                    'field_verbose': info['field_verbose'],
                    'total': total_count,
                    'unconverted': unconverted_count,
                    'converted': total_count - unconverted_count,
                }
        except Exception:
            pass

    return stats
