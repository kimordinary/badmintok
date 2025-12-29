#!/usr/bin/env python
"""
Django 관리자 계정 생성 스크립트
사용법: python create_admin.py
또는: docker-compose -f docker-compose.prod.yml exec web python create_admin.py
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'badmintok.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin():
    """로컬 개발용 관리자 계정 생성"""
    email = "admin@localhost.com"
    activity_name = "관리자"
    password = "admin1234"
    
    # 이미 존재하는지 확인
    if User.objects.filter(email=email).exists():
        print(f"이미 존재하는 계정입니다: {email}")
        print("비밀번호를 변경하시겠습니까? (y/n): ", end="")
        response = input().strip().lower()
        if response == 'y':
            user = User.objects.get(email=email)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            print(f"비밀번호가 변경되었습니다: {password}")
        return
    
    # 새 관리자 계정 생성
    try:
        user = User.objects.create_superuser(
            email=email,
            activity_name=activity_name,
            password=password
        )
        print("=" * 50)
        print("관리자 계정이 생성되었습니다!")
        print("=" * 50)
        print(f"이메일: {email}")
        print(f"활동명: {activity_name}")
        print(f"비밀번호: {password}")
        print("=" * 50)
        print(f"\n관리자 페이지: http://localhost/admin/")
        print("=" * 50)
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)

if __name__ == '__main__':
    create_admin()

