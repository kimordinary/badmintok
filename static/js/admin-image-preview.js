(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        initImagePreviews();

        // Inline formset 동적 추가 시 이벤트 처리
        document.addEventListener('click', function(e) {
            if (e.target.matches('.add-row a, .add-row button')) {
                setTimeout(initImagePreviews, 100);
            }
        });
    });

    function initImagePreviews() {
        // ContestImage 인라인의 모든 이미지 입력 필드 찾기
        const imageInputs = document.querySelectorAll('input[type="file"][name*="image"]');

        imageInputs.forEach(function(input) {
            // 이미 이벤트가 등록된 경우 스킵
            if (input.dataset.previewInitialized) return;
            input.dataset.previewInitialized = 'true';

            input.addEventListener('change', function(e) {
                handleImagePreview(e.target);
            });
        });
    }

    function handleImagePreview(input) {
        const file = input.files[0];
        if (!file) return;

        // 이미지 파일 타입 체크
        if (!file.type.startsWith('image/')) return;

        // 같은 row 내의 미리보기 셀 찾기
        const row = input.closest('tr.form-row');
        if (!row) {
            // row가 없으면 기존 방식 사용
            fallbackPreview(input, file);
            return;
        }

        // field-image_preview 셀 찾기
        const previewCell = row.querySelector('td.field-image_preview');
        if (!previewCell) {
            // 미리보기 셀이 없으면 기존 방식 사용
            fallbackPreview(input, file);
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            // 미리보기 셀 내의 readonly div 찾기
            const readonlyDiv = previewCell.querySelector('.readonly');

            if (readonlyDiv) {
                // 기존 "-" 텍스트를 이미지로 교체
                readonlyDiv.innerHTML = `
                    <img src="${e.target.result}"
                         style="max-height: 80px; max-width: 120px; object-fit: contain;"
                         alt="미리보기" />
                `;
            } else {
                // readonly div가 없으면 직접 추가
                const container = previewCell.querySelector('.flex');
                if (container) {
                    container.innerHTML = `
                        <img src="${e.target.result}"
                             style="max-height: 80px; max-width: 120px; object-fit: contain; border-radius: 4px;"
                             alt="미리보기" />
                    `;
                }
            }
        };
        reader.readAsDataURL(file);
    }

    function fallbackPreview(input, file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            // 기존 live-preview 제거
            const existingPreview = input.parentNode.querySelector('.live-preview');
            if (existingPreview) {
                existingPreview.remove();
            }

            // 미리보기 컨테이너 생성
            const previewContainer = document.createElement('div');
            previewContainer.className = 'live-preview';
            previewContainer.style.cssText = 'margin-top: 8px;';
            previewContainer.innerHTML = `
                <img src="${e.target.result}"
                     style="max-height: 120px; max-width: 180px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px; padding: 4px; background: #f9f9f9;"
                     alt="미리보기" />
            `;
            input.parentNode.appendChild(previewContainer);
        };
        reader.readAsDataURL(file);
    }
})();
