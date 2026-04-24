# 웹민턴 모임/동호회 사이트 관리자 권한 부여 설계

## 배경

웹민턴(band 앱)의 모임/동호회는 내부 역할(owner/admin/member) 기반으로 권한을 제어한다. 사이트 전체 관리자(`is_staff` 또는 `is_superuser`)는 현재 모임 생성 제한을 우회하는 일부 로직만 있고, 모임 내부 관리 기능(수정/삭제/멤버 관리/글 관리 등)에 대한 우회 권한이 없다. 이로 인해 운영상 필요한 상황(스팸 모임 정리, 잠수 모임장 대체, 약관 위반 글 삭제 등)에서 관리자가 직접 개입할 수 없다.

## 목표

- 사이트 관리자는 모든 모임에 대해 모임장(owner)과 동일한 작업을 수행 가능
- 앱 UI는 관리자 권한으로 접근 중임을 명확히 표시
- 기존 일반 유저의 권한 체크는 변경하지 않음
- 최상위 관리자(superuser)의 실명은 웹민턴 내 어디에서도 노출되지 않도록 고정

## 결정 사항

### 관리자 식별 기준
`is_staff=True OR is_superuser=True` 중 하나라도 만족하면 사이트 관리자로 취급.

### 우회 범위
모임장(owner) 및 관리자(admin) 역할이 수행하는 모든 작업을 허용:
- 모임 정보 수정 / 삭제 / 공개 범위 변경
- 가입 신청 승인·거절, 멤버 강퇴, 역할 변경
- 모임 내 게시글·댓글 수정·삭제, 고정, 공지 설정
- 투표·번개 생성·수정·종료

### 앱 UI 방침 (투명한 관리자 모드)
- 관리자가 비회원 상태로 모임에 진입 시 가입 버튼은 그대로 노출
- "관리자 권한으로 접근 중" 배지 별도 표시
- 편집/삭제/멤버 관리 등 관리 UI는 `is_site_admin` 플래그로 조건부 노출
- 멤버 리스트에는 관리자가 표시되지 않음 (실제 가입하지 않았기 때문)

### 작성자 표시
관리자가 작성한 게시글·댓글은 평소처럼 본인의 `activity_name`으로 표시. 별도 "[관리자]" 같은 접두사 없음.

### 실명 마스킹
`is_superuser=True`인 유저의 `real_name` property는 무조건 `activity_name`을 반환하도록 변경.
- 웹민턴 템플릿 3곳(band/schedule_detail.html, band/post_detail.html, band/detail.html)과 band API serializer(band/api/serializers.py)가 모두 `real_name`을 사용하므로 property 한 곳 수정으로 전역 반영.
- `is_staff`만 있는 유저는 영향 없음 (일반 스태프는 실제 실명 노출 유지).

## 아키텍처

### 1. 헬퍼 함수 (신규)
`accounts/permissions.py`:
```python
def is_site_admin(user):
    """사이트 관리자 여부. 모임/동호회 운영에 한해 owner와 동급으로 취급."""
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_staff or user.is_superuser)
```

### 2. 실명 property 수정
`accounts/models.py`의 `User.real_name`:
```python
@property
def real_name(self):
    if self.is_superuser:
        return self.activity_name
    profile = getattr(self, "profile", None)
    if profile and profile.name:
        return profile.name
    return self.activity_name
```

### 3. band 권한 체크 패치 패턴
기존 코드:
```python
member = BandMember.objects.filter(
    band=band, user=request.user,
    role__in=['owner', 'admin'], status='active'
).first()
if not member:
    return Response({'error': '권한 없음'}, status=403)
```

패치 후:
```python
from accounts.permissions import is_site_admin

if not is_site_admin(request.user):
    member = BandMember.objects.filter(
        band=band, user=request.user,
        role__in=['owner', 'admin'], status='active'
    ).first()
    if not member:
        return Response({'error': '권한 없음'}, status=403)
```

owner 단독 체크(예: 모임 삭제, 모임장 위임)도 동일 패턴으로 관리자 우회.

### 4. API 응답 확장
모임 상세 API에 필드 추가:
- `is_site_admin: bool` — 요청 유저가 사이트 관리자인가
- `can_manage: bool` — 기존 멤버 role OR 사이트 관리자 OR (일부 API에서만) 모임 created_by

### 5. 예외 케이스
| 상황 | 처리 |
|---|---|
| 관리자가 가입 안 한 모임에 글 작성 | `BandPost.author`는 해당 관리자 User. 표시는 `activity_name` |
| 관리자가 모임장 위임 | 위임 대상은 멤버 중에서만 선택 가능 (관리자는 제외) |
| 관리자가 모임 삭제 | 삭제 허용. 소유권 이전 없이 완전 삭제 |
| 관리자 본인 '탈퇴' | 관리자는 멤버가 아니므로 탈퇴 개념 없음 |
| 조회 권한 (비공개 모임) | 관리자는 모든 비공개 모임도 조회 가능 |

## 영향 범위

### 서버 작업
- `accounts/permissions.py` — 신규 파일
- `accounts/models.py` — `real_name` property 수정
- `band/views.py` — role 체크 25곳 패치
- `band/api/views.py` — role 체크 20곳 패치
- `band/api/serializers.py` — 상세 serializer에 `is_site_admin`, `can_manage` 필드 추가

### 앱 작업 (별도 PR)
- 모임 상세 응답의 `is_site_admin` 소비
- 관리자 배지 UI 추가
- 편집/삭제/멤버 관리 버튼 표시 조건에 `|| is_site_admin` 추가
- 서버 작업 완료 후 상세 작업 목록 전달

### 범위 외
- community 앱 (이미 `is_staff` 우회 적용됨)
- 감사 로그 (Django admin LogEntry로 커버)
- 자동화 테스트 (band 앱 테스트 부재, 이번엔 수동 검증)

## 검증

- `python manage.py check` 통과
- 로컬 서버 기동 후 관리자 계정으로 가입 안 한 모임에 대해:
  - 모임 수정·삭제 가능 확인
  - 멤버 관리 페이지 접근 가능 확인
  - 모임 내 게시글·댓글 삭제 가능 확인
- 일반 유저는 기존대로 권한 없을 시 403 반환 확인
- 실명 마스킹: superuser 계정으로 band 관련 페이지 접속 후 `activity_name` 표시 확인
