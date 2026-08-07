# -*- coding: utf-8 -*-
"""Calibre InterfaceAction entry points."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path

from calibre.gui2 import error_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.utils.config import config_dir
from qt.core import QFileDialog, QMenu

from calibre_plugins.lingkuma_calibre.compat import app_executable, safe_join
from calibre_plugins.lingkuma_calibre.config import SettingsDialog, get_state
from calibre_plugins.lingkuma_calibre.epub import prepare_book
from calibre_plugins.lingkuma_calibre.reader import LingKumaReader
from calibre_plugins.lingkuma_calibre.resource_manifest import RESOURCE_FILES
from calibre_plugins.lingkuma_calibre.version import PRODUCT, VERSION_STR

DIRECT_FORMATS = ('EPUB', 'HTMLZ', 'TXT', 'HTML', 'XHTML', 'HTM')
CONVERSION_PRIORITY = ('AZW3', 'MOBI', 'KFX', 'FB2', 'DOCX', 'ODT', 'RTF', 'PDF')


class LingKumaAction(InterfaceAction):
    name = 'LingKuma for calibre'
    action_spec = ('LingKuma 阅读', None, '使用 LingKuma 阅读所选图书', None)
    action_add_menu = True

    def genesis(self):
        self.icon = get_icons('images/icon.png', 'LingKuma for calibre')  # noqa: F821 - calibre plugin builtin
        self.qaction.setIcon(self.icon)
        self.qaction.triggered.connect(self.open_selected_book)
        self.readers = []
        self.resource_root = self._extract_resources()
        print(f'[LingKuma calibre {VERSION_STR}] initialized; resources={self.resource_root}')

        menu = QMenu(self.gui)
        self.qaction.setMenu(menu)
        action_open = menu.addAction(self.icon, '使用 LingKuma 阅读所选图书')
        action_open.triggered.connect(self.open_selected_book)
        action_file = menu.addAction('打开本地电子书……')
        action_file.triggered.connect(self.open_local_file)
        menu.addSeparator()
        action_settings = menu.addAction('完整设置')
        action_settings.triggered.connect(self.show_settings)
        action_vocabulary = menu.addAction('单词列表')
        action_vocabulary.triggered.connect(lambda: self.show_settings(6))
        menu.addSeparator()
        action_import = menu.addAction('导入 LingKuma 数据……')
        action_import.triggered.connect(self.import_data)
        action_export = menu.addAction('导出完整备份……')
        action_export.triggered.connect(self.export_data)
        menu.addSeparator()
        action_diagnostics = menu.addAction('运行安装自检')
        action_diagnostics.triggered.connect(self.show_diagnostics)

    def _extract_resources(self):
        runtime_base = Path(config_dir) / 'plugins' / 'lingkuma-calibre'
        destination = runtime_base / f'runtime-{VERSION_STR}'
        marker = destination / '.complete'
        # A versioned runtime prevents calibre from reusing JavaScript extracted
        # by an older plugin build. Old runtimes are removed only at startup,
        # before any LingKuma reader can be opened.
        runtime_base.mkdir(parents=True, exist_ok=True)
        for old_runtime in runtime_base.glob('runtime-*'):
            if old_runtime != destination:
                shutil.rmtree(old_runtime, ignore_errors=True)
        if marker.exists():
            return destination / 'resources'
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        destination.mkdir(parents=True, exist_ok=True)
        loaded = get_resources(RESOURCE_FILES)  # noqa: F821 - calibre plugin builtin
        missing = [name for name in RESOURCE_FILES if name not in loaded]
        if missing:
            raise RuntimeError('插件安装包缺少资源：' + ', '.join(missing[:8]))
        for name, data in loaded.items():
            target = safe_join(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        marker.write_text(f'LingKuma calibre runtime {VERSION_STR}', encoding='utf-8')
        return destination / 'resources'

    def _selected_ids(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        return [self.gui.library_view.model().id(row) for row in rows]

    def open_selected_book(self):
        ids = self._selected_ids()
        if not ids:
            error_dialog(self.gui, '没有选择图书', '请先在 Calibre 书库中选择一本图书。', show=True)
            return
        if len(ids) > 1:
            info_dialog(self.gui, '只打开第一本', 'LingKuma Reader 每次打开一本图书，本次将打开所选列表中的第一本。', show=True)
        book_id = ids[0]
        try:
            path, title, temp_root = self._book_path_from_library(book_id)
            self._open_prepared(path, book_id=book_id, title=title, temp_root=temp_root)
        except Exception as error:
            error_dialog(
                self.gui, '无法打开图书', str(error),
                det_msg=traceback.format_exc(), show=True,
            )

    def _book_path_from_library(self, book_id):
        db = self.gui.current_db.new_api
        formats = tuple(str(x).upper() for x in (db.formats(book_id) or ()))
        if not formats:
            raise ValueError('所选书目没有电子书文件。')
        metadata = db.get_metadata(book_id)
        title = getattr(metadata, 'title', None) or f'Book {book_id}'
        direct = next((fmt for fmt in DIRECT_FORMATS if fmt in formats), None)
        source_format = direct or next((fmt for fmt in CONVERSION_PRIORITY if fmt in formats), None) or formats[0]
        temp_root = Path(tempfile.mkdtemp(prefix='lingkuma-calibre-source-'))
        try:
            source = temp_root / ('source.' + source_format.lower())
            db.copy_format_to(book_id, source_format, str(source))
            if not source.exists() or source.stat().st_size == 0:
                raise ValueError(f'无法取得 {source_format} 文件。')
            if direct:
                return source, title, temp_root
            if not get_state().storage.get('readerAutoConvert', True):
                raise ValueError(f'当前书只有 {", ".join(formats)} 格式。请先转换为 EPUB，或在设置中开启自动转换。')
            return self._convert_to_epub(source, temp_root), title, temp_root
        except Exception:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise

    def _convert_to_epub(self, source, temp_root):
        converter = app_executable('ebook-convert')
        if not converter:
            raise RuntimeError('没有找到 Calibre 的 ebook-convert 程序，无法自动转换此格式。')
        output = Path(temp_root) / 'converted.epub'
        try:
            kwargs = {'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT, 'text': True, 'encoding': 'utf-8', 'errors': 'replace'}
            if os.name == 'nt':
                kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            process = subprocess.run([converter, str(source), str(output)], timeout=600, **kwargs)
        finally:
            pass
        if process.returncode != 0 or not output.exists():
            details = (process.stdout or '')[-8000:]
            raise RuntimeError('自动转换为 EPUB 失败。\n\n' + details)
        return output

    def open_local_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self.gui, '打开电子书', '',
            '电子书 (*.epub *.htmlz *.txt *.html *.htm *.xhtml *.azw3 *.mobi *.fb2 *.docx *.odt *.rtf *.pdf);;所有文件 (*)',
        )
        if not path:
            return
        temp_root = Path(tempfile.mkdtemp(prefix='lingkuma-calibre-file-'))
        source = temp_root / Path(path).name
        shutil.copy2(path, source)
        try:
            if source.suffix.lower() not in {'.epub', '.htmlz', '.txt', '.html', '.htm', '.xhtml'}:
                if not get_state().storage.get('readerAutoConvert', True):
                    raise ValueError('请先将该文件转换为 EPUB。')
                source = self._convert_to_epub(source, temp_root)
            self._open_prepared(source, title=Path(path).stem, temp_root=temp_root)
        except Exception as error:
            shutil.rmtree(temp_root, ignore_errors=True)
            error_dialog(self.gui, '无法打开文件', str(error), det_msg=traceback.format_exc(), show=True)

    def _open_prepared(self, source, book_id=None, title=None, temp_root=None):
        owned_root = Path(temp_root or tempfile.mkdtemp(prefix='lingkuma-calibre-book-'))
        try:
            work = owned_root / 'book'
            package = prepare_book(source, work, book_id=book_id, title=title)
            package.temp_owned = True
            print(f'[LingKuma calibre {VERSION_STR}] opening book={title!r} source={source}')
            reader = LingKumaReader(package, get_state(), self.resource_root, icon=self.icon, parent=self.gui)
            self.readers.append(reader)
            reader.destroyed.connect(lambda *_: self._discard_reader(reader, owned_root))
            reader.show()
            reader.raise_()
            reader.activateWindow()
        except Exception:
            shutil.rmtree(owned_root, ignore_errors=True)
            raise

    def _discard_reader(self, reader, temp_root=None):
        try: self.readers.remove(reader)
        except ValueError: pass
        if temp_root:
            shutil.rmtree(temp_root, ignore_errors=True)

    def show_settings(self, page=0):
        dialog = SettingsDialog(self.gui, on_saved=self.apply_settings, initial_page=int(page))
        dialog.exec()

    def apply_settings(self):
        for reader in list(self.readers):
            try: reader.apply_settings()
            except Exception: pass

    def shutting_down(self):
        """Release reader windows and loopback servers before calibre exits."""
        readers = list(getattr(self, 'readers', ()))
        self.readers = []
        print(f'[LingKuma calibre {VERSION_STR}] shutting down; readers={len(readers)}')
        for reader in readers:
            try:
                reader.shutdown()
            except Exception:
                print(f'[LingKuma calibre {VERSION_STR}] reader shutdown failed:')
                traceback.print_exc()
            try:
                reader.close()
            except Exception:
                pass

    def show_diagnostics(self):
        try:
            from calibre.constants import __version__ as calibre_version
        except Exception:
            calibre_version = 'unknown'
        missing = [name for name in RESOURCE_FILES if not safe_join(self.resource_root, name).is_file()]
        state = get_state()
        lines = [
            f'{PRODUCT} {VERSION_STR}',
            f'Calibre: {calibre_version}',
            f'运行资源: {len(RESOURCE_FILES) - len(missing)}/{len(RESOURCE_FILES)}',
            f'本地词汇: {len(state.words)}',
            f'状态文件: {state.path}',
            f'当前阅读器: {len(self.readers)}',
            '翻译引擎: ' + str(state.translation_config().get('provider') or 'google-web'),
            '详细解释 AI: ' + ('自定义接口' if state.effective_ai_config().get('source') == 'custom' else 'LingKuma 内置免费 GLM'),
        ]
        if missing:
            lines.append('缺少资源: ' + ', '.join(missing[:10]))
            error_dialog(self.gui, 'LingKuma 自检未通过', '\n'.join(lines), show=True)
        else:
            info_dialog(self.gui, 'LingKuma 自检通过', '\n'.join(lines), show=True)

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self.gui, '导入 LingKuma 数据', '', 'LingKuma 数据 (*.json *.txt *.csv);;所有文件 (*)')
        if not path: return
        try:
            count = get_state().import_data(Path(path).read_text(encoding='utf-8-sig'), merge=True)
            self.apply_settings()
            info_dialog(self.gui, '导入完成', f'已处理 {count} 条词汇记录。', show=True)
        except Exception as error:
            error_dialog(self.gui, '导入失败', str(error), show=True)

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self.gui, '导出 LingKuma 完整备份', 'lingkuma-calibre-backup.json', 'JSON (*.json)')
        if not path: return
        Path(path).write_text(json.dumps(get_state().export_data(), ensure_ascii=False, indent=2), encoding='utf-8')
        info_dialog(self.gui, '导出完成', path, show=True)
