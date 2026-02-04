(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', function() {
        const slugInput = document.getElementById('id_slug');
        if (!slugInput) return;
        
        // URL 구조: https://badmintok.com/badminton-tournament/슬러그
        const BASE_URL_LENGTH = 'https://badmintok.com/badminton-tournament/'.length; // 43자
        const MAX_TOTAL_URL_LENGTH = 80; // 전체 URL 최대 길이
        const MAX_SLUG_LENGTH = MAX_TOTAL_URL_LENGTH - BASE_URL_LENGTH; // 슬러그 최대 길이 (37자)
        const RECOMMENDED_MIN = 70; // 전체 URL 권장 최소 길이
        const RECOMMENDED_MAX = 80; // 전체 URL 권장 최대 길이
        
        // 기존 help text 찾기
        const helpText = document.getElementById('id_slug_helptext');
        if (!helpText) return;
        
        // 글자수 표시를 위한 div 생성
        const counterDiv = document.createElement('div');
        counterDiv.id = 'slug-counter';
        counterDiv.style.marginTop = '8px';
        counterDiv.style.fontSize = '13px';
        counterDiv.style.color = '#666';
        
        // 권장 메시지를 위한 div 생성
        const recommendationDiv = document.createElement('div');
        recommendationDiv.id = 'slug-recommendation';
        recommendationDiv.style.marginTop = '4px';
        recommendationDiv.style.fontSize = '12px';
        recommendationDiv.style.color = '#666';
        
        // help text 다음에 추가
        helpText.parentNode.insertBefore(counterDiv, helpText.nextSibling);
        counterDiv.parentNode.insertBefore(recommendationDiv, counterDiv.nextSibling);
        
        // 초기 설정
        slugInput.setAttribute('maxlength', MAX_SLUG_LENGTH);
        
        function updateCounter() {
            const slugLength = slugInput.value.length;
            const totalUrlLength = BASE_URL_LENGTH + slugLength;
            const remainingTotal = MAX_TOTAL_URL_LENGTH - totalUrlLength;
            const remainingSlug = MAX_SLUG_LENGTH - slugLength;
            
            // 남은 글자수 표시 (전체 URL 기준)
            counterDiv.textContent = `남은 글자수: ${remainingTotal}자 (슬러그: ${slugLength}자/${MAX_SLUG_LENGTH}자, 전체 URL: ${totalUrlLength}자/${MAX_TOTAL_URL_LENGTH}자)`;
            
            // 권장 메시지 표시 (전체 URL 기준)
            if (totalUrlLength === BASE_URL_LENGTH) {
                recommendationDiv.textContent = `권장: 전체 URL이 ${RECOMMENDED_MIN}-${RECOMMENDED_MAX}자 내외가 되도록 작성하세요.`;
                recommendationDiv.style.color = '#666';
            } else if (totalUrlLength < RECOMMENDED_MIN) {
                recommendationDiv.textContent = `권장: 전체 URL이 ${RECOMMENDED_MIN}-${RECOMMENDED_MAX}자 내외가 되도록 작성하세요. (현재 전체 URL: ${totalUrlLength}자)`;
                recommendationDiv.style.color = '#f59e0b';
            } else if (totalUrlLength >= RECOMMENDED_MIN && totalUrlLength <= RECOMMENDED_MAX) {
                recommendationDiv.textContent = `✓ 적절한 길이입니다. (전체 URL: ${totalUrlLength}자)`;
                recommendationDiv.style.color = '#10b981';
            } else {
                recommendationDiv.textContent = `⚠ 전체 URL이 ${RECOMMENDED_MAX}자를 초과했습니다. (${totalUrlLength}자)`;
                recommendationDiv.style.color = '#ef4444';
            }
        }
        
        // 입력 이벤트 리스너
        slugInput.addEventListener('input', function(e) {
            const slugLength = e.target.value.length;
            const totalUrlLength = BASE_URL_LENGTH + slugLength;
            
            // 전체 URL이 80자 초과 시 입력 차단
            if (totalUrlLength > MAX_TOTAL_URL_LENGTH) {
                e.target.value = e.target.value.substring(0, MAX_SLUG_LENGTH);
            }
            
            updateCounter();
        });
        
        // 키보드 이벤트로도 차단 (복사/붙여넣기 등 대비)
        slugInput.addEventListener('keydown', function(e) {
            const slugLength = e.target.value.length;
            const totalUrlLength = BASE_URL_LENGTH + slugLength;
            
            // 백스페이스, Delete, 화살표 키 등은 허용
            if (e.key === 'Backspace' || e.key === 'Delete' || 
                e.key.startsWith('Arrow') || e.key === 'Home' || e.key === 'End' ||
                (e.ctrlKey && (e.key === 'a' || e.key === 'c' || e.key === 'v' || e.key === 'x'))) {
                return;
            }
            
            // 전체 URL이 80자에 도달했으면 입력 차단
            if (totalUrlLength >= MAX_TOTAL_URL_LENGTH) {
                e.preventDefault();
                return false;
            }
        });
        
        // 붙여넣기 이벤트 처리
        slugInput.addEventListener('paste', function(e) {
            setTimeout(function() {
                const slugLength = slugInput.value.length;
                const totalUrlLength = BASE_URL_LENGTH + slugLength;
                if (totalUrlLength > MAX_TOTAL_URL_LENGTH) {
                    slugInput.value = slugInput.value.substring(0, MAX_SLUG_LENGTH);
                }
                updateCounter();
            }, 0);
        });
        
        // 초기 카운터 업데이트
        updateCounter();
    });
})();
