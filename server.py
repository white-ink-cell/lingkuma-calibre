# -*- coding: utf-8 -*-
"""Loopback web server used by the in-calibre LingKuma reader."""

from __future__ import annotations

import json
import mimetypes
import queue
import re
import secrets
import threading
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from calibre_plugins.lingkuma_calibre.compat import safe_join
from calibre_plugins.lingkuma_calibre.version import VERSION_STR

UPSTREAM_SCRIPTS = (
    'src/utils/highlight_floating_button.js',
    'src/service/a1_loadKnowWords.js',
    'src/service/jp/kuromoji.js',
    'src/service/a2_hightlight.js',
    'src/utils/lingqBlocker.js',
    'src/utils/cloudAPI.js',
    'src/utils/dataAccessLayer.js',
    'src/utils/evaluateExpression.js',
    'src/utils/pdfDetection.js',
    'src/utils/sentenseOoOo.js',
    'src/utils/liquid-glass.js',
    'src/plugin/min/compromise.js',
    'src/plugin/min/de-compromise.min.js',
    'src/utils/language-detector/eld.extrasmall.global.js',
    'src/service/a3_aiFragen.js',
    'src/service/a4_tooltip_new.js',
    'src/service/a5_custom_word_selection.js',
    'src/service/a6_custom_highlight.js',
    'src/service/a7_words_boom.js',
    'src/service/a7.1_sentence_navigator.js',
    'src/plugin/tts.js',
    'src/plugin/edge_tts.js',
    'src/plugin/orion_tts.js',
    'src/content.js',
)


def _json_for_script(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def _decode_html(data: bytes) -> str:
    head = data[:2048].decode('ascii', errors='ignore')
    match = re.search(r'charset\s*=\s*["\']?([\w.-]+)', head, re.I)
    candidates = [match.group(1)] if match else []
    candidates += ['utf-8-sig', 'utf-8', 'utf-16', 'gb18030', 'windows-1252']
    for encoding in candidates:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode('utf-8', errors='replace')


def _repair_text_chunks(document: str, remove_soft_hyphen: bool, repair_hyphen: bool) -> str:
    if not remove_soft_hyphen and not repair_hyphen:
        return document
    chunks = re.split(r'(<[^>]+>)', document)
    for index in range(0, len(chunks), 2):
        text = chunks[index]
        if remove_soft_hyphen:
            text = text.replace('\u00ad', '')
        if repair_hyphen:
            # Repair OCR/EPUB line-break hyphenation while leaving normal compounds alone.
            text = re.sub(r'(?<=\w)-[ \t]*\r?\n[ \t]*(?=[a-z])', '', text)
        chunks[index] = text
    return ''.join(chunks)


def _sanitize_book_html(document: str) -> str:
    # Remove CSP, embedded script execution, event handlers and javascript: URLs.
    document = re.sub(r'<meta\b[^>]*http-equiv\s*=\s*["\']?content-security-policy["\']?[^>]*>', '', document, flags=re.I)
    document = re.sub(r'<script\b[^>]*>.*?</script\s*>', '', document, flags=re.I | re.S)
    document = re.sub(r'\s+on[a-z]+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', '', document, flags=re.I)
    document = re.sub(r'(?i)(href|src)\s*=\s*(["\'])\s*javascript:[^"\']*\2', r'\1="#"', document)
    return document


class ReaderServer:
    def __init__(self, resource_root: str | Path, package, state, plugin_version: str = VERSION_STR, viewer_preferences: dict | None = None):
        self.resource_root = Path(resource_root).resolve()
        self.package = package
        self.state = state
        self.plugin_version = plugin_version
        self.viewer_preferences = dict(viewer_preferences or {})
        self.token = secrets.token_urlsafe(24)
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.ui_queue: queue.Queue[str] = queue.Queue()
        self.last_error = ''
        self._lifecycle_lock = threading.RLock()
        self._inline_scripts = self._build_inline_scripts()

    def _build_inline_scripts(self) -> list[tuple[str, str]]:
        scripts: list[tuple[str, str]] = []
        paths = ['adapter/platform.js', 'adapter/shadow_capture.js'] + [f'upstream/{path}' for path in UPSTREAM_SCRIPTS] + ['compat/language_bridge.js', 'compat/theme_event_bridge.js', 'compat/glass_fallback.js', 'compat/sentence_patch.js', 'host/page_appearance.js', 'host/navigation_progress.js', 'adapter/lingkuma_boot.js']
        for rel in paths:
            target = safe_join(self.resource_root, rel)
            source = target.read_text(encoding='utf-8').replace('</script', '<\\/script')
            scripts.append((rel, source))
        return scripts

    @property
    def base_url(self) -> str:
        if not self.httpd:
            return ''
        return f'http://127.0.0.1:{self.httpd.server_address[1]}/{self.token}'

    def start(self) -> str:
        with self._lifecycle_lock:
            if self.httpd:
                return self.base_url
        parent = self

        class Handler(BaseHTTPRequestHandler):
            server_version = f'LingKumaCalibre/{VERSION_STR}'
            protocol_version = 'HTTP/1.1'

            def _safe_write(self, data):
                try:
                    self.wfile.write(data)
                    return True
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
                    return False

            def log_message(self, _format, *_args):
                return

            def _headers(self, status=200, content_type='application/json; charset=utf-8', length=None):
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Cache-Control', 'no-store, max-age=0')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Connection', 'close')
                if length is not None:
                    self.send_header('Content-Length', str(length))
                self.end_headers()

            def _json(self, value, status=200):
                data = json.dumps(value, ensure_ascii=False).encode('utf-8')
                self._headers(status, 'application/json; charset=utf-8', len(data))
                self._safe_write(data)

            def _body_json(self):
                length = min(int(self.headers.get('Content-Length', '0') or 0), 16 * 1024 * 1024)
                raw = self.rfile.read(length) if length else b'{}'
                return json.loads(raw.decode('utf-8') or '{}')

            def _authorized_path(self):
                path = unquote(urlsplit(self.path).path)
                prefix = '/' + parent.token
                if path != prefix and not path.startswith(prefix + '/'):
                    return None
                return path[len(prefix):].lstrip('/')

            def do_GET(self):
                rel = self._authorized_path()
                if rel is None:
                    return self._json({'error': 'not found'}, HTTPStatus.NOT_FOUND)
                try:
                    if not rel:
                        self.send_response(HTTPStatus.FOUND)
                        self.send_header('Location', parent.chapter_url(0))
                        self.end_headers()
                        return
                    if rel.startswith('book/'):
                        return self._serve_book(rel[5:])
                    if rel.startswith('res/'):
                        return self._serve_resource(rel[4:])
                    if rel == 'api/bootstrap':
                        return self._json(parent.bootstrap(0))
                    return self._json({'error': 'not found'}, HTTPStatus.NOT_FOUND)
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
                    return
                except Exception as error:
                    parent.last_error = traceback.format_exc()
                    return self._json({'error': str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

            def do_POST(self):
                rel = self._authorized_path()
                if rel is None or not rel.startswith('api/'):
                    return self._json({'error': 'not found'}, HTTPStatus.NOT_FOUND)
                try:
                    payload = self._body_json()
                    action = rel[4:]
                    if action == 'storage/get':
                        result = parent.state.storage_get(payload.get('keys'))
                    elif action == 'storage/set':
                        result = {'success': True, 'changes': parent.state.storage_set(payload)}
                    elif action == 'storage/remove':
                        result = {'success': True, 'changes': parent.state.storage_remove(payload.get('keys') or [])}
                    elif action == 'storage/clear':
                        result = {'success': True, 'changes': parent.state.storage_clear()}
                    elif action == 'message':
                        result = parent.state.handle_message(payload)
                    elif action == 'progress':
                        parent.state.set_progress(parent.package.book_key, payload.get('chapter', 0), payload.get('scrollRatio', 0))
                        result = {'success': True}
                    elif action == 'ui':
                        parent.ui_queue.put(dict(payload))
                        result = {'success': True}
                    elif action == 'log':
                        level = str(payload.get('level') or 'log')
                        message = str(payload.get('message') or '')
                        source = str(payload.get('source') or payload.get('url') or '')
                        line = payload.get('line')
                        print(f'[LingKuma calibre {parent.plugin_version} JS {level}] {message}' + (f' ({source}:{line})' if source else ''))
                        result = {'success': True}
                    else:
                        return self._json({'error': 'unknown API action'}, HTTPStatus.NOT_FOUND)
                    return self._json(result)
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
                    return
                except Exception as error:
                    parent.last_error = traceback.format_exc()
                    return self._json({'error': str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

            def _serve_resource(self, rel):
                target = safe_join(parent.resource_root, rel)
                if not target.is_file():
                    return self._json({'error': 'resource not found'}, HTTPStatus.NOT_FOUND)
                data = target.read_bytes()
                mime = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
                if target.suffix.lower() == '.js':
                    mime = 'application/javascript; charset=utf-8'
                elif target.suffix.lower() == '.css':
                    mime = 'text/css; charset=utf-8'
                self._headers(200, mime, len(data))
                self._safe_write(data)

            def _serve_book(self, rel):
                target = safe_join(parent.package.root, rel)
                if not target.is_file():
                    return self._json({'error': 'book resource not found'}, HTTPStatus.NOT_FOUND)
                suffix = target.suffix.lower()
                if suffix in {'.html', '.htm', '.xhtml', '.xhtm'}:
                    query = parse_qs(urlsplit(self.path).query)
                    is_main_reader_page = query.get('lkmain', ['0'])[-1] == '1'
                    if is_main_reader_page:
                        chapter_index = parent.chapter_index(rel)
                        data = parent.inject_html(target.read_bytes(), chapter_index)
                    else:
                        # EPUBs often prefetch linked XHTML files. Do not inject the
                        # entire LingKuma runtime into those hidden/background loads.
                        # Still remove executable book scripts before serving them.
                        document = _decode_html(target.read_bytes())
                        document = _sanitize_book_html(document)
                        document = _repair_text_chunks(
                            document,
                            bool(parent.state.storage.get('epubSoftHyphenCleanup', True)),
                            bool(parent.state.storage.get('epubHyphenRepair', True)),
                        )
                        data = document.encode('utf-8')
                    # Serve transformed EPUB XHTML as HTML. This avoids XML parser
                    # failures from third-party book markup while preserving layout.
                    mime = 'text/html; charset=utf-8'
                else:
                    data = target.read_bytes()
                    mime = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
                self._headers(200, mime, len(data))
                self._safe_write(data)

        class LoopbackServer(ThreadingHTTPServer):
            allow_reuse_address = True
            daemon_threads = True
            block_on_close = False

        httpd = LoopbackServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(
            target=lambda: httpd.serve_forever(poll_interval=0.1),
            name=f'LingKumaCalibreHTTP-{httpd.server_address[1]}',
            daemon=True,
        )
        with self._lifecycle_lock:
            # A concurrent stop can only happen during application shutdown.
            # Publish both objects atomically before starting the thread.
            self.httpd = httpd
            self.thread = thread
        thread.start()
        print(f'[LingKuma calibre {self.plugin_version}] HTTP started on 127.0.0.1:{httpd.server_address[1]}')
        return self.base_url

    def stop(self) -> None:
        """Stop the loopback server and wait briefly for its daemon thread."""
        with self._lifecycle_lock:
            httpd, thread = self.httpd, self.thread
            self.httpd = None
            self.thread = None
        if httpd is None:
            return
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            httpd.server_close()
        except Exception:
            pass
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=3.0)
        if thread is not None and thread.is_alive():
            print(f'[LingKuma calibre {self.plugin_version}] WARNING: HTTP thread did not stop: {thread.name}')
        else:
            print(f'[LingKuma calibre {self.plugin_version}] HTTP stopped')

    def chapter_index(self, rel_path: str) -> int:
        normalized = rel_path.replace('\\', '/').lstrip('/')
        for index, chapter in enumerate(self.package.chapters):
            if chapter.path == normalized:
                return index
        return 0

    def chapter_url(self, index: int) -> str:
        index = max(0, min(int(index), len(self.package.chapters) - 1))
        # Quote only URL-hostile characters but preserve path separators.
        from urllib.parse import quote
        return f'{self.base_url}/book/{quote(self.package.chapters[index].path, safe="/")}?lkmain=1'

    def bootstrap(self, chapter_index: int) -> dict:
        # Pass the persisted LingKuma settings through unchanged. Host bootstrap
        # must describe the environment, not silently rewrite application policy.
        storage = self.state.storage_get(None)
        return {
            'baseURL': self.base_url,
            'pluginVersion': self.plugin_version,
            'tabID': 1,
            'bookKey': self.package.book_key,
            'bookTitle': self.package.title,
            'chapterIndex': int(chapter_index),
            'chapterCount': len(self.package.chapters),
            'progress': self.state.get_progress(self.package.book_key),
            'storage': storage,
            'calibreViewer': self.viewer_preferences,
        }

    def inject_html(self, data: bytes, chapter_index: int) -> bytes:
        document = _decode_html(data)
        document = _sanitize_book_html(document)
        document = _repair_text_chunks(
            document,
            bool(self.state.storage.get('epubSoftHyphenCleanup', True)),
            bool(self.state.storage.get('epubHyphenRepair', True)),
        )
        # XML declarations before the doctype are fine, but ensure a complete HTML document.
        if not re.search(r'<html\b', document, re.I):
            document = f'<!doctype html><html><head><meta charset="utf-8"></head><body>{document}</body></html>'
        if not re.search(r'<head\b', document, re.I):
            document = re.sub(r'(<html\b[^>]*>)', r'\1<head><meta charset="utf-8"></head>', document, count=1, flags=re.I)
        if not re.search(r'<body\b', document, re.I):
            document = re.sub(r'(</head\s*>)', r'\1<body>', document, count=1, flags=re.I)
            document = re.sub(r'(</html\s*>)', r'</body>\1', document, count=1, flags=re.I)

        bootstrap = _json_for_script(self.bootstrap(chapter_index))
        viewer_css = ''
        if str(self.state.storage.get('readerLayoutMode') or 'calibre') == 'calibre':
            raw_css = str(self.viewer_preferences.get('userStylesheet') or '')
            if raw_css:
                viewer_css = '<style data-lk-calibre-user-style>' + raw_css.replace('</style', '<\\/style') + '</style>'
        head = (
            f'<link rel="stylesheet" href="{self.base_url}/res/host/reader_inject.css"/>'
            f'<link rel="stylesheet" href="{self.base_url}/res/upstream/content.css"/>'
            + viewer_css
        )
        scripts = [f'<script>globalThis.__LINGKUMA_CALIBRE_BOOTSTRAP__={bootstrap};</script>']
        # Inline all critical JavaScript.  QWebEngine on some Windows systems
        # aborts bursts of loopback resource requests (WinError 10053), leaving
        # a visible but non-interactive tooltip.  Inline scripts keep the exact
        # upstream order while requiring only the chapter request itself.
        for rel, source in self._inline_scripts:
            scripts.append(f'<script data-lingkuma-source="{rel}">{source}\n//# sourceURL=lingkuma-calibre://{rel}</script>')
        script_block = ''.join(scripts)
        document = re.sub(r'(</head\s*>)', lambda match: head + match.group(1), document, count=1, flags=re.I)
        if re.search(r'</body\s*>', document, re.I):
            document = re.sub(r'(</body\s*>)', lambda match: script_block + match.group(1), document, count=1, flags=re.I)
        else:
            document += script_block
        return document.encode('utf-8')
