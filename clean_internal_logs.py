#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Clean internal IP and localhost visitor logs"""

from badmintok.models import VisitorLog
from django.db.models import Q

print("=" * 70)
print("Cleaning internal IP visitor logs")
print("=" * 70)

# 삭제 대상 찾기
internal_logs = VisitorLog.objects.filter(
    Q(referer_domain='localhost') |
    Q(referer_domain__startswith='172.') |
    Q(referer_domain__startswith='192.168.') |
    Q(referer_domain__startswith='10.') |
    Q(ip_address='127.0.0.1') |
    Q(ip_address='::1') |
    Q(ip_address__startswith='172.') |
    Q(ip_address__startswith='192.168.') |
    Q(ip_address__startswith='10.')
)

count = internal_logs.count()
print(f"\nFound {count} internal visitor logs to delete")

if count > 0:
    # 샘플 보여주기
    print("\nSample of logs to be deleted (first 5):")
    for log in internal_logs[:5]:
        print(f"  - {log.visited_at.strftime('%Y-%m-%d %H:%M')} | IP: {log.ip_address} | Referer: {log.referer_domain}")

    print(f"\n{'='*70}")
    print("Do you want to delete these logs? (yes/no)")
    confirmation = input("> ").strip().lower()

    if confirmation in ['yes', 'y']:
        deleted_count = internal_logs.delete()[0]
        print(f"\n✓ Successfully deleted {deleted_count} internal visitor logs")
    else:
        print("\nCancelled. No logs were deleted.")
else:
    print("\nNo internal logs found. Nothing to delete.")

print("\n" + "=" * 70)
print("Current statistics:")
print("=" * 70)

from django.utils import timezone
from datetime import timedelta

now = timezone.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
week_start = today_start - timedelta(days=7)

total_logs = VisitorLog.objects.count()
today_visitors = VisitorLog.objects.filter(visited_at__gte=today_start).values('session_key').distinct().count()
week_visitors = VisitorLog.objects.filter(visited_at__gte=week_start).values('session_key').distinct().count()

print(f"Total visitor logs: {total_logs}")
print(f"Today's unique visitors: {today_visitors}")
print(f"This week's unique visitors: {week_visitors}")
