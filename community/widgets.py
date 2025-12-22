from django import forms
from django.utils.safestring import mark_safe


class QuillEditorWidget(forms.Textarea):
    """Admin용 Quill 에디터 위젯.

    - 기본 textarea를 숨기고 같은 위치에 Quill 에디터를 렌더링합니다.
    - 값은 textarea에 HTML 형태로 저장됩니다.
    """

    class Media:
        css = {
            "all": (
                "https://cdn.quilljs.com/1.3.6/quill.snow.css",
            )
        }
        js = (
            "https://cdn.quilljs.com/1.3.6/quill.js",
            "js/admin-quill.js",
        )

    def __init__(self, attrs=None):
        default_attrs = {"class": "vLargeTextField js-quill-editor"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # 기본 textarea 렌더링 (숨겨두고 JS가 Quill 에디터로 교체)
        textarea_html = super().render(name, value, attrs, renderer)
        # JS에서 .js-quill-editor 클래스를 가진 textarea를 찾아 처리하므로 여기선 그대로 반환
        return mark_safe(textarea_html)


class EditorJSWidget(forms.Textarea):
    """Admin용 Editor.js 블록 에디터 위젯.
    
    - Editor.js를 사용하여 블록 기반 에디터를 제공합니다.
    - 데이터는 JSON 형태로 저장됩니다.
    - 배드민톡 글(source='badmintok')에만 사용됩니다.
    """

    class Media:
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/@editorjs/editorjs@latest/dist/editor.css",
            )
        }
        js = (
            "https://cdn.jsdelivr.net/npm/@editorjs/editorjs@latest",
            "https://cdn.jsdelivr.net/npm/@editorjs/paragraph@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/header@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/list@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/image@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/quote@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/code@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/delimiter@latest/dist/bundle.js",
            "js/admin-editorjs.js",
        )

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "vLargeTextField js-editorjs-editor",
            "style": "display: none;",  # textarea는 숨김
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # textarea는 숨겨두고, JS가 Editor.js 인스턴스를 생성
        textarea_html = super().render(name, value, attrs, renderer)
        # Editor.js 컨테이너 추가
        editor_container = f'<div id="editorjs-{name}" class="editorjs-container"></div>'
        return mark_safe(textarea_html + editor_container)
