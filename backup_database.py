#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
데이터베이스 백업 스크립트
스키마와 데이터를 모두 백업합니다.
"""
import os
import sys
import json
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'badmintok.settings')
django.setup()

from django.core.management import call_command
from django.core import serializers
from django.db import connection
from io import StringIO
import codecs

def backup_data():
    """데이터 백업"""
    print("데이터 백업 중...")
    output = StringIO()
    
    try:
        # 모든 앱의 데이터 백업
        call_command('dumpdata', 
                    exclude=['contenttypes', 'auth.Permission', 'sessions'],
                    indent=2,
                    stdout=output,
                    use_natural_foreign_keys=True,
                    use_natural_primary_keys=False)
        
        # UTF-8로 파일 저장
        with codecs.open('backup_data.json', 'w', encoding='utf-8') as f:
            f.write(output.getvalue())
        
        print("✓ 데이터 백업 완료: backup_data.json")
        return True
    except Exception as e:
        print(f"✗ 데이터 백업 실패: {e}")
        # 개별 앱별로 백업 시도
        apps = ['accounts', 'band', 'community', 'contests', 'badmintok']
        all_data = []
        
        for app in apps:
            try:
                output = StringIO()
                call_command('dumpdata', app, indent=2, stdout=output)
                data = json.loads(output.getvalue())
                all_data.extend(data)
                print(f"✓ {app} 앱 데이터 백업 완료")
            except Exception as app_error:
                print(f"✗ {app} 앱 백업 실패: {app_error}")
        
        if all_data:
            with codecs.open('backup_data.json', 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print("✓ 통합 데이터 백업 완료: backup_data.json")
            return True
        
        return False

def backup_schema():
    """스키마 백업 (SQL)"""
    print("스키마 백업 중...")
    
    try:
        with codecs.open('backup_schema.sql', 'w', encoding='utf-8') as f:
            # 모든 마이그레이션의 SQL 생성
            from django.core.management import call_command
            from io import StringIO
            
            apps = ['accounts', 'band', 'community', 'contests', 'badmintok', 'admin', 'auth', 'contenttypes', 'sessions']
            
            for app in apps:
                try:
                    # 앱의 모든 마이그레이션 파일 찾기
                    import os
                    from django.apps import apps as django_apps
                    
                    app_config = django_apps.get_app_config(app.split('.')[-1] if '.' in app else app)
                    migrations_path = os.path.join(app_config.path, 'migrations')
                    
                    if os.path.exists(migrations_path):
                        migration_files = [f for f in os.listdir(migrations_path) 
                                         if f.endswith('.py') and f != '__init__.py']
                        
                        for migration_file in sorted(migration_files):
                            migration_name = migration_file[:-3]  # .py 제거
                            try:
                                output = StringIO()
                                call_command('sqlmigrate', app, migration_name, stdout=output)
                                sql = output.getvalue()
                                if sql.strip():
                                    f.write(f"\n-- Migration: {app}.{migration_name}\n")
                                    f.write(sql)
                                    f.write("\n")
                            except Exception as mig_error:
                                pass  # 마이그레이션 파일이 없거나 이미 적용된 경우 무시
                except Exception as app_error:
                    pass  # 앱이 없으면 무시
            
            print("✓ 스키마 백업 완료: backup_schema.sql")
            return True
    except Exception as e:
        print(f"✗ 스키마 백업 실패: {e}")
        return False

def backup_table_structure():
    """테이블 구조 백업 (SHOW CREATE TABLE)"""
    print("테이블 구조 백업 중...")
    
    try:
        with codecs.open('backup_table_structure.sql', 'w', encoding='utf-8') as f:
            cursor = connection.cursor()
            
            # 모든 테이블 목록 가져오기
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            f.write("-- 테이블 구조 백업\n")
            f.write(f"-- 생성일: {django.utils.timezone.now()}\n\n")
            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")
            
            for table in tables:
                try:
                    cursor.execute(f"SHOW CREATE TABLE `{table}`")
                    result = cursor.fetchone()
                    if result:
                        f.write(f"-- Table structure for table `{table}`\n")
                        f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                        f.write(f"{result[1]};\n\n")
                except Exception as table_error:
                    print(f"  ⚠ 테이블 {table} 구조 백업 실패: {table_error}")
            
            f.write("SET FOREIGN_KEY_CHECKS=1;\n")
            
            print("✓ 테이블 구조 백업 완료: backup_table_structure.sql")
            return True
    except Exception as e:
        print(f"✗ 테이블 구조 백업 실패: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("데이터베이스 백업 시작")
    print("=" * 50)
    
    # 데이터 백업
    data_success = backup_data()
    
    # 스키마 백업
    schema_success = backup_schema()
    
    # 테이블 구조 백업
    structure_success = backup_table_structure()
    
    print("=" * 50)
    print("백업 완료")
    print("=" * 50)
    print(f"데이터 백업: {'✓' if data_success else '✗'}")
    print(f"스키마 백업: {'✓' if schema_success else '✗'}")
    print(f"테이블 구조 백업: {'✓' if structure_success else '✗'}")
    
    if data_success or structure_success:
        print("\n백업 파일:")
        if data_success:
            print("  - backup_data.json (데이터)")
        if structure_success:
            print("  - backup_table_structure.sql (테이블 구조)")
        if schema_success:
            print("  - backup_schema.sql (마이그레이션 SQL)")
