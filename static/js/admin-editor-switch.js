/**
 * Django Admin에서 source 필드 변경에 따라 에디터를 동적으로 전환
 * - source='badmintok' → Editor.js
 * - 그 외 → Quill
 */

(function() {
    'use strict';

    function switchEditor() {
        const sourceField = document.querySelector('select[name="source"]');
        const contentField = document.querySelector('textarea[name="content"]');
        
        if (!sourceField || !contentField) {
            return;
        }

        const sourceValue = sourceField.value;
        const isBadmintok = sourceValue === 'badmintok';
        
        // Quill 에디터 영역
        const quillWrapper = contentField.parentElement.querySelector('.admin-quill-editor');
        const quillInstance = contentField.__quillInstance;
        
        // Editor.js 영역
        const editorjsContainer = document.getElementById(`editorjs-${contentField.name}`);
        const editorjsInstance = window.editorInstances && window.editorInstances[contentField.name];

        if (isBadmintok) {
            // 배드민톡 → Editor.js 사용
            // Quill 숨기기
            if (quillWrapper) {
                quillWrapper.style.display = 'none';
            }
            contentField.style.display = 'none';
            
            // Editor.js 컨테이너가 없으면 생성
            if (!editorjsContainer) {
                const container = document.createElement('div');
                container.id = `editorjs-${contentField.name}`;
                container.className = 'editorjs-container';
                contentField.parentElement.insertBefore(container, contentField);
            } else {
                editorjsContainer.style.display = 'block';
            }

            // Editor.js가 아직 초기화되지 않았다면 초기화
            if (!editorjsInstance) {
                console.log('Editor.js 초기화 시작...');
                // Editor.js 로드 대기
                function waitForEditorJS(retries = 20) {
                    if (typeof EditorJS !== 'undefined') {
                        console.log('EditorJS 로드 확인됨, initEditorJS 호출');
                        initEditorJS(contentField);
                    } else if (retries > 0) {
                        setTimeout(() => waitForEditorJS(retries - 1), 100);
                    } else {
                        console.error('EditorJS를 로드할 수 없습니다.');
                    }
                }
                waitForEditorJS();
            } else {
                console.log('Editor.js 이미 초기화됨');
            }
        } else {
            // 그 외 → Quill 사용
            // Editor.js 숨기기
            if (editorjsContainer) {
                editorjsContainer.style.display = 'none';
            }
            
            // Quill 표시
            if (quillWrapper) {
                quillWrapper.style.display = 'block';
            }
            contentField.style.display = 'none';
            
            // Quill이 아직 초기화되지 않았다면 초기화
            if (!quillInstance && typeof Quill !== 'undefined') {
                initQuill(contentField);
            }
        }
    }

    function initEditorJS(textarea) {
        const containerId = `editorjs-${textarea.name}`;
        const container = document.getElementById(containerId);
        
        if (!container || typeof EditorJS === 'undefined') {
            console.warn('Editor.js 또는 컨테이너를 찾을 수 없습니다.');
            return;
        }

        // 플러그인 확인 및 로드 대기
        function waitForPlugins(callback, retries = 50) {
            // CDN에서 로드된 플러그인 확인 (여러 가능한 경로 시도)
            // UMD 번들은 보통 window에 플러그인 이름으로 노출됨
            const plugins = {};
            
            // Header 플러그인 확인
            if (window.Header) {
                plugins.Header = window.Header;
            } else if (window.HeaderTool) {
                plugins.Header = window.HeaderTool;
            }
            
            // List 플러그인 확인
            if (window.List) {
                plugins.List = window.List;
            } else if (window.ListTool) {
                plugins.List = window.ListTool;
            }
            
            // Image 플러그인 확인
            if (window.Image) {
                plugins.Image = window.Image;
            } else if (window.ImageTool) {
                plugins.Image = window.ImageTool;
            }
            
            // Quote 플러그인 확인
            if (window.Quote) {
                plugins.Quote = window.Quote;
            } else if (window.QuoteTool) {
                plugins.Quote = window.QuoteTool;
            }
            
            // CodeTool 플러그인 확인
            if (window.CodeTool) {
                plugins.CodeTool = window.CodeTool;
            } else if (window.Code) {
                plugins.CodeTool = window.Code;
            }
            
            // Delimiter 플러그인 확인
            if (window.Delimiter) {
                plugins.Delimiter = window.Delimiter;
            } else if (window.DelimiterTool) {
                plugins.Delimiter = window.DelimiterTool;
            }
            
            // Paragraph 플러그인 확인 (필수)
            if (window.Paragraph) {
                plugins.Paragraph = window.Paragraph;
            } else if (window.ParagraphTool) {
                plugins.Paragraph = window.ParagraphTool;
            }

            console.log('플러그인 확인 시도:', {
                Header: !!plugins.Header,
                List: !!plugins.List,
                Image: !!plugins.Image,
                Quote: !!plugins.Quote,
                CodeTool: !!plugins.CodeTool,
                Delimiter: !!plugins.Delimiter,
                Paragraph: !!plugins.Paragraph,
            });
            
            // window 객체 전체 확인 (디버깅용)
            console.log('window 객체에서 Editor.js 관련:', Object.keys(window).filter(k => 
                k.includes('Editor') || k.includes('Header') || k.includes('List') || 
                k.includes('Image') || k.includes('Quote') || k.includes('Code') || 
                k.includes('Delimiter') || k.includes('Paragraph')
            ));

            // 최소한 Paragraph는 있어야 함 (필수)
            // 없어도 일단 시도 (Editor.js가 기본 Paragraph를 제공할 수 있음)
            if (retries === 0 || plugins.Paragraph) {
                console.log('플러그인 로드 완료, Editor.js 초기화 시작');
                callback(plugins);
            } else {
                setTimeout(() => waitForPlugins(callback, retries - 1), 100);
            }
        }

        waitForPlugins(function(plugins) {
            console.log('플러그인 로드 상태:', plugins);
            
            // 기존 값 파싱
            let initialData = null;
            if (textarea.value) {
                try {
                    initialData = JSON.parse(textarea.value);
                } catch (e) {
                    initialData = {
                        blocks: [{
                            type: 'paragraph',
                            data: {
                                text: textarea.value.replace(/<[^>]*>/g, '')
                            }
                        }]
                    };
                }
            }

            // tools 객체 생성 (undefined 제외)
            // 플러그인이 없어도 Editor.js는 기본 Paragraph를 제공하므로 최소한 작동함
            const tools = {};
            
            if (plugins.Header) {
                tools.header = {
                    class: plugins.Header,
                    config: {
                        placeholder: '제목을 입력하세요',
                        levels: [2, 3, 4],
                        defaultLevel: 2
                    }
                };
            }
            
            if (plugins.List) {
                tools.list = {
                    class: plugins.List,
                    inlineToolbar: true,
                    config: {
                        defaultStyle: 'unordered'
                    }
                };
            }
            
            if (plugins.Image) {
                tools.image = {
                    class: plugins.Image,
                    config: {
                        endpoints: {
                            byFile: '/admin/editorjs-upload/',
                        },
                        field: 'image',
                        types: 'image/*',
                        captionPlaceholder: '이미지 설명을 입력하세요',
                        buttonContent: '이미지 추가',
                        uploader: {
                            async uploadByFile(file) {
                                const formData = new FormData();
                                formData.append('image', file);
                                
                                const csrfToken = getCookie('csrftoken');
                                const response = await fetch('/admin/editorjs-upload/', {
                                    method: 'POST',
                                    body: formData,
                                    headers: {
                                        'X-CSRFToken': csrfToken
                                    }
                                });

                                if (!response.ok) {
                                    throw new Error('이미지 업로드 실패');
                                }

                                const result = await response.json();
                                if (result.success === 1) {
                                    return result;
                                } else {
                                    throw new Error(result.message || '이미지 업로드 실패');
                                }
                            }
                        }
                    }
                };
            }
            
            if (plugins.Quote) {
                tools.quote = {
                    class: plugins.Quote,
                    inlineToolbar: true,
                    shortcut: 'CMD+SHIFT+O',
                    config: {
                        quotePlaceholder: '인용구를 입력하세요',
                        captionPlaceholder: '출처를 입력하세요'
                    }
                };
            }
            
            if (plugins.CodeTool) {
                tools.code = {
                    class: plugins.CodeTool,
                    config: {
                        placeholder: '코드를 입력하세요'
                    }
                };
            }
            
            if (plugins.Delimiter) {
                tools.delimiter = plugins.Delimiter;
            }
            
            if (plugins.Paragraph) {
                tools.paragraph = {
                    class: plugins.Paragraph,
                    inlineToolbar: true
                };
            }

            console.log('Editor.js tools:', tools);
            console.log('tools 객체 키:', Object.keys(tools));

            // Editor.js 초기화
            try {
                const editor = new EditorJS({
                    holder: containerId,
                    data: initialData,
                    tools: Object.keys(tools).length > 0 ? tools : undefined, // tools가 비어있으면 기본 사용
                    placeholder: '내용을 입력하세요...',
                    autofocus: false,
                    readOnly: false
                });
                
                console.log('Editor.js 초기화 성공!');
                
                // 인스턴스 저장
                if (!window.editorInstances) {
                    window.editorInstances = {};
                }
                window.editorInstances[textarea.name] = editor;

                // 폼 제출 시 데이터 저장
                const form = textarea.closest('form');
                if (form) {
                    form.addEventListener('submit', async function(e) {
                        try {
                            const outputData = await editor.save();
                            textarea.value = JSON.stringify(outputData);
                            console.log('Editor.js 데이터 저장 완료');
                        } catch (error) {
                            console.error('Editor.js 저장 실패:', error);
                        }
                    }, { once: true });
                }
            } catch (error) {
                console.error('Editor.js 초기화 실패:', error);
                alert('에디터 초기화에 실패했습니다. 콘솔을 확인해주세요.');
            }

        });
    }

    function initQuill(textarea) {
        if (typeof Quill === 'undefined' || textarea.dataset.quillInitialized === '1') {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.style.marginTop = '8px';

        const editorDiv = document.createElement('div');
        editorDiv.className = 'admin-quill-editor';
        editorDiv.style.minHeight = '300px';

        textarea.style.display = 'none';
        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.appendChild(editorDiv);
        wrapper.appendChild(textarea);

        const initialHtml = textarea.value || '';
        const quill = new Quill(editorDiv, {
            theme: 'snow',
            modules: {
                toolbar: {
                    container: [
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ 'header': [1, 2, 3, false] }],
                        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                        ['link', 'blockquote', 'code-block', 'image'],
                        ['clean']
                    ]
                }
            }
        });

        if (initialHtml) {
            quill.clipboard.dangerouslyPasteHTML(initialHtml);
        }

        const form = textarea.form;
        if (form) {
            form.addEventListener('submit', function() {
                textarea.value = quill.root.innerHTML;
            }, { once: true });
        }

        textarea.__quillInstance = quill;
        textarea.dataset.quillInitialized = '1';
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // 페이지 로드 시 초기화
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Admin editor switch 초기화 시작');
        
        // 초기 상태 확인 (더 긴 대기 시간)
        setTimeout(function() {
            console.log('Editor.js 상태:', typeof EditorJS !== 'undefined' ? '로드됨' : '로드 안됨');
            console.log('Quill 상태:', typeof Quill !== 'undefined' ? '로드됨' : '로드 안됨');
            switchEditor();
        }, 1000); // 1초 대기

        // source 필드 변경 감지
        const sourceField = document.querySelector('select[name="source"]');
        if (sourceField) {
            console.log('Source 필드 찾음:', sourceField);
            sourceField.addEventListener('change', function() {
                console.log('Source 필드 변경:', this.value);
                setTimeout(switchEditor, 200);
            });
        } else {
            console.warn('Source 필드를 찾을 수 없습니다.');
        }
    });
})();
