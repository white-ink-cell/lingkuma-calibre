"""Calibre filesystem and SQLite primitives for the reused Zotero lookup core.

The reader passes virtual paths under ``data/``. No book page can name an
arbitrary local file or issue arbitrary SQL through this boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path, PurePosixPath


_SQL = {
    'pragma quick_check',
    'pragma table_info(lookup_cache)',
    'pragma table_info(metadata)',
    'pragma table_info(entries)',
    "pragma index_info('entries_headword_norm')",
    'select key, value from metadata',
    "select count(*) from sqlite_master where type = 'table' and name in ('metadata', 'entries')",
    "select count(*) from sqlite_master where type = 'index' and name = 'entries_headword_norm' and tbl_name = 'entries'",
    'select meanings_json from entries where length(trim(headword)) > 0 and length(trim(meanings_json)) > 2 limit 1',
    'select headword, ipa, audio_json from entries where headword_norm = ? limit 8',
    'select headword, meanings_json, pos_json, ipa, audio_json, lemma, forms_json from entries where headword_norm = ? limit 8',
    'select result_json from lookup_cache where dictionary_identity = ? and source_language = ? and target_language = ? and normalized_term = ?',
    'insert or replace into lookup_cache (dictionary_identity, source_language, target_language, normalized_term, result_json) values (?, ?, ?, ?, ?)',
}


class LookupHost:
    _write_lock = threading.RLock()
    _default_condition = threading.Condition()
    _default_leases: dict[tuple[str, str], tuple[str, float]] = {}

    def __init__(self, resource_root: str | Path, data_root: str | Path):
        self.resource_root = Path(resource_root).resolve()
        self.data_root = Path(data_root).resolve()
        self._owned_leases: dict[str, tuple[str, str]] = {}

    def _default_key(self, request: dict) -> tuple[str, str]:
        dictionary_id = str(request.get('dictionaryID') or '')
        if dictionary_id != 'kaikki-en-zh-cn-2026-09-02':
            raise ValueError('Unknown default dictionary')
        return str(self.data_root), dictionary_id

    def release_all_leases(self) -> None:
        with self._default_condition:
            for token, key in list(self._owned_leases.items()):
                if self._default_leases.get(key, (None,))[0] == token:
                    self._default_leases.pop(key, None)
                self._owned_leases.pop(token, None)
            self._default_condition.notify_all()

    def stage_user_dictionary(self, source_path: str | Path) -> str:
        """Hand a Qt-selected file to the existing JS importer without exposing its path."""
        source = Path(source_path)
        if source.suffix.lower() != '.lkdict' or not source.is_file():
            raise ValueError('Select an existing .lkdict file')
        virtual = f'data/imports/{uuid.uuid4().hex}.lkdict'
        target = self._path(virtual)
        with self._write_lock:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(source, target)
            except Exception:
                target.unlink(missing_ok=True)
                raise
        return virtual

    def remove_staged_dictionary(self, virtual_path: str) -> None:
        path = self._path(virtual_path)
        if path.parent != self.data_root / 'imports' or path.suffix != '.lkdict':
            raise ValueError('Not a staged dictionary')
        with self._write_lock:
            path.unlink(missing_ok=True)

    def translate_quick(self, request: dict) -> dict:
        """Relay only Zotero's existing marked-sentence Edge request."""
        url = str(request.get('url') or '')
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme, parsed.netloc, parsed.path) != (
                'https', 'edge.microsoft.com', '/translate/translatetext'):
            raise ValueError('Quick Context provider URL is not permitted')
        body = str(request.get('body') or '')
        if not body or len(body) > 50000:
            raise ValueError('Invalid Quick Context request size')
        timeout = min(60, max(3, float(request.get('timeout') or 15)))
        outgoing = urllib.request.Request(url, data=body.encode('utf-8'), method='POST',
                                          headers={'Accept': 'application/json',
                                                   'Content-Type': 'application/json; charset=UTF-8'})

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_args, **_kwargs):
                return None

        with urllib.request.build_opener(NoRedirect).open(outgoing, timeout=timeout) as response:
            data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise ValueError('Quick Context response is too large')
        return json.loads(data.decode('utf-8'))

    def _path(self, raw: object) -> Path:
        value = str(raw or '')
        virtual = PurePosixPath(value)
        if (not value.startswith('data/') or '\\' in value or
                any(part in {'', '.', '..'} for part in virtual.parts) or
                len(value) > 300):
            raise ValueError('Invalid lookup data path')
        path = (self.data_root / Path(*virtual.parts[1:])).resolve()
        if not path.is_relative_to(self.data_root):
            raise ValueError('Lookup path escapes its data directory')
        return path

    def _bundle(self, raw: object) -> Path:
        value = str(raw or '')
        if value != 'assets/dictionaries/kaikki-en-zh-cn-2026-09.lkdict':
            raise ValueError('Unknown bundled dictionary')
        path = (self.resource_root / value).resolve()
        if not path.is_relative_to(self.resource_root):
            raise ValueError('Bundled path escapes resources')
        return path

    def run(self, request: dict) -> dict:
        op = str(request.get('op') or '')
        if op == 'acquireDefault':
            key = self._default_key(request)
            with self._default_condition:
                while True:
                    active = self._default_leases.get(key)
                    remaining = active[1] - time.monotonic() if active else 0
                    if remaining <= 0:
                        token = uuid.uuid4().hex
                        self._default_leases[key] = (token, time.monotonic() + 120)
                        self._owned_leases[token] = key
                        return {'value': token}
                    self._default_condition.wait(timeout=min(remaining, 5))
        if op == 'releaseDefault':
            token = str(request.get('lease') or '')
            with self._default_condition:
                key = self._owned_leases.pop(token, None)
                if key and self._default_leases.get(key, (None,))[0] == token:
                    self._default_leases.pop(key, None)
                    self._default_condition.notify_all()
            return {'value': True}
        if op == 'exists':
            return {'value': self._path(request.get('path')).is_file()}
        if op == 'stat':
            path = self._path(request.get('path'))
            info = path.stat()
            return {'value': {'type': 'regular' if path.is_file() else 'directory',
                              'size': info.st_size, 'lastModified': info.st_mtime_ns,
                              'creationTime': info.st_ctime_ns}}
        if op == 'mkdir':
            with self._write_lock:
                self._path(request.get('path')).mkdir(parents=True, exist_ok=True)
            return {'value': True}
        if op in {'copy', 'move', 'remove', 'copyBundled'}:
            with self._write_lock:
                target = self._path(request.get('target') if op != 'remove' else request.get('path'))
                if op == 'remove':
                    target.unlink(missing_ok=True)
                else:
                    source = self._bundle(request.get('source')) if op == 'copyBundled' else self._path(request.get('source'))
                    if not source.is_file():
                        raise ValueError('Dictionary source is missing')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if op == 'move':
                        os.replace(source, target)
                    else:
                        shutil.copyfile(source, target)
            return {'value': True}
        if op == 'sha256':
            digest = hashlib.sha256()
            with self._path(request.get('path')).open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            return {'value': digest.hexdigest()}
        if op in {'query', 'value'}:
            raw_sql = str(request.get('sql') or '')
            sql = ' '.join(raw_sql.strip().split())
            normalized = sql.lower()
            create_cache = normalized.startswith('create table if not exists lookup_cache (')
            if normalized not in _SQL and not create_cache:
                raise ValueError('Lookup SQL is not permitted')
            path = self._path(request.get('path'))
            is_cache = path.name == 'lookup-cache.sqlite' and path.parent == self.data_root
            writes_cache = create_cache or normalized.startswith('insert or replace into lookup_cache ')
            if writes_cache and not is_cache:
                raise ValueError('Dictionary files are read-only')
            if is_cache and normalized not in {
                    'pragma table_info(lookup_cache)',
                    'select result_json from lookup_cache where dictionary_identity = ? and source_language = ? and target_language = ? and normalized_term = ?',
                    'insert or replace into lookup_cache (dictionary_identity, source_language, target_language, normalized_term, result_json) values (?, ?, ?, ?, ?)'} and not create_cache:
                raise ValueError('Cache query is not permitted')
            if not is_cache and not (path.name.endswith('.lkdict') or path.name.endswith('.lkdict.part')):
                raise ValueError('Unknown lookup database')
            params = request.get('params') or []
            if not isinstance(params, list) or len(params) > 8 or any(
                    not isinstance(value, (str, int, float, type(None))) or
                    isinstance(value, str) and len(value) > 65536 for value in params):
                raise ValueError('Invalid lookup query parameters')
            if is_cache:
                path.parent.mkdir(parents=True, exist_ok=True)
                connection = sqlite3.connect(path, timeout=10)
            else:
                connection = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True, timeout=10)
            try:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(sql, params).fetchmany(32)
                if writes_cache:
                    connection.commit()
                return {'value': rows[0][0] if op == 'value' and rows else None} if op == 'value' else {
                    'value': [dict(row) for row in rows]}
            finally:
                connection.close()
        raise ValueError('Unknown lookup host operation')
