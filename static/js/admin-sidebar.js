(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const sidebar = document.getElementById('nav-sidebar');
        if (!sidebar) return;

        // 각 모듈(앱 그룹)에 아코디언 기능 추가
        const modules = sidebar.querySelectorAll('.module');

        modules.forEach(function(module) {
            const caption = module.querySelector('caption');
            const tbody = module.querySelector('tbody');

            if (!caption || !tbody) return;

            // caption을 클릭 가능하게 만들기
            caption.style.cursor = 'pointer';
            caption.classList.add('accordion-header');

            // 토글 아이콘 추가
            const toggleIcon = document.createElement('span');
            toggleIcon.className = 'accordion-icon';
            toggleIcon.innerHTML = '▼';
            caption.appendChild(toggleIcon);

            // 클릭 이벤트
            caption.addEventListener('click', function(e) {
                e.preventDefault();

                const isCollapsed = tbody.classList.contains('collapsed');

                if (isCollapsed) {
                    // 펼치기
                    tbody.classList.remove('collapsed');
                    toggleIcon.innerHTML = '▼';
                    caption.classList.remove('collapsed');
                } else {
                    // 접기
                    tbody.classList.add('collapsed');
                    toggleIcon.innerHTML = '▶';
                    caption.classList.add('collapsed');
                }

                // localStorage에 상태 저장
                saveAccordionState();
            });
        });

        // 저장된 상태 복원
        restoreAccordionState();

        function saveAccordionState() {
            const state = {};
            modules.forEach(function(module, index) {
                const tbody = module.querySelector('tbody');
                if (tbody) {
                    state[index] = tbody.classList.contains('collapsed');
                }
            });
            localStorage.setItem('adminSidebarAccordion', JSON.stringify(state));
        }

        function restoreAccordionState() {
            const saved = localStorage.getItem('adminSidebarAccordion');
            if (!saved) return;

            try {
                const state = JSON.parse(saved);
                modules.forEach(function(module, index) {
                    const tbody = module.querySelector('tbody');
                    const caption = module.querySelector('caption');
                    const toggleIcon = caption ? caption.querySelector('.accordion-icon') : null;

                    if (tbody && state[index]) {
                        tbody.classList.add('collapsed');
                        if (caption) caption.classList.add('collapsed');
                        if (toggleIcon) toggleIcon.innerHTML = '▶';
                    }
                });
            } catch (e) {
                // 파싱 에러 무시
            }
        }
    });
})();
