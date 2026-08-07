# -*- coding: utf-8 -*-
"""Qt WebEngine based LingKuma reader hosted inside calibre."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from calibre.gui2 import safe_open_url
from qt.core import (
    QAction,
    QComboBox,
    QHBoxLayout,
    QIcon,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTimer,
    QToolBar,
    QUrl,
    QWidget,
)
from qt.webengine import QWebEnginePage, QWebEngineProfile, QWebEngineView

from calibre_plugins.lingkuma_calibre.compat import calibre_viewer_preferences
from calibre_plugins.lingkuma_calibre.config import ReaderAppearanceDialog, SettingsDialog
from calibre_plugins.lingkuma_calibre.server import ReaderServer
from calibre_plugins.lingkuma_calibre.version import USER_AGENT, VERSION_STR


class LingKumaWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802 - Qt API
        print(f'[LingKuma calibre {VERSION_STR} JS console {level}] {message} ({source_id}:{line_number})')

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):  # noqa: N802 - Qt API
        host = (url.host() or '').lower()
        if url.scheme() in {'http', 'https'} and host not in {'127.0.0.1', 'localhost'}:
            safe_open_url(url)
            return False
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)


class LingKumaReader(QMainWindow):
    def __init__(self, package, state, resource_root, icon=None, parent=None):
        super().__init__(parent)
        self.package = package
        self.state = state
        self.resource_root = Path(resource_root)
        self.current_chapter = 0
        self._shutdown_done = False
        self.calibre_viewer_prefs = calibre_viewer_preferences()
        self.server = ReaderServer(
            self.resource_root, package, state, plugin_version=VERSION_STR,
            viewer_preferences=self.calibre_viewer_prefs,
        )
        # Do not start the server until every Qt widget has been constructed.
        # Older builds started it before toolbar creation, so any Qt API error
        # leaked one HTTP thread for each failed open attempt.
        self.setWindowTitle(f'{package.title} — LingKuma Reader')
        if isinstance(icon, QIcon):
            self.setWindowIcon(icon)
        self.resize(1220, 900)
        self.setMinimumSize(760, 560)

        self.profile = QWebEngineProfile(self)
        self.profile.setHttpUserAgent(self.profile.httpUserAgent() + ' ' + USER_AGENT)
        self.view = QWebEngineView(self)
        self.page = LingKumaWebPage(self.profile, self.view)
        self.view.setPage(self.page)
        # Use calibre's own font-family/base-size bridge when available.  The
        # HTML adapter below mirrors margins and maximum text width; this call
        # keeps QWebEngine's serif/sans/monospace choices identical to the
        # native calibre viewer.
        try:
            from calibre.gui2.viewer.web_view import apply_font_settings
            apply_font_settings(self.page)
        except Exception as error:
            print(f'[LingKuma calibre {VERSION_STR}] calibre font settings unavailable: {error}')
        self.setCentralWidget(self.view)
        self._build_toolbar()
        self.setStatusBar(QStatusBar(self))
        self.view.loadStarted.connect(lambda: self.statusBar().showMessage('正在载入章节……'))
        self.view.loadProgress.connect(lambda value: self.statusBar().showMessage(f'正在载入章节…… {value}%'))
        self.view.loadFinished.connect(self._load_finished)
        self.view.titleChanged.connect(self._title_changed)

        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(150)
        self.ui_timer.timeout.connect(self._poll_server_actions)
        self.ui_timer.start()

        try:
            self.server.start()
            progress = self.state.get_progress(self.package.book_key)
            self.current_chapter = max(0, min(int(progress.get('chapter', 0)), len(package.chapters) - 1)) if self.state.storage.get('readerRememberPosition', True) else 0
            self.chapter_combo.setCurrentIndex(self.current_chapter)
            self.load_chapter(self.current_chapter)
        except Exception:
            self.server.stop()
            raise

    def _build_toolbar(self):
        toolbar = QToolBar(self)
        toolbar.setWindowTitle('LingKuma Reader')
        toolbar.setObjectName('LingKumaReaderToolbar')
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        previous = QAction('◀ 上一章', self)
        previous.setShortcut('Alt+Left')
        previous.triggered.connect(lambda: self.load_chapter(self.current_chapter - 1))
        toolbar.addAction(previous)

        next_action = QAction('下一章 ▶', self)
        next_action.setShortcut('Alt+Right')
        next_action.triggered.connect(lambda: self.load_chapter(self.current_chapter + 1))
        toolbar.addAction(next_action)

        self.chapter_combo = QComboBox(self)
        self.chapter_combo.setMinimumWidth(260)
        for index, chapter in enumerate(self.package.chapters):
            self.chapter_combo.addItem(f'{index + 1}. {chapter.title}', index)
        self.chapter_combo.activated.connect(lambda index: self.load_chapter(index))
        toolbar.addWidget(self.chapter_combo)
        toolbar.addSeparator()

        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText('在本章中查找')
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMaximumWidth(230)
        self.search_box.returnPressed.connect(self.find_next)
        toolbar.addWidget(self.search_box)
        find_button = QPushButton('查找', self)
        find_button.clicked.connect(self.find_next)
        toolbar.addWidget(find_button)
        toolbar.addSeparator()

        zoom_out = QAction('A−', self); zoom_out.triggered.connect(lambda: self.view.setZoomFactor(max(.5, self.view.zoomFactor() - .1)))
        zoom_in = QAction('A+', self); zoom_in.triggered.connect(lambda: self.view.setZoomFactor(min(3.0, self.view.zoomFactor() + .1)))
        reset = QAction('100%', self); reset.triggered.connect(lambda: self.view.setZoomFactor(1.0))
        toolbar.addAction(zoom_out); toolbar.addAction(zoom_in); toolbar.addAction(reset)
        toolbar.addSeparator()

        refresh = QAction('重新载入', self); refresh.setShortcut('Ctrl+R'); refresh.triggered.connect(self.view.reload)
        page_settings = QAction('书页设置', self); page_settings.setShortcut('Ctrl+Shift+P'); page_settings.triggered.connect(self.open_page_settings)
        settings = QAction('LingKuma 设置', self); settings.triggered.connect(self.open_settings)
        vocabulary = QAction('词库', self); vocabulary.triggered.connect(lambda: self.open_settings(6))
        toolbar.addAction(refresh); toolbar.addAction(page_settings); toolbar.addAction(settings); toolbar.addAction(vocabulary)

    def load_chapter(self, index):
        if not self.package.chapters:
            return
        index = max(0, min(int(index), len(self.package.chapters) - 1))
        self.current_chapter = index
        if self.chapter_combo.currentIndex() != index:
            self.chapter_combo.blockSignals(True); self.chapter_combo.setCurrentIndex(index); self.chapter_combo.blockSignals(False)
        self.view.setUrl(QUrl(self.server.chapter_url(index)))

    def find_next(self):
        text = self.search_box.text().strip()
        if not text:
            return
        self.view.findText(text)

    def _load_finished(self, ok):
        if ok:
            self.statusBar().showMessage(f'第 {self.current_chapter + 1} / {len(self.package.chapters)} 章', 4000)
            # LingKuma starts asynchronously after DOM load and storage callbacks.
            # Test after that initialization window rather than immediately when
            # QWebEngine reports loadFinished.
            # Bind the delayed diagnostic to the page that actually finished loading.
            # If the user navigates/reloads before the timer fires, skip the stale
            # self-test instead of executing against a transient document with no
            # documentElement yet.
            expected_url = self.view.url().toString()
            QTimer.singleShot(1200, lambda url=expected_url: self._run_page_self_test(url))
        else:
            details = self.server.last_error or self.view.url().toString()
            QMessageBox.warning(self, '章节载入失败', '无法载入当前章节。\n\n' + details)

    def _run_page_self_test(self, expected_url=None):
        # This is diagnostics only.  A delayed timer from the previous chapter can
        # otherwise fire while QWebEngine is replacing the document during fast
        # navigation/reload.  Never let diagnostics create a console error.
        if expected_url and self.view.url().toString() != expected_url:
            return
        script = r"""
        (() => JSON.stringify({
          chrome: !!globalThis.chrome?.storage?.local,
          tooltip: typeof globalThis.getSentenceForWord === 'function',
          highlightEntry: typeof globalThis.highlightAllWords === 'function',
          highlightManager: typeof highlightManager !== 'undefined' && !!highlightManager,
          floatingButton: !!document.getElementById('lingkuma-word-highlight-floating-root'),
          platform: !!globalThis.__LINGKUMA_CALIBRE_READER__,
          layout: document.documentElement?.dataset?.lkReaderLayout || '',
          bodyWidth: Math.round(document.body?.getBoundingClientRect().width || 0),
          viewportWidth: innerWidth
        }))()
        """
        try:
            self.page.runJavaScript(
                script,
                lambda result: print(f'[LingKuma calibre {VERSION_STR}] page self-test: {result}')
            )
        except Exception as error:
            print(f'[LingKuma calibre {VERSION_STR}] page self-test failed: {error}')

    def _title_changed(self, _title):
        self.setWindowTitle(f'{self.package.title} — LingKuma Reader')

    def open_settings(self, page=0):
        dialog = SettingsDialog(self, on_saved=self.apply_settings, initial_page=int(page))
        dialog.exec()

    def open_page_settings(self):
        dialog = ReaderAppearanceDialog(
            self, on_applied=self.apply_page_appearance, state=self.state
        )
        dialog.exec()

    def apply_page_appearance(self, values=None):
        """Apply page-only settings immediately without depending on a reload."""
        self.calibre_viewer_prefs = calibre_viewer_preferences()
        self.server.viewer_preferences = dict(self.calibre_viewer_prefs)
        storage = self.state.storage_get(None)
        payload = json.dumps(storage, ensure_ascii=False).replace('</', '<\\/')
        viewer = json.dumps(self.calibre_viewer_prefs, ensure_ascii=False).replace('</', '<\\/')
        script = (
            "(() => {"
            "const fn = globalThis.__LK_APPLY_READER_APPEARANCE__;"
            "if (typeof fn !== 'function') return JSON.stringify({ok:false,reason:'missing'});"
            f"return JSON.stringify(fn({payload}, {viewer}) || {{ok:true}});"
            "})()"
        )

        def finished(result):
            print(f'[LingKuma calibre {VERSION_STR}] page appearance applied: {result}')
            if not result or '"ok":false' in str(result):
                self.view.reload()

        try:
            from calibre.gui2.viewer.web_view import apply_font_settings
            apply_font_settings(self.page)
        except Exception:
            pass
        try:
            self.page.runJavaScript(script, finished)
        except Exception as error:
            print(f'[LingKuma calibre {VERSION_STR}] direct page appearance failed: {error}')
            self.view.reload()

    def apply_settings(self):
        # Refresh calibre's own viewer preferences as well as LingKuma state.
        self.calibre_viewer_prefs = calibre_viewer_preferences()
        self.server.viewer_preferences = dict(self.calibre_viewer_prefs)
        try:
            from calibre.gui2.viewer.web_view import apply_font_settings
            apply_font_settings(self.page)
        except Exception:
            pass
        self.view.reload()

    def _poll_server_actions(self):
        while True:
            try:
                action = self.server.ui_queue.get_nowait()
            except Exception:
                break
            payload = action if isinstance(action, dict) else {'action': str(action)}
            command = str(payload.get('action') or '')
            if command == 'settings':
                self.open_settings(0)
            elif command == 'page-settings':
                self.open_page_settings()
            elif command in {'vocabulary', 'sidebar'}:
                self.open_settings(6)
            elif command == 'open-url':
                url = QUrl(str(payload.get('url') or ''))
                if url.isValid() and url.scheme() in {'http', 'https'}:
                    safe_open_url(url)

    def shutdown(self):
        """Idempotently stop WebEngine activity and the loopback server."""
        if self._shutdown_done:
            return
        self._shutdown_done = True
        print(f'[LingKuma calibre {VERSION_STR}] closing reader: {self.package.title!r}')
        try:
            self.ui_timer.stop()
        except Exception:
            pass
        try:
            self.view.stop()
        except Exception:
            pass
        try:
            self.server.stop()
        finally:
            if getattr(self.package, 'temp_owned', False):
                shutil.rmtree(self.package.root, ignore_errors=True)

    def closeEvent(self, event):  # noqa: N802 - Qt API
        try:
            self.shutdown()
        finally:
            super().closeEvent(event)
