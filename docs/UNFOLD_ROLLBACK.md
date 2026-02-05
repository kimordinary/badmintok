# Django Unfold 복구 방안

## 현재 변경 사항
1. `requirements.txt` - django-unfold 추가
2. `badmintok/settings.py` - unfold 앱 등록 및 UNFOLD 설정 추가
3. `templates/admin/base_site.html` - 삭제 (백업: base_site.html.backup)

## 원 상태로 복구하는 방법

### 1. base_site.html 복구
```bash
cp templates/admin/base_site.html.backup templates/admin/base_site.html
```

### 2. settings.py에서 unfold 제거

INSTALLED_APPS에서 다음 3줄 제거:
```python
'unfold',  # Django Unfold - must be before django.contrib.admin
'unfold.contrib.filters',  # Unfold filters
'unfold.contrib.forms',  # Unfold forms
```

파일 끝의 UNFOLD 설정 전체 삭제:
```python
# Django Unfold Admin 설정
UNFOLD = {
    ...
}
```

### 3. requirements.txt에서 django-unfold 제거
```
django-unfold
```
이 줄을 삭제

### 4. Docker 재빌드
```bash
docker-compose down
docker-compose up -d --build
```

## 빠른 복구 스크립트

```bash
# base_site.html 복구
cp templates/admin/base_site.html.backup templates/admin/base_site.html

# Git으로 settings.py와 requirements.txt 복구 (커밋 전이라면)
git checkout badmintok/settings.py
git checkout requirements.txt

# Docker 재빌드
docker-compose down
docker-compose up -d --build
```
