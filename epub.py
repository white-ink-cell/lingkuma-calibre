# -*- coding: utf-8 -*-
"""Prepare calibre book formats for the embedded LingKuma reader."""

from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from calibre_plugins.lingkuma_calibre.compat import safe_join

HTML_EXTENSIONS = {'.html', '.htm', '.xhtml', '.xhtm'}


@dataclass
class Chapter:
    title: str
    path: str


@dataclass
class BookPackage:
    title: str
    root: Path
    chapters: list[Chapter]
    book_key: str
    source_path: Path
    temp_owned: bool = True
    metadata: dict = field(default_factory=dict)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()[:20]


def _safe_extract_zip(path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 20000:
            raise ValueError('电子书压缩包包含过多文件')
        total_size = sum(max(0, int(info.file_size)) for info in infos)
        if total_size > 2 * 1024 * 1024 * 1024:
            raise ValueError('电子书解压后超过 2 GB 安全限制')
        for info in infos:
            name = info.filename.replace('\\', '/')
            if not name or name.endswith('/'):
                if name:
                    safe_join(destination, name).mkdir(parents=True, exist_ok=True)
                continue
            target = safe_join(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)


def _local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def _element_text(node: ET.Element | None) -> str:
    if node is None:
        return ''
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()


def _href_path(value: str) -> str:
    # Drop fragment/query, URL-decode, and normalize to a relative POSIX path.
    raw = unquote(urlsplit(value or '').path).replace('\\', '/')
    parts = []
    for part in PurePosixPath(raw).parts:
        if part in {'', '.', '/'}:
            continue
        if part == '..':
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return '/'.join(parts)


def _relative_from(base_dir: str, href: str) -> str:
    base_parts = [x for x in PurePosixPath(base_dir).parts if x not in {'', '.', '/'}]
    href_parts = [x for x in PurePosixPath(_href_path(href)).parts if x not in {'', '.', '/'}]
    combined: list[str] = []
    for part in base_parts + href_parts:
        if part == '..':
            if combined:
                combined.pop()
        elif part != '.':
            combined.append(part)
    return '/'.join(combined)


def _parse_nav_labels(root: Path, opf_dir: str, manifest: dict[str, dict]) -> dict[str, str]:
    labels: dict[str, str] = {}
    nav_item = next((item for item in manifest.values() if 'nav' in item.get('properties', '').split()), None)
    if nav_item:
        nav_rel = _relative_from(opf_dir, nav_item.get('href', ''))
        nav_file = safe_join(root, nav_rel)
        try:
            tree = ET.parse(nav_file)
            nav_dir = str(PurePosixPath(nav_rel).parent)
            for node in tree.getroot().iter():
                if _local_name(node.tag).lower() != 'a':
                    continue
                href = node.attrib.get('href', '')
                label = _element_text(node)
                if href and label:
                    labels[_relative_from(nav_dir, href)] = label
        except Exception:
            pass

    ncx_item = next((item for item in manifest.values() if item.get('media-type') == 'application/x-dtbncx+xml'), None)
    if ncx_item:
        ncx_rel = _relative_from(opf_dir, ncx_item.get('href', ''))
        ncx_file = safe_join(root, ncx_rel)
        try:
            tree = ET.parse(ncx_file)
            ncx_dir = str(PurePosixPath(ncx_rel).parent)
            for nav_point in tree.getroot().iter():
                if _local_name(nav_point.tag) != 'navPoint':
                    continue
                text_node = next((x for x in nav_point.iter() if _local_name(x.tag) == 'text'), None)
                content_node = next((x for x in nav_point.iter() if _local_name(x.tag) == 'content'), None)
                label = _element_text(text_node)
                href = content_node.attrib.get('src', '') if content_node is not None else ''
                if href and label:
                    labels[_relative_from(ncx_dir, href)] = label
        except Exception:
            pass
    return labels


def _prepare_epub(source: Path, root: Path, book_key: str) -> BookPackage:
    _safe_extract_zip(source, root)
    container_path = root / 'META-INF' / 'container.xml'
    if not container_path.exists():
        raise ValueError('EPUB 缺少 META-INF/container.xml')
    container_tree = ET.parse(container_path)
    rootfile = next((node for node in container_tree.getroot().iter() if _local_name(node.tag) == 'rootfile'), None)
    if rootfile is None or not rootfile.attrib.get('full-path'):
        raise ValueError('EPUB 没有有效的 OPF 根文件')
    opf_rel = _href_path(rootfile.attrib['full-path'])
    opf_path = safe_join(root, opf_rel)
    opf_tree = ET.parse(opf_path)
    opf_root = opf_tree.getroot()
    opf_dir = str(PurePosixPath(opf_rel).parent)
    if opf_dir == '.':
        opf_dir = ''

    title = source.stem
    for node in opf_root.iter():
        if _local_name(node.tag).lower() == 'title' and _element_text(node):
            title = _element_text(node)
            break

    manifest: dict[str, dict] = {}
    for node in opf_root.iter():
        if _local_name(node.tag) != 'item':
            continue
        item_id = node.attrib.get('id')
        href = node.attrib.get('href')
        if item_id and href:
            manifest[item_id] = dict(node.attrib)

    labels = _parse_nav_labels(root, opf_dir, manifest)
    chapters: list[Chapter] = []
    seen: set[str] = set()
    for node in opf_root.iter():
        if _local_name(node.tag) != 'itemref':
            continue
        if node.attrib.get('linear', 'yes').lower() == 'no':
            continue
        item = manifest.get(node.attrib.get('idref', ''))
        if not item:
            continue
        media_type = item.get('media-type', '')
        rel = _relative_from(opf_dir, item.get('href', ''))
        if not rel or rel in seen or not safe_join(root, rel).exists():
            continue
        if media_type not in {'application/xhtml+xml', 'text/html'} and Path(rel).suffix.lower() not in HTML_EXTENSIONS:
            continue
        seen.add(rel)
        title_value = labels.get(rel) or Path(rel).stem.replace('_', ' ').replace('-', ' ').strip() or f'章节 {len(chapters) + 1}'
        chapters.append(Chapter(title=title_value, path=rel))

    if not chapters:
        chapters = _scan_html_chapters(root)
    if not chapters:
        raise ValueError('EPUB 中没有可读取的 HTML/XHTML 章节')
    return BookPackage(title=title, root=root, chapters=chapters, book_key=book_key, source_path=source, metadata={'format': 'EPUB'})


def _scan_html_chapters(root: Path) -> list[Chapter]:
    candidates = sorted(
        (path for path in root.rglob('*') if path.is_file() and path.suffix.lower() in HTML_EXTENSIONS),
        key=lambda p: (len(p.relative_to(root).parts), str(p).lower()),
    )
    chapters: list[Chapter] = []
    for path in candidates:
        rel = path.relative_to(root).as_posix()
        if rel.lower().endswith(('toc.html', 'toc.xhtml', 'nav.xhtml')) and len(candidates) > 1:
            continue
        chapters.append(Chapter(path=rel, title=path.stem.replace('_', ' ').replace('-', ' ') or f'章节 {len(chapters)+1}'))
    return chapters


def _prepare_htmlz(source: Path, root: Path, book_key: str) -> BookPackage:
    _safe_extract_zip(source, root)
    chapters = _scan_html_chapters(root)
    if not chapters:
        raise ValueError('HTMLZ 中没有可读取的 HTML 文件')
    return BookPackage(title=source.stem, root=root, chapters=chapters, book_key=book_key, source_path=source, metadata={'format': 'HTMLZ'})


def _prepare_text(source: Path, root: Path, book_key: str) -> BookPackage:
    root.mkdir(parents=True, exist_ok=True)
    raw = source.read_bytes()
    text = None
    for encoding in ('utf-8-sig', 'utf-8', 'gb18030', 'latin-1'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    text = text if text is not None else raw.decode('utf-8', errors='replace')
    paragraphs = []
    for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').replace('\r', '\n')):
        block = block.strip()
        if block:
            paragraphs.append(f'<p>{html.escape(block).replace(chr(10), "<br/>")}</p>')
    body = '\n'.join(paragraphs) or '<p></p>'
    target = root / 'index.html'
    target.write_text(
        '<!doctype html><html><head><meta charset="utf-8"><title>'
        + html.escape(source.stem)
        + '</title></head><body><article>' + body + '</article></body></html>',
        encoding='utf-8',
    )
    return BookPackage(title=source.stem, root=root, chapters=[Chapter(source.stem, 'index.html')], book_key=book_key, source_path=source, metadata={'format': 'TXT'})


def _prepare_single_html(source: Path, root: Path, book_key: str) -> BookPackage:
    root.mkdir(parents=True, exist_ok=True)
    target = root / source.name
    shutil.copy2(source, target)
    return BookPackage(title=source.stem, root=root, chapters=[Chapter(source.stem, source.name)], book_key=book_key, source_path=source, metadata={'format': source.suffix[1:].upper()})


def prepare_book(source_path: str | Path, work_root: str | Path, book_id: int | str | None = None, title: str | None = None) -> BookPackage:
    source = Path(source_path).resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(str(source))
    digest = _hash_file(source)
    book_key = f'calibre:{book_id}:{digest}' if book_id is not None else f'file:{digest}'
    root = Path(work_root).resolve() / digest
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    suffix = source.suffix.lower()
    if suffix == '.epub':
        package = _prepare_epub(source, root, book_key)
    elif suffix in {'.htmlz', '.zip'}:
        package = _prepare_htmlz(source, root, book_key)
    elif suffix == '.txt':
        package = _prepare_text(source, root, book_key)
    elif suffix in HTML_EXTENSIONS:
        package = _prepare_single_html(source, root, book_key)
    else:
        raise ValueError(f'暂不支持直接读取 {suffix or "未知"} 格式，请先转换为 EPUB')
    if title:
        package.title = str(title)
    return package
