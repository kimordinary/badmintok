"""탭 카테고리 자동 생성 기능 테스트"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "badmintok.settings")
django.setup()

from community.models import Tab, Category

print("=== Testing Auto Category Creation ===\n")

# 1. 테스트용 탭 생성 (카테고리 없이)
print("1. Creating test tab without category...")
test_tab = Tab.objects.create(
    name="테스트탭",
    slug="test-auto",
    source=Tab.Source.COMMUNITY,
    display_order=999,
    is_active=True
)
print(f"   Created tab: {test_tab.name} (slug: {test_tab.slug})")
print(f"   Initial category: {test_tab.category}")

# 2. 탭 다시 로드해서 카테고리 확인
print("\n2. Reloading tab to check auto-created category...")
test_tab.refresh_from_db()
print(f"   Tab after save: {test_tab.name}")
print(f"   Category: {test_tab.category}")

# 3. 카테고리가 실제로 생성되었는지 확인
if test_tab.category:
    print(f"   Category name: {test_tab.category.name}")
    print(f"   Category slug: {test_tab.category.slug}")
    print(f"   Category is_active: {test_tab.category.is_active}")
    print("\n   SUCCESS: Category was auto-created and linked!")
else:
    print("\n   FAILED: Category was not created!")

# 4. 정리 (생성한 탭과 카테고리 삭제)
print("\n3. Cleaning up test data...")
if test_tab.category:
    category = test_tab.category
    test_tab.delete()
    # 카테고리에 연결된 다른 탭이 없으면 삭제
    if not Tab.objects.filter(category=category).exists():
        category.delete()
        print("   Deleted test category")
else:
    test_tab.delete()

print("   Deleted test tab")
print("\n=== Test Complete ===")
