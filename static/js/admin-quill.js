// Admin용 Quill 에디터 초기화 스크립트
// .js-quill-editor 클래스를 가진 textarea를 찾아 Quill 에디터로 변환합니다.

(function() {
  // CSRF 토큰 쿠키에서 가져오기 (Django 전용)
  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function initAdminQuillEditors() {
    if (typeof Quill === 'undefined') {
      console.warn('Quill 이 로드되지 않았습니다.');
      return;
    }

    var textareas = document.querySelectorAll('textarea.js-quill-editor');
    if (!textareas.length) {
      return;
    }

    textareas.forEach(function(textarea) {
      // 이미 초기화된 경우 스킵
      if (textarea.dataset.quillInitialized === '1') {
        return;
      }

      var wrapper = document.createElement('div');
      wrapper.style.marginTop = '8px';

      var editorDiv = document.createElement('div');
      editorDiv.className = 'admin-quill-editor';
      editorDiv.style.minHeight = '300px';

      // textarea 숨기고, 그 앞에 에디터 컨테이너 삽입
      textarea.style.display = 'none';
      textarea.parentNode.insertBefore(wrapper, textarea);
      wrapper.appendChild(editorDiv);
      wrapper.appendChild(textarea);

      // Quill 초기 데이터 설정
      var initialHtml = textarea.value || '';

      var quill = new Quill(editorDiv, {
        theme: 'snow',
        modules: {
          toolbar: {
            container: [
              ['bold', 'italic', 'underline', 'strike'],
              [{ 'header': [1, 2, 3, false] }],
              [{ 'list': 'ordered' }, { 'list': 'bullet' }],
              [{ 'indent': '-1' }, { 'indent': '+1' }],
              ['link', 'blockquote', 'code-block', 'image'],
              [{ 'color': [] }, { 'background': [] }],
              ['clean']
            ],
            handlers: {
              image: function() {
                var fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = 'image/*';
                fileInput.style.display = 'none';
                document.body.appendChild(fileInput);

                fileInput.addEventListener('change', function() {
                  var file = fileInput.files[0];
                  if (!file) {
                    document.body.removeChild(fileInput);
                    return;
                  }

                  var formData = new FormData();
                  formData.append('image', file);

                  var xhr = new XMLHttpRequest();
                  xhr.open('POST', '/admin/quill-upload/');
                  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

                  var csrfToken = getCookie('csrftoken');
                  if (csrfToken) {
                    xhr.setRequestHeader('X-CSRFToken', csrfToken);
                  }

                  xhr.onload = function() {
                    try {
                      if (xhr.status === 200) {
                        var resp = JSON.parse(xhr.responseText);
                        if (resp.url) {
                          var range = quill.getSelection(true) || { index: quill.getLength() };
                          quill.insertEmbed(range.index, 'image', resp.url, 'user');
                          quill.setSelection(range.index + 1);
                        }
                      } else {
                        console.error('이미지 업로드 실패:', xhr.status, xhr.responseText);
                        alert('이미지 업로드에 실패했습니다.');
                      }
                    } catch (e) {
                      console.error('이미지 업로드 응답 처리 중 오류:', e);
                    }
                    document.body.removeChild(fileInput);
                  };

                  xhr.onerror = function() {
                    console.error('이미지 업로드 중 네트워크 오류');
                    alert('이미지 업로드 중 오류가 발생했습니다.');
                    document.body.removeChild(fileInput);
                  };

                  xhr.send(formData);
                });

                fileInput.click();
              }
            }
          }
        }
      });

      if (initialHtml) {
        quill.clipboard.dangerouslyPasteHTML(initialHtml);
      }

      // 폼 제출 시 Quill 내용을 textarea에 반영
      var form = textarea.form;
      if (form && !form.__quillBound) {
        form.__quillBound = true;
        form.addEventListener('submit', function() {
          var editors = form.querySelectorAll('textarea.js-quill-editor');
          editors.forEach(function(ta) {
            if (ta.__quillInstance) {
              ta.value = ta.__quillInstance.root.innerHTML;
            }
          });
        });
      }

      // textarea에 인스턴스 저장
      textarea.__quillInstance = quill;
      textarea.dataset.quillInitialized = '1';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminQuillEditors);
  } else {
    initAdminQuillEditors();
  }
})();
