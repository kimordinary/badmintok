#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check visitor statistics for duplicates and bot traffic"""

from badmintok.models import VisitorLog
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

now = timezone.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
week_start = today_start - timedelta(days=7)

print("=" * 50)
print("오늘 통계 분석")
print("=" * 50)

# 오늘 통계
total_logs = VisitorLog.objects.filter(visited_at__gte=today_start).count()
unique_sessions = VisitorLog.objects.filter(visited_at__gte=today_start).values("session_key").distinct().count()
bot_visits = VisitorLog.objects.filter(visited_at__gte=today_start, device_type="bot").count()
real_users = VisitorLog.objects.filter(visited_at__gte=today_start).exclude(device_type="bot").values("session_key").distinct().count()

print(f"전체 방문 로그: {total_logs}건")
print(f"고유 세션 수 (현재 표시되는 방문자): {unique_sessions}명")
print(f"봇 방문: {bot_visits}건 ({round(bot_visits/total_logs*100, 1) if total_logs > 0 else 0}%)")
print(f"실제 사용자 방문 (봇 제외): {real_users}명")

print("\n" + "=" * 50)
print("디바이스별 통계 (오늘)")
print("=" * 50)
device_stats = VisitorLog.objects.filter(
    visited_at__gte=today_start
).values('device_type').annotate(
    count=Count('id')
).order_by('-count')

for d in device_stats:
    print(f"{d['device_type']}: {d['count']}건")

print("\n" + "=" * 50)
print("최근 7일 통계 분석")
print("=" * 50)

total_logs_week = VisitorLog.objects.filter(visited_at__gte=week_start).count()
unique_sessions_week = VisitorLog.objects.filter(visited_at__gte=week_start).values("session_key").distinct().count()
bot_visits_week = VisitorLog.objects.filter(visited_at__gte=week_start, device_type="bot").count()
real_users_week = VisitorLog.objects.filter(visited_at__gte=week_start).exclude(device_type="bot").values("session_key").distinct().count()

print(f"전체 방문 로그: {total_logs_week}건")
print(f"고유 세션 수 (현재 표시되는 방문자): {unique_sessions_week}명")
print(f"봇 방문: {bot_visits_week}건 ({round(bot_visits_week/total_logs_week*100, 1) if total_logs_week > 0 else 0}%)")
print(f"실제 사용자 방문 (봇 제외): {real_users_week}명")

# 샘플 봇 로그 확인
print("\n" + "=" * 50)
print("최근 봇 방문 기록 샘플 (최근 5개)")
print("=" * 50)
bot_samples = VisitorLog.objects.filter(device_type="bot").order_by('-visited_at')[:5]
for log in bot_samples:
    print(f"{log.visited_at.strftime('%Y-%m-%d %H:%M:%S')} | {log.url_path} | {log.user_agent[:50]}...")

# 중복 세션 체크
print("\n" + "=" * 50)
print("중복이 많은 세션 TOP 5 (오늘)")
print("=" * 50)
duplicate_sessions = VisitorLog.objects.filter(
    visited_at__gte=today_start
).values('session_key').annotate(
    count=Count('id')
).order_by('-count')[:5]

for session in duplicate_sessions:
    print(f"세션키: {session['session_key'][:20]}... | 방문 횟수: {session['count']}회")
