(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const startInput = document.getElementById('id_schedule_start');
        const endInput = document.getElementById('id_schedule_end');
        if (!startInput || !endInput) return;

        // "경기 일정 자동 생성" 버튼을 schedule_end 필드 옆에 추가
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = '경기일정 자동 생성';
        btn.style.cssText = 'margin-left: 12px; padding: 6px 14px; font-size: 13px; font-weight: 600; color: #fff; background: #31AA60; border: none; border-radius: 6px; cursor: pointer;';
        btn.addEventListener('mouseenter', function() { btn.style.opacity = '0.85'; });
        btn.addEventListener('mouseleave', function() { btn.style.opacity = '1'; });

        // 대회 일정 fieldset 아래에 버튼 삽입
        const fieldRow = endInput.closest('.field-row') || endInput.closest('.form-row');
        if (fieldRow) {
            const btnWrapper = document.createElement('div');
            btnWrapper.style.cssText = 'padding: 0 12px 12px 12px;';
            btnWrapper.appendChild(btn);
            fieldRow.parentNode.insertBefore(btnWrapper, fieldRow.nextSibling);
        }

        btn.addEventListener('click', function() {
            const startVal = startInput.value;
            const endVal = endInput.value || startVal;

            if (!startVal) {
                alert('대회 시작일을 먼저 입력해주세요.');
                return;
            }

            // 날짜 범위 계산
            const start = parseDate(startVal);
            const end = parseDate(endVal);
            if (!start || !end || start > end) {
                alert('대회 일정을 올바르게 입력해주세요.');
                return;
            }

            const dates = [];
            for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
                dates.push(formatDate(new Date(d)));
            }

            // 기존 경기일정 인라인 확인
            const totalFormsInput = document.querySelector('[name="schedules-TOTAL_FORMS"]');
            if (!totalFormsInput) return;

            // 이미 입력된 날짜 수집
            const existingDates = new Set();
            const totalForms = parseInt(totalFormsInput.value);
            for (let i = 0; i < totalForms; i++) {
                const dateInput = document.getElementById('id_schedules-' + i + '-date');
                const deleteCheckbox = document.getElementById('id_schedules-' + i + '-DELETE');
                if (dateInput && dateInput.value && !(deleteCheckbox && deleteCheckbox.checked)) {
                    existingDates.add(dateInput.value);
                }
            }

            // 추가할 날짜 (이미 존재하는 날짜 제외)
            const newDates = dates.filter(function(d) { return !existingDates.has(d); });

            if (newDates.length === 0) {
                alert('이미 모든 날짜가 추가되어 있습니다.');
                return;
            }

            // "경기 일정 더 추가하기" 링크 찾기
            const addLink = document.querySelector('#schedules-empty')
                && document.querySelector('#schedules-empty').closest('tbody')
                && document.querySelector('#schedules-empty').closest('tbody').querySelector('.add-row a');

            if (!addLink) {
                alert('경기일정 추가 버튼을 찾을 수 없습니다.');
                return;
            }

            // 각 날짜에 대해 행 추가
            newDates.forEach(function(dateStr) {
                // 추가 버튼 클릭
                addLink.click();

                // 새로 생성된 행의 날짜 필드에 값 입력
                var newIndex = parseInt(totalFormsInput.value) - 1;
                var newDateInput = document.getElementById('id_schedules-' + newIndex + '-date');
                if (newDateInput) {
                    newDateInput.value = dateStr;
                }
            });

            alert(newDates.length + '일의 경기일정이 추가되었습니다. 아래에서 종목과 연령대를 선택해주세요.');
        });

        function parseDate(str) {
            var parts = str.split('-');
            if (parts.length === 3) {
                return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            }
            return null;
        }

        function formatDate(d) {
            var year = d.getFullYear();
            var month = ('0' + (d.getMonth() + 1)).slice(-2);
            var day = ('0' + d.getDate()).slice(-2);
            return year + '-' + month + '-' + day;
        }
    });
})();
