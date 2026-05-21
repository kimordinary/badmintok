"""방문자 추적 미들웨어"""
import hashlib
import re
from urllib.parse import urlparse

from django.utils import timezone


class VisitorTrackingMiddleware:
    """방문자 로그를 기록하는 미들웨어 - 젯팩 스타일 통계"""

    def __init__(self, get_response):
        self.get_response = get_response

        # 봇 패턴 (User-Agent에서 봇 감지)
        # 자동화 도구·헤드리스 브라우저·HTTP 클라이언트 라이브러리까지 포괄
        self.bot_patterns = re.compile(
            r'bot|crawler|spider|scraper|slurp|'
            r'headless|phantom|selenium|playwright|puppeteer|'
            r'curl|wget|python-requests|axios|node-fetch|httpclient|okhttp|'
            r'uptimerobot|pingdom|datadog|newrelic|^$',
            re.IGNORECASE
        )

        # 제외할 URL 패턴 (사용자 콘텐츠 페이지뷰가 아닌 것)
        # 주의: /app은 사용자 의도 액션이라 포함 (별도 AppDownloadClick에도 기록되지만 OK)
        self.exclude_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/api/',                # API 호출은 페이지뷰 아님
            '/favicon.ico',
            '/robots.txt',
            '/sitemap.xml',
            '/sw.js',
            '/manifest.json',
            '/ads.txt',
            '/.well-known/',        # 인증서 검증 등 자동 호출
        ]

    def __call__(self, request):
        # 요청 처리 전
        response = self.get_response(request)

        # 요청 처리 후 - 방문 로그 기록
        if self._should_track(request, response):
            self._log_visit(request)

        return response

    def _should_track(self, request, response):
        """로그를 기록할지 여부 판단"""
        # GET 요청만 기록
        if request.method != 'GET':
            return False

        # 200, 301, 302 응답만 기록
        if response.status_code not in [200, 301, 302]:
            return False

        # 제외할 경로 체크
        path = request.path
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False

        # localhost 및 내부 IP 제외
        ip_address = self._get_client_ip(request)
        if self._is_internal_ip(ip_address):
            return False

        # referer가 localhost인 경우 제외
        referer = request.META.get('HTTP_REFERER', '')
        if referer and ('localhost' in referer or '127.0.0.1' in referer):
            return False

        # 봇이면 기록 안 함 (DB 용량 절감)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if self._detect_device_type(user_agent) == 'bot':
            return False

        return True

    def _log_visit(self, request):
        """방문 로그 기록"""
        from .models import VisitorLog

        # IP 주소 추출
        ip_address = self._get_client_ip(request)

        # User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # 세션 키: 이미 있으면 사용, 없으면 IP+UA 기반 합성 키 사용
        # (세션을 강제 생성하면 익명 사용자가 매 요청마다 새 unique visitor로 잡혀
        #  인플레이션이 크고 django_session 테이블도 무의미하게 부풀어 오름)
        session_key = request.session.session_key
        if not session_key:
            fingerprint = f"{ip_address or 'unknown'}|{user_agent[:200]}"
            session_key = 'anon_' + hashlib.md5(fingerprint.encode('utf-8')).hexdigest()[:30]

        # URL 경로
        url_path = request.path

        # 리퍼러 정보
        referer = request.META.get('HTTP_REFERER', '')
        referer_domain = ''
        if referer:
            parsed = urlparse(referer)
            referer_domain = parsed.netloc

        # 디바이스 타입 판별
        device_type = self._detect_device_type(user_agent)

        # 사용자 (로그인한 경우)
        user = request.user if request.user.is_authenticated else None

        # 로그 생성
        try:
            VisitorLog.objects.create(
                user=user,
                session_key=session_key,
                ip_address=ip_address,
                url_path=url_path,
                referer=referer[:500],  # 최대 길이 제한
                referer_domain=referer_domain[:200],
                user_agent=user_agent[:500],
                device_type=device_type,
            )
        except Exception as e:
            # 로그 기록 실패 시 무시 (애플리케이션 동작에 영향 없도록)
            pass

    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _is_internal_ip(self, ip):
        """내부 IP인지 확인 (localhost, 사설 IP 등)"""
        if not ip:
            return False

        # localhost 및 루프백
        if ip in ['localhost', '127.0.0.1', '::1']:
            return True

        # 사설 IP 대역 체크
        # 10.x.x.x
        if ip.startswith('10.'):
            return True

        # 172.16.x.x ~ 172.31.x.x
        if ip.startswith('172.'):
            try:
                second_octet = int(ip.split('.')[1])
                if 16 <= second_octet <= 31:
                    return True
            except (IndexError, ValueError):
                pass

        # 192.168.x.x
        if ip.startswith('192.168.'):
            return True

        return False

    def _detect_device_type(self, user_agent):
        """User-Agent로부터 디바이스 타입 판별"""
        user_agent_lower = user_agent.lower()

        # 봇 감지
        if self.bot_patterns.search(user_agent):
            return 'bot'

        # 모바일 감지
        mobile_patterns = ['mobile', 'android', 'iphone', 'ipod', 'blackberry', 'windows phone']
        if any(pattern in user_agent_lower for pattern in mobile_patterns):
            return 'mobile'

        # 태블릿 감지
        tablet_patterns = ['ipad', 'tablet', 'kindle']
        if any(pattern in user_agent_lower for pattern in tablet_patterns):
            return 'tablet'

        # 기본값: 데스크톱
        return 'desktop'
