/**
 * 모바일 오버레이 클릭 차단 방지 유틸리티
 * 
 * 이 스크립트는 모바일 메뉴 오버레이가 화면을 덮어서 클릭을 막는 문제를 방지합니다.
 * 특정 페이지에서 오버레이를 완전히 비활성화해야 할 때 사용합니다.
 */

(function() {
    'use strict';
    
    // 모바일 감지 함수
    function isMobile() {
        return window.matchMedia("(max-width: 1024px)").matches;
    }
    
    // 오버레이 완전 제거 함수
    function killOverlay() {
        const overlay = document.getElementById('mobileMenuOverlay');
        if (overlay) {
            overlay.remove(); // DOM에서 완전히 제거
        }
        const mobileMenu = document.getElementById('mobileMenu');
        if (mobileMenu) {
            mobileMenu.classList.remove('active');
            mobileMenu.style.transform = 'translateX(-100%)';
        }
        if (document.body) {
            document.body.style.overflow = '';
            document.body.style.pointerEvents = 'auto';
        }
    }
    
    // 모바일 메뉴 토글 버튼 비활성화
    function disableMobileMenuToggle() {
        const mobileMenuToggle = document.getElementById('mobileMenuToggle');
        if (mobileMenuToggle && isMobile()) {
            // 기존 이벤트 리스너 제거를 위해 클론
            const newToggle = mobileMenuToggle.cloneNode(true);
            mobileMenuToggle.parentNode.replaceChild(newToggle, mobileMenuToggle);
            // 빈 핸들러로 대체 (capture phase에서 실행하여 base.html 스크립트보다 먼저 실행)
            newToggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                killOverlay();
            }, true);
        }
    }
    
    // 전역 함수로 export
    window.MobileOverlayFix = {
        kill: killOverlay,
        disableToggle: disableMobileMenuToggle,
        isMobile: isMobile
    };
    
    // body에 disable-mobile-overlay 클래스가 있으면 자동으로 비활성화
    if (isMobile() && document.body && document.body.classList.contains('disable-mobile-overlay')) {
        // 즉시 실행
        killOverlay();
        disableMobileMenuToggle();
        
        // MutationObserver로 오버레이가 다시 추가되면 즉시 제거
        const observer = new MutationObserver(function(mutations) {
            if (!isMobile()) return;
            
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        if (node.id === 'mobileMenuOverlay' || (node.querySelector && node.querySelector('#mobileMenuOverlay'))) {
                            killOverlay();
                        }
                    }
                });
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const overlay = document.getElementById('mobileMenuOverlay');
                    if (overlay && overlay.classList.contains('active')) {
                        killOverlay();
                    }
                }
            });
        });
        
        function startObserving() {
            if (document.body) {
                observer.observe(document.body, { 
                    childList: true, 
                    subtree: true, 
                    attributes: true, 
                    attributeFilter: ['class'] 
                });
            }
        }
        
        if (document.body) {
            startObserving();
        } else {
            document.addEventListener('DOMContentLoaded', startObserving);
        }
        
        // DOMContentLoaded 전에도 실행
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                killOverlay();
                disableMobileMenuToggle();
            }, { once: true });
        }
        
        // 주기적으로 확인 (매우 빠르게)
        setInterval(function() {
            if (isMobile()) {
                killOverlay();
                disableMobileMenuToggle();
            }
        }, 20);
        
        // 리사이즈 시 재확인
        window.addEventListener('resize', function() {
            if (isMobile()) {
                killOverlay();
                disableMobileMenuToggle();
            }
        });
    }
})();

