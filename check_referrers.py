#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check where visitors are coming from"""

from badmintok.models import VisitorLog
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

now = timezone.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
week_start = today_start - timedelta(days=7)

print("=" * 70)
print("Where are visitors coming from? (Last 7 days)")
print("=" * 70)

# Count by referer source
direct_visits = VisitorLog.objects.filter(
    visited_at__gte=week_start,
    referer=''
).values('session_key').distinct().count()

search_visits = VisitorLog.objects.filter(
    visited_at__gte=week_start,
    referer_domain__icontains='google'
).values('session_key').distinct().count() + VisitorLog.objects.filter(
    visited_at__gte=week_start,
    referer_domain__icontains='naver'
).values('session_key').distinct().count()

other_referrers = VisitorLog.objects.filter(
    visited_at__gte=week_start
).exclude(referer='').exclude(
    referer_domain__icontains='google'
).exclude(
    referer_domain__icontains='naver'
).values('session_key').distinct().count()

total = VisitorLog.objects.filter(visited_at__gte=week_start).values('session_key').distinct().count()

print(f"Direct visits (no referer): {direct_visits} ({round(direct_visits/total*100,1) if total > 0 else 0}%)")
print(f"From search engines: {search_visits} ({round(search_visits/total*100,1) if total > 0 else 0}%)")
print(f"From other sources: {other_referrers} ({round(other_referrers/total*100,1) if total > 0 else 0}%)")
print(f"Total unique visitors: {total}")

print("\n" + "=" * 70)
print("Top referer domains (Last 7 days)")
print("=" * 70)

top_referrers = VisitorLog.objects.filter(
    visited_at__gte=week_start,
    referer_domain__isnull=False
).exclude(
    referer_domain=''
).values('referer_domain').annotate(
    count=Count('id')
).order_by('-count')[:10]

if top_referrers:
    for idx, ref in enumerate(top_referrers, 1):
        print(f"{idx}. {ref['referer_domain']}: {ref['count']} visits")
else:
    print("No external referrers found")

print("\n" + "=" * 70)
print("Sample of direct visits (no referer) - Last 10")
print("=" * 70)

direct_samples = VisitorLog.objects.filter(
    visited_at__gte=today_start,
    referer=''
).order_by('-visited_at')[:10]

for log in direct_samples:
    print(f"{log.visited_at.strftime('%H:%M:%S')} | {log.url_path} | {log.device_type}")

print("\n" + "=" * 70)
print("IP address distribution (today)")
print("=" * 70)

ip_distribution = VisitorLog.objects.filter(
    visited_at__gte=today_start
).values('ip_address').annotate(
    count=Count('id')
).order_by('-count')[:10]

for idx, ip in enumerate(ip_distribution, 1):
    print(f"{idx}. IP: {ip['ip_address']}: {ip['count']} visits")
