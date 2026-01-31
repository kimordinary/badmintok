/**
 * Django Admin에서 Editor.js 블록 에디터 초기화
 * 완전한 UI를 위한 최적화된 초기화
 */

(function() {
    'use strict';

    // CSRF 토큰 가져오기
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

    // 플러그인 클래스 매핑
    const PLUGIN_MAPPINGS = {
        Header: ['Header'],
        List: ['List'],
        Table: ['Table'],
        Image: ['Image'],
        Quote: ['Quote'],
        Code: ['CodeTool'],
        Delimiter: ['Delimiter']
    };

    // 플러그인 찾기
    function findPlugin(pluginNames) {
        for (let name of pluginNames) {
            if (window[name] && typeof window[name] === 'function') {
                return window[name];
            }
        }
        return null;
    }

    // 모든 플러그인 로드 확인
    function loadPlugins() {
        const plugins = {};

        for (let [key, names] of Object.entries(PLUGIN_MAPPINGS)) {
            const plugin = findPlugin(names);
            if (plugin) {
                plugins[key] = plugin;
            }
        }

        return plugins;
    }

    // Editor.js 초기화
    function initEditorJS() {
        console.log('Editor.js 초기화 함수 실행');

        const contentField = document.querySelector('textarea[name="content"]');

        if (!contentField) {
            console.warn('content textarea를 찾을 수 없습니다.');
            return;
        }

        const containerId = `editorjs-content`;
        let container = document.getElementById(containerId);

        // 컨테이너가 없으면 생성
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.className = 'editorjs-container';
            container.style.border = '1px solid #e2e8f0';
            container.style.borderRadius = '4px';
            container.style.padding = '20px';
            container.style.minHeight = '400px';
            container.style.background = '#ffffff';
            contentField.style.display = 'none';
            contentField.parentElement.insertBefore(container, contentField);
        }

        // 이미 초기화된 경우 스킵
        if (window.editorInstance) {
            console.log('Editor.js 이미 초기화됨');
            return;
        }

        if (typeof EditorJS === 'undefined') {
            console.error('EditorJS를 찾을 수 없습니다.');
            return;
        }

        // 플러그인 로드 확인
        const plugins = loadPlugins();
        console.log('로드된 플러그인:', Object.keys(plugins));

        // 기존 값 파싱
        let initialData = null;
        if (contentField.value && contentField.value.trim()) {
            try {
                initialData = JSON.parse(contentField.value);
                if (!initialData.blocks || !Array.isArray(initialData.blocks)) {
                    throw new Error('Invalid Editor.js data format');
                }
            } catch (e) {
                console.log('JSON 파싱 실패, 텍스트로 변환');
                const text = contentField.value.replace(/<[^>]*>/g, '').trim();
                if (text) {
                    initialData = {
                        blocks: [{
                            type: 'paragraph',
                            data: {
                                text: text
                            }
                        }]
                    };
                }
            }
        }

        // tools 객체 생성
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

        if (plugins.Table) {
            tools.table = {
                class: plugins.Table,
                inlineToolbar: true,
                config: {
                    rows: 2,
                    cols: 3
                }
            };
        }

        if (plugins.Image) {
            tools.image = {
                class: plugins.Image,
                config: {
                    uploader: {
                        async uploadByFile(file) {
                            const formData = new FormData();
                            formData.append('image', file);

                            const csrfToken = getCookie('csrftoken');
                            const response = await fetch('/community/upload-image/', {
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
                            return {
                                success: 1,
                                file: {
                                    url: result.url
                                }
                            };
                        }
                    }
                }
            };
        }

        if (plugins.Quote) {
            tools.quote = {
                class: plugins.Quote,
                inlineToolbar: true,
                config: {
                    quotePlaceholder: '인용구를 입력하세요',
                    captionPlaceholder: '출처'
                }
            };
        }

        if (plugins.Code) {
            tools.code = {
                class: plugins.Code,
                config: {
                    placeholder: '코드를 입력하세요'
                }
            };
        }

        if (plugins.Delimiter) {
            tools.delimiter = plugins.Delimiter;
        }

        console.log('Editor.js tools 설정:', Object.keys(tools));

        // Editor.js 초기화
        try {
            const editorConfig = {
                holder: containerId,
                tools: tools,
                placeholder: '내용을 입력하세요... (Enter를 눌러 새 블록을 추가하세요)',
                autofocus: true,
                minHeight: 300
            };

            if (initialData) {
                editorConfig.data = initialData;
            }

            const editor = new EditorJS(editorConfig);

            editor.isReady.then(() => {
                console.log('✅ Editor.js 초기화 완료!');
            }).catch((error) => {
                console.error('Editor.js 준비 실패:', error);
            });

            window.editorInstance = editor;

            // 폼 제출 시 데이터 저장
            const form = contentField.closest('form');
            if (form) {
                form.addEventListener('submit', async function(e) {
                    try {
                        const outputData = await editor.save();
                        contentField.value = JSON.stringify(outputData);
                        console.log('Editor.js 데이터 저장 완료');
                    } catch (error) {
                        console.error('Editor.js 저장 실패:', error);
                        e.preventDefault();
                        alert('콘텐츠 저장 중 오류가 발생했습니다.');
                    }
                });
            }
        } catch (error) {
            console.error('Editor.js 초기화 실패:', error);
            alert('에디터 초기화에 실패했습니다. 콘솔을 확인해주세요.');
        }
    }

    // 페이지 로드 시 초기화
    function initialize() {
        console.log('🚀 Admin Editor.js 스크립트 로드됨');

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                setTimeout(function() {
                    console.log('DOM 로드 완료, Editor.js 확인 중...');
                    if (typeof EditorJS !== 'undefined') {
                        console.log('✅ EditorJS 로드됨');
                        initEditorJS();
                    } else {
                        console.error('❌ EditorJS가 로드되지 않았습니다.');
                    }
                }, 500);
            });
        } else {
            setTimeout(function() {
                console.log('이미 DOM 로드됨, Editor.js 확인 중...');
                if (typeof EditorJS !== 'undefined') {
                    console.log('✅ EditorJS 로드됨');
                    initEditorJS();
                } else {
                    console.error('❌ EditorJS가 로드되지 않았습니다.');
                }
            }, 500);
        }
    }

    // 즉시 실행
    initialize();
})();
