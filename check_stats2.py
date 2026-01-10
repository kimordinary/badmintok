#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Detailed check for visitor statistics"""

from badmintok.models import VisitorLog
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

now = timezone.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

print("=" * 70)
print("Top 10 sessions with most visits today")
print("=" * 70)

duplicate_sessions = VisitorLog.objects.filter(
    visited_at__gte=today_start
).values('session_key', 'device_type', 'user_agent').annotate(
    visit_count=Count('id')
).order_by('-visit_count')[:10]

for idx, session in enumerate(duplicate_sessions, 1):
    ua = session['user_agent'][:80] if session['user_agent'] else 'N/A'
    print(f"{idx}. Session: {session['session_key'][:30]}")
    print(f"   Device: {session['device_type']} | Visits: {session['visit_count']}")
    print(f"   User-Agent: {ua}")
    print()

print("=" * 70)
print("Recent 10 visitor logs (today)")
print("=" * 70)

recent_logs = VisitorLog.objects.filter(
    visited_at__gte=today_start
).order_by('-visited_at')[:10]

for log in recent_logs:
    ua = log.user_agent[:60] if log.user_agent else 'N/A'
    print(f"{log.visited_at.strftime('%H:%M:%S')} | {log.device_type:8} | {log.url_path}")
    print(f"  UA: {ua}")
    print()

print("=" * 70)
print("Check for bot patterns in user agents")
print("=" * 70)

import re
bot_patterns = re.compile(r'bot|crawler|spider|scraper|slurp|google|bing|yahoo|baidu', re.IGNORECASE)

all_logs_today = VisitorLog.objects.filter(visited_at__gte=today_start)
potential_bots = 0

for log in all_logs_today:
    if bot_patterns.search(log.user_agent):
        potential_bots += 1
        if potential_bots <= 5:  # Show first 5
            print(f"Potential bot detected: {log.user_agent[:100]}")

print(f"\nTotal potential bots found: {potential_bots} out of {all_logs_today.count()}")
