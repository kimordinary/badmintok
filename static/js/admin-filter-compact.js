/**
 * Admin 필터 사이드바를 상단으로 이동하고 컴팩트하게 만들기
 */

(function() {
    'use strict';

    function initCompactFilter() {
        const filterContainer = document.querySelector('#changelist-filter');
        if (!filterContainer) {
            return;
        }

        // 필터를 검색란 바로 아래로 이동
        const changelistFormContainer = document.querySelector('.changelist-form-container');
        const toolbar = document.querySelector('#toolbar');
        
        if (changelistFormContainer && toolbar) {
            // toolbar 다음에 필터 삽입
            toolbar.parentNode.insertBefore(filterContainer, toolbar.nextSibling);
        } else if (changelistFormContainer) {
            // changelist-form-container 내부의 첫 번째 요소로 배치
            if (changelistFormContainer.firstChild) {
                changelistFormContainer.insertBefore(filterContainer, changelistFormContainer.firstChild);
            } else {
                changelistFormContainer.appendChild(filterContainer);
            }
        }

        // details 태그들을 가로로 배치하기 위한 wrapper 생성
        const detailsElements = filterContainer.querySelectorAll('details');
        if (detailsElements.length > 0) {
            // details들을 감싸는 wrapper div 생성
            const wrapper = document.createElement('div');
            wrapper.className = 'filter-details-wrapper';
            wrapper.style.cssText = 'display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start;';
            
            // extra-actions 다음에 wrapper 삽입
            const extraActions = filterContainer.querySelector('#changelist-filter-extra-actions');
            if (extraActions && extraActions.nextSibling) {
                filterContainer.insertBefore(wrapper, extraActions.nextSibling);
            } else {
                const h2 = filterContainer.querySelector('h2');
                if (h2 && h2.nextSibling) {
                    filterContainer.insertBefore(wrapper, h2.nextSibling);
                } else {
                    filterContainer.appendChild(wrapper);
                }
            }
            
            // 모든 details를 wrapper로 이동
            detailsElements.forEach((details, index) => {
                wrapper.appendChild(details);
                // 첫 번째 details만 열어두기
                if (index > 0) {
                    details.removeAttribute('open');
                }
            });
        }

        // 필터 컨테이너를 더 컴팩트하게
        filterContainer.style.maxWidth = '100%';
        filterContainer.style.width = '100%';
    }

    // 페이지 로드 시 초기화
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCompactFilter);
    } else {
        initCompactFilter();
    }
})();
