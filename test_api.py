#!/usr/bin/env python3
"""
배드민톡 API 테스트 스크립트

사용법:
    python test_api.py                    # 프로덕션 테스트
    python test_api.py --local            # 로컬 테스트
    python test_api.py --endpoint posts   # 특정 엔드포인트만 테스트
"""

import requests
import json
import sys
from typing import Dict, Any

# 색상 출력용
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def test_endpoint(base_url: str, endpoint: str, params: Dict = None) -> bool:
    """API 엔드포인트 테스트"""
    url = f"{base_url}{endpoint}"

    print_info(f"테스트 중: {url}")
    if params:
        print_info(f"파라미터: {params}")

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print_success(f"성공 (200 OK)")
            print(f"  응답 크기: {len(json.dumps(data))} bytes")

            # 응답 데이터 미리보기
            if isinstance(data, dict):
                if 'results' in data:
                    print(f"  결과 개수: {len(data['results'])}개")
                    if data['results']:
                        print(f"  첫 번째 항목 키: {list(data['results'][0].keys())}")
                elif 'latest_posts' in data:
                    print(f"  최신 게시물: {len(data['latest_posts'])}개")
                elif 'hot_posts' in data:
                    print(f"  인기 게시물: {len(data['hot_posts'])}개")
                elif 'banners' in data:
                    print(f"  배너: {len(data['banners'])}개")
                else:
                    print(f"  응답 키: {list(data.keys())[:5]}")
            elif isinstance(data, list):
                print(f"  배열 길이: {len(data)}개")

            print()
            return True
        else:
            print_error(f"실패 ({response.status_code})")
            print(f"  응답: {response.text[:200]}")
            print()
            return False

    except requests.exceptions.Timeout:
        print_error("타임아웃 (10초)")
        print()
        return False
    except requests.exceptions.ConnectionError:
        print_error("연결 실패")
        print()
        return False
    except Exception as e:
        print_error(f"오류: {str(e)}")
        print()
        return False

def main():
    # 커맨드 라인 인자 파싱
    args = sys.argv[1:]
    is_local = '--local' in args
    specific_endpoint = None

    for arg in args:
        if arg.startswith('--endpoint='):
            specific_endpoint = arg.split('=')[1]

    # Base URL 설정
    base_url = "http://localhost:8000/api/" if is_local else "https://badmintok.com/api/"

    print("=" * 60)
    print(f"배드민톡 API 테스트")
    print(f"환경: {'로컬 (localhost)' if is_local else '프로덕션 (badmintok.com)'}")
    print(f"Base URL: {base_url}")
    print("=" * 60)
    print()

    # 테스트할 엔드포인트 정의
    tests = [
        # (엔드포인트, 파라미터, 설명)
        # === Badmintok API ===
        ("", None, "홈 - 최신 게시물 5개"),
        ("badmintok/posts/", None, "배드민톡 게시물 목록"),
        ("badmintok/posts/", {"page": 1, "page_size": 5}, "배드민톡 게시물 (페이지 1, 5개)"),
        ("badmintok/hot-posts/", None, "배드민톡 인기 게시물 TOP 10"),

        # === Community API ===
        ("community/posts/", None, "동호인톡 게시물 목록"),
        ("community/posts/", {"tab": "hot"}, "동호인톡 HOT 탭"),
        ("community/posts/", {"search": "배드민턴"}, "동호인톡 게시물 검색"),
        ("community/categories/", None, "동호인톡 카테고리 목록"),

        # === Contests API ===
        ("contests/", None, "대회 목록"),
        ("contests/", {"period": "upcoming"}, "예정된 대회 (30일 이내)"),
        ("contests/", {"order": "popular"}, "인기 대회순"),
        ("contests/hot/", None, "인기 대회 TOP 10"),
        ("contests/categories/", None, "대회 분류 목록"),

        # === Band API ===
        ("bands/", None, "밴드 목록"),
        ("bands/", {"band_type": "flash"}, "번개 목록"),
        ("bands/hot/", None, "인기 밴드 TOP 10"),

        # === Common Resources ===
        ("banners/", None, "배너 목록"),
        ("notices/", None, "공지사항 목록"),
    ]

    # 특정 엔드포인트만 테스트
    if specific_endpoint:
        tests = [t for t in tests if t[0].startswith(specific_endpoint)]
        if not tests:
            print_error(f"'{specific_endpoint}' 엔드포인트를 찾을 수 없습니다.")
            return

    # 테스트 실행
    results = []
    for endpoint, params, description in tests:
        print(f"[{description}]")
        success = test_endpoint(base_url, endpoint, params)
        results.append((description, success))

    # 결과 요약
    print("=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    success_count = sum(1 for _, success in results if success)
    total_count = len(results)

    for description, success in results:
        if success:
            print_success(description)
        else:
            print_error(description)

    print()
    print(f"성공: {success_count}/{total_count}")

    if success_count == total_count:
        print_success("모든 테스트 통과! 🎉")
    else:
        print_warning(f"{total_count - success_count}개 테스트 실패")

if __name__ == "__main__":
    main()
