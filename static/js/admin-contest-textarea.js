(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        // 글자수 표시할 textarea 필드들
        const textareaIds = [
            'id_description',
            'id_participant_target',
            'id_award_reward_text'
        ];

        textareaIds.forEach(function(id) {
            const textarea = document.getElementById(id);
            if (!textarea) return;

            // 글자수 표시용 div 생성
            const counterDiv = document.createElement('div');
            counterDiv.className = 'textarea-counter';
            counterDiv.style.marginTop = '4px';
            counterDiv.style.fontSize = '12px';
            counterDiv.style.color = '#666';

            // textarea 다음에 추가
            textarea.parentNode.insertBefore(counterDiv, textarea.nextSibling);

            function updateCounter() {
                const length = textarea.value.length;
                counterDiv.textContent = `${length}자`;
            }

            // 이벤트 리스너
            textarea.addEventListener('input', updateCounter);
            textarea.addEventListener('paste', function() {
                setTimeout(updateCounter, 0);
            });

            // 초기 카운터 업데이트
            updateCounter();
        });
    });
})();
