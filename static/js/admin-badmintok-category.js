/**
 * 배드민톡 Admin 페이지에서 탭 기반 카테고리 필터링
 */

(function() {
    'use strict';

    // 배드민톡 카테고리 매핑
    const BADMINTOK_CATEGORIES = {
        'news': ['tournament', 'player', 'equipment', 'community'],
        'reviews': ['racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories'],
        'brand': ['yonex', 'lining', 'victor', 'mizuno', 'technist', 'strokus', 'redsun', 'trion', 'tricore', 'apacs'],
        'feed': []
    };

    // 카테고리 slug와 이름 매핑
    const CATEGORY_NAMES = {
        // 뉴스
        'tournament': '대회 소식',
        'player': '선수 소식',
        'equipment': '장비 뉴스',
        'community': '동호인 소식',
        // 리뷰
        'racket': '라켓',
        'shoes': '신발/가방',
        'apparel': '의류',
        'shuttlecock': '셔틀콕',
        'protective': '보호대',
        'accessories': '기타/용품',
        // 브랜드관
        'yonex': '요넥스',
        'lining': '리닝',
        'victor': '빅터',
        'mizuno': '미즈노',
        'technist': '테크니스트',
        'strokus': '스트로커스',
        'redsun': '레드선',
        'trion': '트라이온',
        'tricore': '트리코어',
        'apacs': '아펙스'
    };

    function initBadmintokCategoryFilter() {
        // 배드민톡 게시글 작성/수정 페이지인지 확인
        const categoryField = document.querySelector('#id_category');
        if (!categoryField) {
            return; // category 필드가 없으면 종료
        }

        // source 필드가 badmintok인지 확인
        const sourceField = document.querySelector('#id_source');
        if (sourceField && sourceField.value !== 'badmintok') {
            return; // 배드민톡 글이 아니면 종료
        }

        // 탭 선택 필드 생성
        const categoryFieldRow = categoryField.closest('.form-row');
        if (!categoryFieldRow) {
            return;
        }

        // 탭 선택 필드 추가
        const tabFieldRow = document.createElement('div');
        tabFieldRow.className = 'form-row';
        tabFieldRow.innerHTML = `
            <div>
                <label for="id_badmintok_tab" style="display: block; margin-bottom: 8px; font-weight: 600;">1단계 탭 선택:</label>
                <select id="id_badmintok_tab" name="badmintok_tab" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    <option value="">-- 탭을 선택하세요 --</option>
                    <option value="news">뉴스</option>
                    <option value="reviews">리뷰</option>
                    <option value="brand">브랜드관</option>
                    <option value="feed">피드</option>
                </select>
            </div>
        `;

        // category 필드 앞에 삽입
        categoryFieldRow.parentNode.insertBefore(tabFieldRow, categoryFieldRow);

        // category 필드 레이블 수정
        const categoryLabel = categoryFieldRow.querySelector('label[for="id_category"]');
        if (categoryLabel) {
            categoryLabel.textContent = '2단계 카테고리 선택:';
        }

        // 기존 카테고리 값으로 탭 자동 선택
        if (categoryField.value) {
            const categoryData = window.BADMINTOK_CATEGORY_DATA || [];
            const categoryMap = {};
            if (categoryData.length > 0) {
                categoryData.forEach(cat => {
                    categoryMap[cat.id] = cat.slug;
                });
            }
            
            const selectedCategoryId = categoryField.value;
            const categorySlug = categoryMap[selectedCategoryId];
            
            if (categorySlug) {
                // 카테고리 slug로 탭 찾기
                for (const [tab, categories] of Object.entries(BADMINTOK_CATEGORIES)) {
                    if (categories.includes(categorySlug)) {
                        document.getElementById('id_badmintok_tab').value = tab;
                        break;
                    }
                }
            } else {
                // 카테고리 데이터가 없으면 텍스트로 매칭
                const selectedCategory = categoryField.options[categoryField.selectedIndex];
                if (selectedCategory) {
                    const categoryText = selectedCategory.textContent.trim();
                    for (const [tab, categories] of Object.entries(BADMINTOK_CATEGORIES)) {
                        const found = categories.some(slug => {
                            const categoryName = CATEGORY_NAMES[slug];
                            return categoryName && categoryText.includes(categoryName);
                        });
                        if (found) {
                            document.getElementById('id_badmintok_tab').value = tab;
                            break;
                        }
                    }
                }
            }
        }

        // 탭 변경 시 카테고리 필터링
        const tabSelect = document.getElementById('id_badmintok_tab');
        tabSelect.addEventListener('change', function() {
            filterCategoriesByTab(this.value);
        });

        // 초기 로드 시 필터링
        if (tabSelect.value) {
            filterCategoriesByTab(tabSelect.value);
        } else {
            // 탭이 선택되지 않았으면 모든 카테고리 숨김 (하지만 필드 자체는 활성화)
            filterCategoriesByTab('');
        }
    }

    function filterCategoriesByTab(selectedTab) {
        const categoryField = document.querySelector('#id_category');
        if (!categoryField) {
            return;
        }

        const allowedSlugs = BADMINTOK_CATEGORIES[selectedTab] || [];
        
        // 카테고리 필드는 항상 활성화 (피드 탭 제외)
        if (selectedTab === 'feed') {
            // 피드 탭에서는 카테고리 필드 비활성화
            categoryField.disabled = true;
            categoryField.value = '';
            // 피드 탭에서는 모든 옵션 숨김
            Array.from(categoryField.options).forEach((option, index) => {
                if (index === 0) {
                    option.style.display = '';
                    option.disabled = false;
                } else {
                    option.style.display = 'none';
                    option.disabled = true;
                }
            });
            return;
        } else {
            // 다른 탭에서는 필드 활성화
            categoryField.disabled = false;
            categoryField.style.pointerEvents = 'auto';
        }

        // 탭이 선택되지 않았으면 모든 카테고리 숨김 (하지만 필드는 활성화)
        if (!selectedTab) {
            categoryField.disabled = false;
            categoryField.style.pointerEvents = 'auto';
            Array.from(categoryField.options).forEach((option, index) => {
                if (index === 0) {
                    option.style.display = '';
                    option.disabled = false;
                } else {
                    option.style.display = 'none';
                    option.disabled = true;
                }
            });
            return;
        }

        // 카테고리 데이터가 있으면 사용, 없으면 옵션 텍스트로 매칭
        const categoryData = window.BADMINTOK_CATEGORY_DATA || [];
        const categoryMap = {};
        if (categoryData.length > 0) {
            categoryData.forEach(cat => {
                categoryMap[cat.id] = cat.slug;
            });
        }

        // 디버깅을 위한 로그
        console.log('필터링 시작:', {
            selectedTab: selectedTab,
            allowedSlugs: allowedSlugs,
            categoryDataLength: categoryData.length,
            categoryMap: categoryMap
        });

        // 옵션 필터링
        let visibleCount = 0;
        Array.from(categoryField.options).forEach((option, index) => {
            if (index === 0) {
                // 첫 번째 옵션(빈 값)은 항상 표시
                option.style.display = '';
                option.disabled = false;
                return;
            }

            const optionValue = option.value;
            if (!optionValue) {
                option.style.display = '';
                option.disabled = false;
                return;
            }

            // 카테고리 slug 확인
            let categorySlug = null;
            const optionText = option.textContent.trim();
            
            if (categoryMap[optionValue]) {
                // 카테고리 데이터에서 slug 가져오기
                categorySlug = categoryMap[optionValue];
            }
            
            // slug로 매칭 시도
            let isAllowed = false;
            if (categorySlug && allowedSlugs.includes(categorySlug)) {
                isAllowed = true;
            } else {
                // slug 매칭 실패 시 카테고리 이름으로 매칭
                for (const [slug, name] of Object.entries(CATEGORY_NAMES)) {
                    if (allowedSlugs.includes(slug) && optionText.includes(name)) {
                        isAllowed = true;
                        break;
                    }
                }
            }
            
            if (isAllowed) {
                option.style.display = '';
                option.disabled = false;
                visibleCount++;
            } else {
                option.style.display = 'none';
                option.disabled = true;
                // 현재 선택된 카테고리가 필터링되면 선택 해제
                if (categoryField.value === optionValue) {
                    categoryField.value = '';
                }
            }
        });
        
        console.log('필터링 완료. 표시된 카테고리 수:', visibleCount);
    }

    // 페이지 로드 시 초기화
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBadmintokCategoryFilter);
    } else {
        initBadmintokCategoryFilter();
    }
})();
