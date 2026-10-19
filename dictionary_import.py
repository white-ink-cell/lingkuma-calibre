"""Trusted Qt file handoff to the unchanged Zotero dictionary importer."""

from __future__ import annotations

import json
from pathlib import Path

from qt.core import QTimer, QUrl
from qt.webengine import QWebEnginePage

from calibre_plugins.lingkuma_calibre.server import ReaderServer


_ACTIVE_IMPORTS = set()


class DictionaryImport:
    def __init__(self, state, resource_root: Path, source_path: str, finished, lookup_data_root=None):
        self.server = ReaderServer(resource_root, None, state, lookup_data_root=lookup_data_root)
        self.source_path = source_path
        self.finished = finished
        self.staged = None
        self.page = None
        self.timer = None
        self.done = False

    def start(self):
        if _ACTIVE_IMPORTS:
            raise RuntimeError('A dictionary operation is already running')
        if self.source_path:
            self.staged = self.server.lookup_host.stage_user_dictionary(self.source_path)
        try:
            self.server.start()
            self.page = QWebEnginePage()
            self.page.loadFinished.connect(self._loaded)
            self.page.load(QUrl(self.server.base_url + '/lookup-import-worker'))
            _ACTIVE_IMPORTS.add(self)
        except Exception:
            if self.staged:
                self.server.lookup_host.remove_staged_dictionary(self.staged)
            self.server.stop()
            raise

    def _loaded(self, ok):
        if self.done:
            return
        if not ok:
            self._finish(None, RuntimeError('Dictionary import page failed to load'))
            return
        self.page.runJavaScript(self._script())
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

    def _script(self):
        return (
            "globalThis.__LK_IMPORT_RESULT__={status:'working'};"
            "globalThis.__LINGKUMA_CALIBRE_IMPORT_DICTIONARY__(" + json.dumps(self.staged) + ")"
            ".then(value=>globalThis.__LK_IMPORT_RESULT__={status:'done',value})"
            ".catch(error=>globalThis.__LK_IMPORT_RESULT__={status:'error',error:String(error)});"
        )

    def _poll(self):
        if not self.done:
            self.page.runJavaScript('JSON.stringify(globalThis.__LK_IMPORT_RESULT__||{})', self._received)

    def _received(self, raw):
        if self.done or not raw:
            return
        try:
            result = json.loads(raw)
        except (ValueError, TypeError):
            return
        if result.get('status') == 'done':
            self._finish(result.get('value'), None)
        elif result.get('status') == 'error':
            self._finish(None, RuntimeError(result.get('error') or 'Dictionary import failed'))

    def _finish(self, value, error):
        if self.done:
            return
        self.done = True
        if self.timer:
            self.timer.stop()
        try:
            if self.staged:
                self.server.lookup_host.remove_staged_dictionary(self.staged)
        finally:
            self.server.stop()
            if self.page:
                self.page.deleteLater()
            _ACTIVE_IMPORTS.discard(self)
            self.finished(value, error)


class DictionaryStatus(DictionaryImport):
    def __init__(self, state, resource_root: Path, finished, pair=None, lookup_data_root=None):
        super().__init__(state, resource_root, None, finished, lookup_data_root)
        self.pair = pair or {}

    def _script(self):
        return (
            "globalThis.__LK_IMPORT_RESULT__={status:'working'};"
            "globalThis.__LINGKUMA_CALIBRE_DICTIONARY_STATUS__(" + json.dumps(self.pair) + ")"
            ".then(value=>globalThis.__LK_IMPORT_RESULT__={status:'done',value})"
            ".catch(error=>globalThis.__LK_IMPORT_RESULT__={status:'error',error:String(error)});"
        )
