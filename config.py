# -*- coding: utf-8 -*-
"""Native calibre settings, vocabulary and data-management UI."""

from __future__ import annotations

import base64
import csv
import io
import json
import os
import queue
import re
import secrets
import tempfile
import threading
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from calibre.utils.config import config_dir
from calibre.utils.localization import get_lang
from qt.core import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColor,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QEvent,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPointF,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextToSpeech,
    QTimer,
    QUrl,
    QVBoxLayout,
    QWheelEvent,
    QWidget,
    Qt,
)
from qt.webengine import QWebEnginePage, QWebEngineSettings

from calibre_plugins.lingkuma_calibre.compat import calibre_viewer_preferences
from calibre_plugins.lingkuma_calibre.gpt_tts import MAX_AUDIO_BYTES, prepare_gpt_tts_request
from calibre_plugins.lingkuma_calibre.edge_tts_host import fetch_edge_tts_audio, cancel_edge_tts_audio
from calibre_plugins.lingkuma_calibre.state import StateStore, normalize_status, normalize_word
from calibre_plugins.lingkuma_calibre.ui_locales import UPSTREAM_UI_I18N
from calibre_plugins.lingkuma_calibre.ui_port_locales import B01_UI_LOCALES, B02_UI_LOCALES, B03_UI_LOCALES, B04_UI_LOCALES, B05_UI_LOCALES, B06_UI_LOCALES, B07_UI_LOCALES, B08_UI_LOCALES, B09_UI_LOCALES, B10_UI_LOCALES, B01B01_UI_LOCALES, B01B02_UI_LOCALES, B01B03_UI_LOCALES, B01B04_UI_LOCALES, B01B05_UI_LOCALES, B01B06_UI_LOCALES, B01B07_UI_LOCALES, B01B08_UI_LOCALES, B01B09_UI_LOCALES, B01B10_UI_LOCALES, B01B11_UI_LOCALES, B01B12_UI_LOCALES, B01B13_UI_LOCALES, B01B14_UI_LOCALES, EDGE_TTS_ERROR_LOCALES, GPT_TTS_ERROR_LOCALES, PORT_UI_LOCALES, RAD_UI_LOCALES
from calibre_plugins.lingkuma_calibre.version import PRODUCT, USER_AGENT, VERSION_STR

PLUGIN_DIR = Path(config_dir) / 'plugins' / 'lingkuma-calibre'
STATE_PATH = PLUGIN_DIR / 'state.json'
_STATE: StateStore | None = None


def get_state() -> StateStore:
    global _STATE
    if _STATE is None:
        _STATE = StateStore(STATE_PATH)
    return _STATE


def _get_nested(data, path, fallback=None):
    current = data
    for part in path.split('.'):
        if not isinstance(current, dict) or part not in current:
            return fallback
        current = current[part]
    return current


def _set_nested(data, path, value):
    parts = path.split('.')
    current = data
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


_OPACITY_COLORS = {
    'wordExplosionHighlightOpacity': 'wordExplosionHighlightColor',
    'wordExplosionUnderlineOpacity': 'wordExplosionUnderlineColor',
    'posHighlightVerbBackgroundOpacity': 'posHighlightVerbBackgroundColor',
    'posHighlightPrepositionBackgroundOpacity': 'posHighlightPrepositionBackgroundColor',
}


def _color_opacity(color):
    match = re.fullmatch(r'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', str(color or ''))
    if not match:
        return None
    return int(int(match.group(1), 16) * 100 / 255 + .5) if match.group(1) else 100


def _edge_preview_percent(value):
    """Pass the settings percentage unambiguously to the existing Edge bridge."""
    return 'default' if value == 0 else f'{value:+g}%'


def _webdav_url(config):
    base = str(config.get('url') or '').strip()
    if not base:
        raise ValueError(_tr('请先填写 WebDAV 地址'))
    parts = urllib.parse.urlsplit(base)
    if parts.scheme.lower() not in {'http', 'https'} or not parts.netloc:
        raise ValueError(_tr('WebDAV 地址必须使用 HTTP 或 HTTPS'))
    filename = str(config.get('filename') or 'lingkuma-calibre-backup.json').strip()
    path = parts.path if parts.path.lower().endswith('.json') else parts.path.rstrip('/') + '/' + urllib.parse.quote(filename, safe='')
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, ''))


def _webdav_directory_url(config):
    base = str(config.get('url') or '').strip()
    if not base:
        raise ValueError(_tr('请先填写 WebDAV 地址'))
    parts = urllib.parse.urlsplit(base)
    if parts.scheme.lower() not in {'http', 'https'} or not parts.netloc:
        raise ValueError(_tr('WebDAV 地址必须使用 HTTP 或 HTTPS'))
    path = parts.path.rsplit('/', 1)[0] + '/' if parts.path.lower().endswith('.json') else parts.path.rstrip('/') + '/'
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, ''))


def _webdav_collection_confirmed(response, directory_url):
    body = response.read(1024 * 1024 + 1)
    if len(body) > 1024 * 1024 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        return False
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return False
    dav = '{DAV:}'
    if root.tag != dav + 'multistatus':
        return False
    target = urllib.parse.urlsplit(directory_url)
    for item in root.findall(dav + 'response'):
        href = item.findtext(dav + 'href')
        if not href:
            continue
        found = urllib.parse.urlsplit(urllib.parse.urljoin(directory_url, href))
        if (found.scheme.lower(), found.hostname, found.port) != (target.scheme.lower(), target.hostname, target.port):
            continue
        if urllib.parse.unquote(found.path).rstrip('/') != urllib.parse.unquote(target.path).rstrip('/'):
            continue
        for propstat in item.findall(dav + 'propstat'):
            status = propstat.findtext(dav + 'status') or ''
            if (re.match(r'^HTTP/\d(?:\.\d)?\s+200(?:\s|$)', status)
                    and propstat.find(dav + 'prop/' + dav + 'resourcetype/' + dav + 'collection') is not None):
                return True
    return False


def _webdav_headers(config, include_json=False):
    headers = {'User-Agent': USER_AGENT}
    username = str(config.get('username') or '')
    password = str(config.get('password') or '')
    if username or password:
        token = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')
        headers['Authorization'] = 'Basic ' + token
    if include_json:
        headers['Content-Type'] = 'application/json; charset=utf-8'
    return headers


def _webdav_request(config, method='GET', data=None, timeout=45):
    url = _webdav_url(config)
    headers = _webdav_headers(config, include_json=data is not None)
    authorization = headers.pop('Authorization', None)
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    if authorization:
        # urllib's redirect handler copies normal headers across origins.
        request.add_unredirected_header('Authorization', authorization)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        destination = response.geturl() if hasattr(response, 'geturl') else url
        source_parts, destination_parts = urllib.parse.urlsplit(url), urllib.parse.urlsplit(destination)
        if (source_parts.scheme.lower(), source_parts.hostname, source_parts.port) != (
                destination_parts.scheme.lower(), destination_parts.hostname, destination_parts.port):
            raise ValueError(_tr('WebDAV 请求被重定向到其他地址；已拒绝读取'))
        return response.status, response.read()


# Calibre adapter UI localization.  This is intentionally isolated from the
# reader/runtime code: it only changes labels shown by the native Qt settings
# windows.  Chinese Calibre stays Chinese; other UI languages fall back to
# English so the port is usable outside a Chinese desktop.
_UI_EN = {
    '书页设置': 'Page appearance', '保存': 'Save', '应用': 'Apply', '取消': 'Cancel', '选择颜色': 'Choose color',
    'LingKuma 使用独立阅读窗口，因此 Calibre 原生阅读器的“书页设置”面板不会自动出现在这里。本窗口直接控制当前 LingKuma 书页的字体、宽度、页边距和颜色。': 'LingKuma uses its own reader window, so Calibre’s native page-appearance panel is not shown here. These controls directly change the current LingKuma page font, width, margins and colors.',
    '跟随 Calibre 阅读器': 'Follow Calibre reader', '保留 EPUB 原书排版': 'Preserve EPUB layout', '自定义书页': 'Custom page',
    '页面排版': 'Page layout', '羊皮纸': 'Paper', '白色': 'Light', '深色': 'Dark', '自定义颜色': 'Custom colors', '颜色预设': 'Color preset',
    '正文字体': 'Body font', '正文字号': 'Font size', '行距': 'Line height', '正文最大宽度': 'Maximum text width', '正文宽度': 'Text width',
    '上': 'Top', '右': 'Right', '下': 'Bottom', '左': 'Left', '页边距': 'Margins', '页面背景': 'Page background', '文字颜色': 'Text color', '链接颜色': 'Link color',
    '读取 Calibre 当前设置': 'Load current Calibre settings', '选择': 'Choose', '无法应用书页设置': 'Could not apply page appearance', '无法保存书页设置': 'Could not save page appearance',
    'LingKuma for calibre 设置': 'LingKuma for calibre Settings', '完整语言学习、阅读器、AI、词库和同步设置': 'Language learning, reader, AI, vocabulary and sync settings',
    '界面语言': 'Interface language', '自动（跟随 Calibre）': 'Auto (follow Calibre)', '中文': 'Chinese', '保存后重新打开设置窗口生效': 'Takes effect the next time the settings window is opened',
    '基础设置': 'General', '整句翻译与单词爆炸': 'Sentence translation & Word Explosion', '查词弹窗': 'Word tooltip', 'AI / API 配置': 'AI / API',
    'TTS 配置': 'TTS', '数据库与 WebDAV': 'Database & WebDAV', '单词列表': 'Vocabulary', '阅读器': 'Reader', '关于': 'About', '保存并应用': 'Save & apply',
    '词典': 'Dictionary', '使用默认词典': 'Use default dictionary', '使用自定义词典': 'Use custom dictionary', '导入自定义词典': 'Import custom dictionary', '刷新词典状态': 'Refresh dictionary status', '词典状态不可用': 'Dictionary status unavailable', '未确定当前语言组合': 'Current language pair unknown', '自定义词典已导入。': 'Custom dictionary imported.', '当前：自定义词典': 'Current: custom dictionary', '当前：默认词典': 'Current: default dictionary',
    '启用': 'Enabled', '单词高亮（总开关）': 'Word highlighting (master switch)', 'LingKuma 原版总开关：关闭后高亮、查词和整句翻译都会停止': 'Original LingKuma master switch: disabling it stops highlighting, lookup and sentence translation.',
    'Kuma 小按钮': 'Kuma floating controls', '在阅读页面显示开关和明暗按钮': 'Show enable and light/dark controls on the reading page.',
    '英文高亮': 'Highlight alphabetic words', '中文高亮': 'Highlight Chinese', '日语高亮': 'Highlight Japanese', '韩语高亮': 'Highlight Korean',
    '自动识别日语汉字': 'Auto-detect Japanese kanji', '日语 Kuromoji 分词（实验）': 'Japanese Kuromoji tokenization (experimental)',
    '自动语言学习': 'Automatic language learning', '自动生成第一条中文释义': 'Auto-generate first translation', '自动生成第二条中文释义': 'Auto-generate contextual explanation',
    '自动保存 AI 释义': 'Auto-save AI translations', '为新词保存 AI 释义': 'Save AI translations for new words', '自动保存例句': 'Auto-save example sentences', '每词自动保存例句上限': 'Maximum auto-saved examples per word',
    '启用整句翻译面板': 'Enable sentence translation panel', '触发方式': 'Trigger', '点击单词': 'Click word', '双击': 'Double-click', '选择文字': 'Select text',
    '面板位置': 'Panel position', '自动': 'Auto', '上方': 'Above', '下方': 'Below', '单词排列': 'Word layout', '一列': 'One column', '两列': 'Two columns', '三列': 'Three columns',
    '每个词显示释义': 'Translations per word', '全部': 'All', '1 条': '1', '2 条': '2', '整句译文数量': 'Sentence translations', '字号': 'Font size', '最大宽度': 'Maximum width',
    '优先显示在上方': 'Prefer above', '高亮原句': 'Highlight source sentence', '在面板中显示英文原句': 'Show source sentence in panel', '句子标记': 'Sentence marking',
    '句子高亮颜色': 'Sentence highlight color', '显示下划线': 'Show underline', '下划线样式': 'Underline style', '实线': 'Solid', '虚线': 'Dashed', '点线': 'Dotted', '下划线颜色': 'Underline color', '下划线粗细': 'Underline thickness',
    '查词弹窗行为': 'Tooltip behavior', '只在点击时显示': 'Show only on click', '自动展开完整弹窗': 'Auto-expand full tooltip', '点击其他位置自动关闭': 'Close when clicking elsewhere',
    '再次点击时刷新': 'Refresh on repeated click', '默认显示详细内容': 'Show details by default', '默认展开句子区域': 'Expand sentence section by default', '默认展开释义胶囊': 'Expand translation capsules by default',
    '优先在单词上方显示': 'Prefer above word', '选区弹窗优先向下显示': 'Prefer selection popup below', '单词与弹窗间距': 'Word-to-tooltip gap', '选词弹窗间距': 'Selection popup gap', '外观': 'Appearance', '主题': 'Theme', '浅色': 'Light',
    '图案背景': 'Pattern background', '液态玻璃效果': 'Liquid glass effect', '分析面板玻璃效果': 'Analysis-panel glass effect', '玻璃类型': 'Glass type', '关闭': 'Off', '轻度': 'Light', '完整': 'Full',
    '自定义胶囊': 'Custom capsules', '恢复被缩小的弹窗': 'Restore minimized tooltip',
    '普通单词译文和整句翻译优先使用专用翻译引擎；第二条语境解释、词性标签和自由分析仍由 AI 完成。': 'Word translations and sentence translations use the selected translation engine first. Context explanations, POS/tags and free-form analysis still use AI.',
    '快速翻译引擎': 'Translation', '翻译服务': 'Translation service', 'Google Web Translate（免 Key，实验性）': 'Google Web Translate (no key, experimental)',
    'Microsoft Translator（需自己的 Key）': 'Microsoft Translator (your key required)', 'Google Cloud Translation（需自己的 Key）': 'Google Cloud Translation (your key required)', 'LingKuma AI（最完整但较慢）': 'LingKuma AI (fullest, slower)',
    '目标语言': 'Target language', '翻译服务失败时回退到 LingKuma AI': 'Fall back to LingKuma AI if translation service fails', '翻译超时': 'Translation timeout',
    'Google Web Translate 不需要 Key，速度通常快于生成式 AI，但它不是面向第三方插件承诺稳定性的正式接口；若失效，可切换到 Microsoft/Google Cloud 官方接口或启用 AI 回退。': 'Google Web Translate needs no key and is usually faster than generative AI, but it is not a stability-guaranteed third-party API. If it stops working, switch to Microsoft/Google Cloud or enable AI fallback.',
    'Calibre 请求调度': 'Calibre request scheduling', '启用快速调度（推荐）': 'Enable fast scheduling (recommended)', '整句生词合并翻译': 'Batch sentence-word translations',
    '详细解释使用的 OpenAI 兼容接口': 'OpenAI-compatible API for detailed explanations', 'API 地址': 'API endpoint', '模型': 'Model', '留空使用 LingKuma 默认服务': 'Leave blank to use LingKuma default service',
    '可选提示词覆盖': 'Optional prompt overrides', '第一条中文释义提示词': 'First translation prompt', '第二条中文释义提示词': 'Second/context explanation prompt', '词性与标签提示词': 'POS/tag prompt',
    '整句翻译提示词': 'Sentence translation prompt', '句子分析提示词': 'Sentence analysis prompt', '语言检测提示词': 'Language detection prompt', '高级': 'Advanced', '留空使用 LingKuma 原始提示词': 'Leave blank to use the original LingKuma prompt',
    '朗读总设置': 'TTS general', '单词朗读': 'Word TTS', '句子朗读': 'Sentence TTS', '句子朗读自动识别语言': 'Auto-detect sentence TTS language', '系统本地语音': 'System voice',
    '自定义 URL 1': 'Custom URL 1', '自定义 URL 2': 'Custom URL 2', '单词语音渠道': 'Word TTS provider', '句子语音渠道': 'Sentence TTS provider', '语音名称': 'Voice name', '留空自动选择': 'Leave blank for automatic selection',
    '速度': 'Speed', '音调': 'Pitch', '自动选择语音': 'Select voice automatically', '语音': 'Voice', '音量': 'Volume', '声音': 'Voice', '音频格式': 'Audio format', '朗读指令': 'TTS instructions',
    '自定义单词音频': 'Custom word audio', '使用 {word}、{lang}': 'Use {word}, {lang}', '模板说明 / 备注': 'Template notes',
    '本地数据库': 'Local database', '导出完整备份': 'Export full backup', '导入并合并': 'Import & merge', '导入并替换': 'Import & replace', '清空词库': 'Clear vocabulary',
    'WebDAV 多设备同步': 'WebDAV multi-device sync', 'WebDAV 地址': 'WebDAV URL', '用户名': 'Username', '密码': 'Password', '备份文件名': 'Backup filename', '测试连接': 'Test connection',
    '上传当前数据': 'Upload current data', '下载并合并': 'Download & merge', '下载并替换': 'Download & replace', 'EPUB 文本修复': 'EPUB text repair', '移除软连字符': 'Remove soft hyphens', '修复换行断词': 'Repair line-break hyphenation',
    '搜索单词、释义或标签': 'Search words, translations or tags', '全部状态': 'All statuses', '未分级': 'Unrated', '陌生': 'Unknown', '初识': 'New', '学习中': 'Learning', '较熟悉': 'Familiar', '已掌握': 'Known',
    '刷新': 'Refresh', '单词': 'Word', '状态': 'Status', '中文释义': 'Translations', '标签': 'Tags', '例句数': 'Examples', '保存表格修改': 'Save table changes', '删除所选词': 'Delete selected words', '导入已知单词': 'Import known words', '导出学习数据': 'Export learning data',
    'LingKuma 阅读器': 'LingKuma Reader', '自定义阅读主题': 'Custom reader theme', '自定义字体名称': 'Custom font family', '例如 Georgia / Microsoft YaHei': 'e.g. Georgia / Microsoft YaHei',
    '自定义页边距与颜色': 'Custom margins & colors', '上边距': 'Top margin', '右边距': 'Right margin', '下边距': 'Bottom margin', '左边距': 'Left margin', '页面背景色': 'Page background', '阅读行为': 'Reading behavior',
    '记住每本书阅读位置': 'Remember reading position per book', '自动将其他格式转换为 EPUB': 'Automatically convert other formats to EPUB',
    '阅读窗口工具栏新增“书页设置”（Ctrl+Shift+P），可以在读书时直接修改字体、正文宽度、页边距和页面颜色并立即应用。LingKuma Reader 是独立窗口，因此不会弹出 Calibre 原生 ebook-viewer 的设置面板。': 'The reader toolbar includes “Page appearance” (Ctrl+Shift+P), which changes font, text width, margins and page colors immediately. LingKuma Reader is a separate window, so Calibre’s native ebook-viewer settings panel is not opened.',
    'LingKuma 使用独立的完整原生设置窗口。点击下面的按钮进行配置。': 'LingKuma uses a separate full native settings window. Click the button below to configure it.', '打开 LingKuma 完整设置': 'Open LingKuma settings',
}

# Labels added since the first Calibre port; keep its existing translations.
_UI_EN.update({
    '英语': 'English', '德语': 'German', '法语': 'French', '西班牙语': 'Spanish',
    '日语': 'Japanese', '韩语': 'Korean', '俄语': 'Russian', '意大利语': 'Italian',
    '测试本地语音': 'Test local speech',
    '当前系统没有可用的本地 TTS': 'No local TTS engine is available',
    '本地 TTS 测试失败': 'Local TTS test failed',
    'AI 配置档': 'AI profiles', '当前配置档': 'Active profile',
    '轮询已启用的配置档': 'Rotate enabled profiles',
    '配置档名称': 'Profile name', '配置档 API 地址': 'Profile API endpoint',
    '配置档模型': 'Profile model', '配置档 API Key': 'Profile API key',
    '配置档 Temperature': 'Profile temperature', '加入轮询': 'Include in rotation',
    '不发送 Temperature': 'Omit temperature', '自定义请求参数': 'Custom request fields',
    '每行 key=JSON': 'One key=JSON per line',
    '新增配置档': 'Add profile', '复制配置档': 'Copy profile',
    '删除配置档': 'Delete profile',
    '原有单接口回退设置': 'Legacy single-endpoint fallback',
    '当前配置档填写 API 地址后优先使用该配置档；留空时使用下方原有接口设置，仍为空则使用 LingKuma 默认服务。':
        'An active profile with an API endpoint takes priority. If it is empty, use the legacy endpoint below; if both are empty, use the default LingKuma service.',
    '配置档数据超出当前编辑范围或不完整；原始数据已保留，当前窗口不会改写配置档。':
        'Profile data exceeds the editor limits or is incomplete. Original data is preserved; this window will not rewrite profiles.',
    '小按钮控制范围': 'Floating control scope', '所有阅读器': 'All readers', '当前阅读器': 'Current reader',
    '日语页面自动加载 Kuromoji': 'Load Kuromoji on Japanese pages',
    'Bionic Reading（长文可能影响性能）': 'Bionic Reading (may slow long texts)',
    '启用 Bionic Reading（默认关闭）': 'Enable Bionic Reading (off by default)',
    '字体': 'Font', 'Reading Ruler（阅读标尺）': 'Reading Ruler',
    '启用 Reading Ruler（默认关闭）': 'Enable Reading Ruler (off by default)',
    '反色遮罩': 'Dim outside the ruler', '宽度模式': 'Width mode', '全屏': 'Full width',
    '自定义': 'Custom', '自定义宽度': 'Custom width', '标尺高度': 'Ruler height',
    '透明度': 'Opacity', '颜色': 'Color', 'POS Highlight（词性高亮）': 'POS Highlight',
    '启用 POS Highlight（默认关闭）': 'Enable POS Highlight (off by default)',
    '语言': 'Language', '德语': 'German', '英语': 'English', '高亮动词': 'Highlight verbs',
    '动词背景色': 'Verb background', '动词背景颜色': 'Verb background color',
    '动词背景透明度': 'Verb background opacity', '动词下划线': 'Verb underline',
    '动词下划线样式': 'Verb underline style', '波浪线': 'Wavy',
    '动词下划线颜色': 'Verb underline color', '动词下划线粗细': 'Verb underline thickness',
    '动词下划线位置': 'Verb underline position', '底部': 'Bottom', '顶部': 'Top',
    '高亮介词': 'Highlight prepositions', '介词背景色': 'Preposition background',
    '介词背景颜色': 'Preposition background color', '介词背景透明度': 'Preposition background opacity',
    '介词下划线': 'Preposition underline', '介词下划线样式': 'Preposition underline style',
    '介词下划线颜色': 'Preposition underline color', '介词下划线粗细': 'Preposition underline thickness',
    '介词下划线位置': 'Preposition underline position', '悬停': 'Hover',
    '手动拖动': 'Drag manually', '横向': 'Horizontal', '纵向': 'Vertical',
    '面板排列': 'Panel layout', '3 条': '3', '单词爆炸优先模式': 'Word Explosion priority mode',
    '朗读时逐词高亮': 'Highlight words during speech',
    '静音时逐词高亮': 'Highlight words without speech',
    '只朗读，不逐词高亮': 'Speak without word highlighting',
    '逐词高亮速度': 'Word highlighting speed', '显示熟句动画': 'Animate familiar sentences',
    '句子高亮透明度': 'Sentence highlight opacity', '上下都有': 'Both',
    '下划线位置': 'Underline position', '下划线透明度': 'Underline opacity',
    '选词弹窗优先显示在下方': 'Prefer selection popup below',
    '内置背景类型': 'Built-in background type', '随机 SVG 图案': 'Random SVG pattern',
    '设备像素缩放': 'Device pixel scaling', '阅读快捷键': 'Reading shortcuts',
    '查词': 'Look up word', '复制句子': 'Copy sentence', '分析窗口': 'Analysis window',
    '句子爆炸': 'Sentence explosion', '切换词汇状态': 'Change word status',
    '添加 AI 释义': 'Add AI meaning', '关闭弹窗': 'Close popup',
    '每批最多单词数': 'Maximum words per batch',
    '同时进行的详细 AI 请求': 'Concurrent detailed AI requests',
    '高级提示词': 'Advanced prompts', '自动朗读单词': 'Speak words automatically',
    'URL 模板 1': 'URL template 1', 'URL 模板 2': 'URL template 2',
    ' 秒': ' s',
    '例如：Speak clearly and naturally.': 'For example: Speak clearly and naturally.',
    '一个字符，或输入 Tab / Space 等按键名': 'One character, or a key name such as Tab or Space',
    '[{"label":"例子","prompt":"……"}]': '[{"label":"Example","prompt":"..."}]',
    '原有值（当前不可选：{value}）': 'Previous value (not selectable now: {value})',
    '（保留旧值 {value}）': ' (kept previous value {value})',
    '当前选项范围为 {minimum}–{maximum}。旧值 {value} 将保留；修改此项后使用新值。':
        'Current range: {minimum}–{maximum}. The previous value {value} is kept until you edit this setting.',
    '0 未分级': '0 Unrated', '1 陌生': '1 Unknown', '2 初识': '2 New',
    '3 学习中': '3 Learning', '4 较熟悉': '4 Familiar', '5 已掌握': '5 Known',
    '词汇状态 0': 'Word status 0', '词汇状态 1': 'Word status 1',
    '词汇状态 2': 'Word status 2', '词汇状态 3': 'Word status 3',
    '词汇状态 4': 'Word status 4', '词汇状态 5': 'Word status 5',
    '每页': 'Per page', '上一页': 'Previous', '下一页': 'Next',
    '第 {page} / {pages} 页，共 {count} 条': 'Page {page} / {pages}, {count} entries',
    '词汇状态无效': 'Invalid vocabulary status',
    '单词 {word} 的状态必须是 0–5。': 'Status for {word} must be 0–5.',
    '学习统计': 'Learning statistics', '当前词库统计': 'Current vocabulary statistics',
    '按词汇状态': 'By vocabulary status', '按语言': 'By language',
    '单词数': 'Words', '词库为空。': 'The vocabulary is empty.',
    '导入词汇': 'Import vocabulary',
    '粘贴 LingKuma JSON，或每行输入一个单词': 'Paste LingKuma JSON or one word per line',
    '导入方式': 'Import mode', '合并': 'Merge', '替换全部词库': 'Replace all vocabulary',
    '纯词表语言': 'Plain-list language', '日本語': 'Japanese',
    '自定义语言代码': 'Custom language code',
    '两个字母，例如 nl': 'Two letters, e.g. nl',
    '纯词表状态': 'Plain-list status',
    '5 完全掌握': '5 Mastered', '4 几乎掌握': '4 Almost mastered',
    '3 较熟悉': '3 Familiar', '2 继续学习': '2 Keep learning',
    '1 学习中': '1 Learning', '0 未知': '0 Unknown',
    '选择文件': 'Choose file', '清空输入': 'Clear input',
    '选择词汇文件': 'Choose vocabulary file',
    '词汇文件 (*.json *.txt *.csv);;所有文件 (*)': 'Vocabulary files (*.json *.txt *.csv);;All files (*)',
    '替换将删除当前全部词汇记录，是否继续？': 'Replacement will delete all current vocabulary records. Continue?',
    '基于开源项目 LingKuma 1.1.1，将原有高亮、查词弹窗、AI 中文释义、整句翻译、词库、例句与 TTS 代码复用于 Calibre 桌面环境。':
        'Based on the open-source LingKuma 1.1.1 project, reusing its highlighting, word tooltip, AI meanings, sentence translation, vocabulary, examples and TTS in Calibre.',
    '本移植版使用独立适配层提供 Chrome storage/runtime 接口；上游 LingKuma 代码和许可证保留在插件包内。':
        'This port provides Chrome storage/runtime compatibility in a separate adapter layer; the upstream LingKuma code and license remain in the plugin package.',
    '已恢复': 'Restored',
    '最小化状态已清除。重新点击单词后会显示完整弹窗。':
        'Minimized state cleared. Click a word to show the full tooltip again.',
    '无法保存设置': 'Could not save settings', '保存完成': 'Saved',
    '词库修改已经保存。': 'Vocabulary changes have been saved.',
    '确认删除': 'Confirm deletion', '删除所选 {count} 个单词？': 'Delete {count} selected words?',
    '导出 LingKuma 备份': 'Export LingKuma backup', '导出完成': 'Export complete',
    '导入 LingKuma 数据': 'Import LingKuma data',
    'LingKuma 数据 (*.json *.txt *.csv);;所有文件 (*)': 'LingKuma data (*.json *.txt *.csv);;All files (*)',
    '导入完成': 'Import complete', '已处理 {count} 条词汇记录。': 'Processed {count} vocabulary records.',
    '导入失败': 'Import failed', '确认清空': 'Confirm clearing', '清空失败': 'Clearing failed',
    '这会删除全部本地词汇记录，是否继续？': 'This deletes all local vocabulary records. Continue?',
    '例句清理': 'Example cleanup', '每个词最多保留的例句数量': 'Maximum examples per word',
    '清理多余例句': 'Remove excess examples', '确认清理例句': 'Confirm example cleanup',
    '确定要将每个词的例句保留为前 {count} 条吗？此操作不可撤销。': 'Keep the first {count} examples for each word? This cannot be undone.',
    '清理例句失败': 'Example cleanup failed', '例句清理完成': 'Example cleanup complete',
    '已删除 {count} 条多余例句。': 'Removed {count} excess examples.',
    '服务器可以访问（HTTP {status}）。': 'Server reachable (HTTP {status}).',
    'WebDAV 地址必须使用 HTTP 或 HTTPS': 'WebDAV URL must use HTTP or HTTPS',
    'WebDAV 目录未返回有效响应（HTTP {status}）。': 'WebDAV directory did not return a valid response (HTTP {status}).',
    'WebDAV 连接失败': 'WebDAV connection failed',
    '上传完成': 'Upload complete', 'WebDAV 返回 HTTP {status}。': 'WebDAV returned HTTP {status}.',
    'WebDAV 上传未确认成功（HTTP {status}）。': 'WebDAV upload was not confirmed successful (HTTP {status}).',
    '上传失败': 'Upload failed', '覆盖确认': 'Confirm replacement',
    '导入并替换会更新本地设置并替换全部词库，是否继续？':
        'Import and replace will update local settings and replace all vocabulary. Continue?',
    '下载并替换会覆盖本地设置和词库，是否继续？':
        'Download and replace will overwrite local settings and vocabulary. Continue?',
    '下载完成': 'Download complete', '下载失败': 'Download failed',
    '请先填写 WebDAV 地址': 'Enter a WebDAV URL first.',
    '自定义胶囊 JSON 无效：{error}': 'Invalid custom-capsule JSON: {error}',
    '颜色格式无效：{key}；需要 #RRGGBB 或 #RRGGBBAA':
        'Invalid color for {key}; use #RRGGBB or #RRGGBBAA.',
    '快捷键无效：{key}': 'Invalid shortcut: {key}',
    '快捷键冲突：{key} 与 {prior}': 'Shortcut conflict: {key} and {prior}',
    '{key} 不是有效颜色': '{key} is not a valid color',
})


_UI_LANGUAGES = ('zh', 'zh_TW', 'en', 'de', 'fr', 'es', 'ja', 'ko', 'ru', 'it')
_UPSTREAM_ZH_KEYS = {value: key for key, value in UPSTREAM_UI_I18N['zh'].items()}
_UPSTREAM_EN_KEYS = {value: key for key, value in UPSTREAM_UI_I18N['en'].items()}
_UI_PORT_LOCALES = {
    'zh_TW': {'基础设置': '基本設定', '界面语言': '介面語言'},
    'de': {'基础设置': 'Allgemein', '界面语言': 'Oberflächensprache'},
    'fr': {'基础设置': 'Général', '界面语言': "Langue de l’interface"},
    'es': {'基础设置': 'General', '界面语言': 'Idioma de la interfaz'},
    'ja': {'基础设置': '基本設定', '界面语言': '表示言語'},
    'ko': {'基础设置': '기본 설정', '界面语言': '인터페이스 언어'},
    'ru': {'基础设置': 'Основные настройки', '界面语言': 'Язык интерфейса'},
    'it': {'基础设置': 'Impostazioni generali', '界面语言': "Lingua dell'interfaccia"},
}


def _ui_language_mode(selected=None) -> str:
    """Resolve the native settings language without changing stored preferences."""
    if selected is None:
        try:
            selected = get_state().storage.get('interfaceLanguage') or 'auto'
        except Exception:
            selected = 'auto'
    mode = str(selected).strip().replace('-', '_')
    if mode.lower() == 'auto':
        try:
            mode = str(get_lang() or 'en').replace('-', '_')
        except Exception:
            mode = 'en'
    if mode.lower().startswith('zh'):
        return 'zh_TW' if mode.lower() in {'zh_tw', 'zh_hk', 'zh_mo'} else 'zh'
    code = mode.lower().split('_', 1)[0]
    return code if code in _UI_LANGUAGES else 'en'


def _ui_is_chinese() -> bool:
    return _ui_language_mode() == 'zh'


def _tr(text: str, language=None) -> str:
    mode = _ui_language_mode(language)
    if mode == 'zh':
        return EDGE_TTS_ERROR_LOCALES['zh'].get(text, GPT_TTS_ERROR_LOCALES['zh'].get(text, text))
    status_label = re.fullmatch(r'词汇状态 ([0-5])', text)
    if status_label:
        template = PORT_UI_LOCALES.get(mode, {}).get('词汇状态 {status}')
        if template is not None:
            return template.format(status=status_label.group(1))
    numbered_status = re.fullmatch(r'([0-5]) (未分级|陌生|初识|学习中|较熟悉|已掌握|完全掌握|几乎掌握|继续学习|未知)', text)
    if numbered_status:
        translated_label = PORT_UI_LOCALES.get(mode, {}).get(numbered_status.group(2))
        if translated_label is not None:
            return f'{numbered_status.group(1)} {translated_label}'
    # User-reviewed port labels take precedence where upstream lacks a complete
    # translation or uses an incorrect one for this native settings surface.
    translated = PORT_UI_LOCALES.get(mode, {}).get(text)
    if translated is not None:
        return translated
    english = _UI_EN.get(text, text)
    if mode == 'en':
        return english
    if text in _UI_PORT_LOCALES.get(mode, {}):
        return _UI_PORT_LOCALES[mode][text]
    key = _UPSTREAM_ZH_KEYS.get(text) or _UPSTREAM_EN_KEYS.get(english)
    return UPSTREAM_UI_I18N[mode].get(key, english) if key else english


def _webdav_error_text(error, language):
    detail = str(error)
    for source in B01B13_UI_LOCALES['en']:
        if detail == source or any(detail == translations[source]
                                   for translations in B01B13_UI_LOCALES.values()):
            return _tr(source, language)
    return detail


def _localize_static_widgets(root, language=None) -> None:
    """Relocalize static Qt labels from their original text, preserving inputs."""
    def translated(owner, field, current):
        # Store provenance on the Qt object. Python wrappers for the same
        # child can change between traversals, and their id() can be reused.
        property_name = f'_lk_i18n_{field!r}'
        original = owner.property(property_name + '_original')
        previous = owner.property(property_name + '_previous')
        if original is None:
            original = current
        if current != previous:
            original = current
        result = _tr(original, language)
        owner.setProperty(property_name + '_original', original)
        owner.setProperty(property_name + '_previous', result)
        return result

    if hasattr(root, 'windowTitle'):
        root.setWindowTitle(translated(root, 'title', root.windowTitle()))
    for widget in root.findChildren(QWidget):
        if isinstance(widget, QLabel):
            if widget.property('_lk_i18n_preserve_html') or widget.property('_lk_i18n_dynamic_mode'):
                continue
            widget.setText(translated(widget, 'text', widget.text()))
        elif isinstance(widget, QGroupBox):
            widget.setTitle(translated(widget, 'title', widget.title()))
        elif isinstance(widget, QPushButton):
            widget.setText(translated(widget, 'text', widget.text()))
        elif isinstance(widget, QCheckBox):
            widget.setText(translated(widget, 'text', widget.text()))
        elif isinstance(widget, QLineEdit):
            widget.setPlaceholderText(translated(widget, 'placeholder', widget.placeholderText()))
        elif isinstance(widget, QPlainTextEdit):
            widget.setPlaceholderText(translated(widget, 'placeholder', widget.placeholderText()))
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setSuffix(translated(widget, 'suffix', widget.suffix()))
        elif isinstance(widget, QComboBox):
            if widget.property('_lk_i18n_preserve_items'):
                continue
            selected = widget.currentIndex()
            draft = widget.currentText() if widget.property('_lk_i18n_preserve_edit') and (
                selected < 0 or widget.currentText() != widget.itemText(selected)) else None
            for index in range(widget.count()):
                widget.setItemText(index, translated(widget, ('item', index), widget.itemText(index)))
            if draft is not None:
                widget.setEditText(draft)
        elif isinstance(widget, QListWidget):
            for index in range(widget.count()):
                item = widget.item(index)
                item.setText(translated(widget, ('item', index), item.text()))
        elif isinstance(widget, QTableWidget):
            for index in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(index)
                if item:
                    item.setText(translated(widget, ('header', index), item.text()))


STYLE = """
QDialog, QWidget { font-size: 13px; }
QDialog { background: #f2f0e9; }
QListWidget { background: rgba(255,255,255,0.60); border: 1px solid #d8d2c4; border-radius: 14px; padding: 6px; }
QListWidget::item { padding: 10px 12px; margin: 2px; border-radius: 10px; }
QListWidget::item:selected { background: #ecd9cb; color: #9b3f25; font-weight: 600; }
QGroupBox { background: rgba(255,255,255,0.72); border: 1px solid #d9d3c7; border-radius: 14px; margin-top: 15px; padding: 18px 12px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTableWidget { background: #fff; border: 1px solid #d8d3c9; border-radius: 8px; padding: 5px; selection-background-color: #d45f3e; }
QPushButton { min-height: 27px; padding: 3px 12px; border-radius: 9px; border: 1px solid #d4cec2; background: #fff; }
QPushButton:hover { background: #f4e4da; }
QPushButton#primary { background: #d86240; color: white; border: none; font-weight: 600; }
QLabel#pageTitle { font-size: 21px; font-weight: 700; color: #3d332b; }
QLabel#muted { color: #777269; }
"""


class ReaderAppearanceDialog(QDialog):
    """Direct page appearance controls for the independent LingKuma reader."""

    def __init__(self, parent=None, on_applied=None, state=None):
        super().__init__(parent)
        self.state = state or get_state()
        self.on_applied = on_applied
        self.setWindowTitle('书页设置')
        self.setMinimumWidth(620)
        self.setStyleSheet(STYLE)
        outer = QVBoxLayout(self)

        note = QLabel(
            'LingKuma 使用独立阅读窗口，因此 Calibre 原生阅读器的“书页设置”面板不会自动出现在这里。'
            '本窗口直接控制当前 LingKuma 书页的字体、宽度、页边距和颜色。'
        )
        note.setWordWrap(True)
        note.setObjectName('muted')
        outer.addWidget(note)

        form = QFormLayout()
        self.layout_mode = QComboBox()
        self.layout_mode.addItem('跟随 Calibre 阅读器', 'calibre')
        self.layout_mode.addItem('保留 EPUB 原书排版', 'original')
        self.layout_mode.addItem('自定义书页', 'custom')
        form.addRow('页面排版', self.layout_mode)

        self.theme = QComboBox()
        for label, value in [('羊皮纸', 'paper'), ('白色', 'light'), ('深色', 'dark'), ('自定义颜色', 'custom')]:
            self.theme.addItem(label, value)
        form.addRow('颜色预设', self.theme)

        self.font_family = QComboBox()
        self.font_family.setEditable(True)
        self.font_family.setProperty('_lk_i18n_preserve_items', True)
        self.font_family.addItems(['', 'Georgia', 'Times New Roman', 'Arial', 'Microsoft YaHei', 'Noto Serif', 'Noto Sans'])
        form.addRow('正文字体', self.font_family)

        self.font_size = QSpinBox(); self.font_size.setRange(8, 72); self.font_size.setSuffix(' px')
        self.line_height = QDoubleSpinBox(); self.line_height.setRange(.8, 4); self.line_height.setSingleStep(.05); self.line_height.setDecimals(2)
        self.content_width = QSpinBox(); self.content_width.setRange(400, 2200); self.content_width.setSuffix(' px')
        form.addRow('正文字号', self.font_size)
        form.addRow('行距', self.line_height)
        form.addRow('正文最大宽度', self.content_width)

        margin_widget = QWidget(); margin_layout = QHBoxLayout(margin_widget); margin_layout.setContentsMargins(0, 0, 0, 0)
        self.margin_top = QSpinBox(); self.margin_right = QSpinBox(); self.margin_bottom = QSpinBox(); self.margin_left = QSpinBox()
        for label, widget in [('上', self.margin_top), ('右', self.margin_right), ('下', self.margin_bottom), ('左', self.margin_left)]:
            widget.setRange(0, 300); widget.setSuffix(' px')
            margin_layout.addWidget(QLabel(label)); margin_layout.addWidget(widget)
        form.addRow('页边距', margin_widget)

        self.background = self._color_row(form, '页面背景', '#f8f0dc')
        self.foreground = self._color_row(form, '文字颜色', '#4a372b')
        self.link = self._color_row(form, '链接颜色', '#6c4d2e')
        outer.addLayout(form)

        presets = QHBoxLayout()
        load_calibre = QPushButton('读取 Calibre 当前设置')
        load_calibre.clicked.connect(self.load_calibre_preferences)
        paper = QPushButton('羊皮纸'); paper.clicked.connect(lambda: self.apply_preset('paper'))
        light = QPushButton('白色'); light.clicked.connect(lambda: self.apply_preset('light'))
        dark = QPushButton('深色'); dark.clicked.connect(lambda: self.apply_preset('dark'))
        presets.addWidget(load_calibre); presets.addStretch(1); presets.addWidget(paper); presets.addWidget(light); presets.addWidget(dark)
        outer.addLayout(presets)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('保存')
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText('应用')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_safe)
        outer.addWidget(buttons)
        self.load()
        # Editing any page-specific value should immediately switch from the
        # inherited Calibre/original modes to the custom page mode.
        self.theme.currentIndexChanged.connect(self._mark_custom)
        self.font_family.editTextChanged.connect(self._mark_custom)
        self.font_size.valueChanged.connect(self._mark_custom)
        self.line_height.valueChanged.connect(self._mark_custom)
        self.content_width.valueChanged.connect(self._mark_custom)
        for widget in (self.margin_top, self.margin_right, self.margin_bottom, self.margin_left):
            widget.valueChanged.connect(self._mark_custom)
        for widget in (self.background, self.foreground, self.link):
            widget.textEdited.connect(self._mark_custom)
        _localize_static_widgets(self)

    def _mark_custom(self, *_args):
        index = self.layout_mode.findData('custom')
        if index >= 0 and self.layout_mode.currentIndex() != index:
            self.layout_mode.setCurrentIndex(index)

    def _color_row(self, form, label, default):
        row = QWidget(); layout = QHBoxLayout(row); layout.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(default); edit.setPlaceholderText('#RRGGBB')
        button = QPushButton('选择')
        button.clicked.connect(lambda: self.pick_color(edit))
        layout.addWidget(edit, 1); layout.addWidget(button)
        form.addRow(label, row)
        return edit

    def pick_color(self, edit):
        initial = QColor(edit.text().strip() or '#ffffff')
        color = QColorDialog.getColor(initial, self, _tr('选择颜色'))
        if color.isValid():
            edit.setText(color.name())
            self.theme.setCurrentIndex(self.theme.findData('custom'))

    def apply_preset(self, name):
        values = {
            'paper': ('#f8f0dc', '#4a372b', '#6c4d2e'),
            'light': ('#ffffff', '#222222', '#315f9f'),
            'dark': ('#222222', '#e6e0d7', '#8ab4f8'),
        }[name]
        self.background.setText(values[0]); self.foreground.setText(values[1]); self.link.setText(values[2])
        index = self.theme.findData(name)
        if index >= 0: self.theme.setCurrentIndex(index)
        self.layout_mode.setCurrentIndex(self.layout_mode.findData('custom'))

    def load_calibre_preferences(self):
        prefs = calibre_viewer_preferences()
        family = prefs.get('serifFamily') or prefs.get('sansFamily') or ''
        self.font_family.setCurrentText(str(family))
        if prefs.get('baseFontSize'): self.font_size.setValue(int(prefs['baseFontSize']))
        self.content_width.setValue(int(prefs.get('maxTextWidth') or 860))
        self.margin_top.setValue(int(prefs.get('marginTop') or 0)); self.margin_right.setValue(int(prefs.get('marginRight') or 0))
        self.margin_bottom.setValue(int(prefs.get('marginBottom') or 0)); self.margin_left.setValue(int(prefs.get('marginLeft') or 0))
        self.background.setText(str(prefs.get('backgroundColor') or '#ffffff'))
        self.foreground.setText(str(prefs.get('foregroundColor') or '#222222'))
        self.link.setText(str(prefs.get('linkColor') or '#315f9f'))
        self.layout_mode.setCurrentIndex(self.layout_mode.findData('calibre'))

    def load(self):
        storage = self.state.storage
        index = self.layout_mode.findData(storage.get('readerLayoutMode', 'calibre')); self.layout_mode.setCurrentIndex(max(0, index))
        theme = storage.get('readerTheme', 'paper'); index = self.theme.findData(theme); self.theme.setCurrentIndex(max(0, index))
        self.font_family.setCurrentText(str(storage.get('readerCustomFontFamily') or ''))
        self.font_size.setValue(int(storage.get('readerFontSize') or 20))
        self.line_height.setValue(float(storage.get('readerLineHeight') or 1.65))
        self.content_width.setValue(int(storage.get('readerContentWidth') or 860))
        self.margin_top.setValue(int(storage.get('readerMarginTop') or 40)); self.margin_right.setValue(int(storage.get('readerMarginRight') or 60))
        self.margin_bottom.setValue(int(storage.get('readerMarginBottom') or 40)); self.margin_left.setValue(int(storage.get('readerMarginLeft') or 60))
        self.background.setText(str(storage.get('readerBackgroundColor') or '#f8f0dc'))
        self.foreground.setText(str(storage.get('readerTextColor') or '#4a372b'))
        self.link.setText(str(storage.get('readerLinkColor') or '#6c4d2e'))

    def apply(self):
        values = {
            'readerLayoutMode': self.layout_mode.currentData(),
            'readerTheme': self.theme.currentData(),
            'readerCustomFontFamily': self.font_family.currentText().strip(),
            'readerFontSize': self.font_size.value(),
            'readerLineHeight': self.line_height.value(),
            'readerContentWidth': self.content_width.value(),
            'readerMarginTop': self.margin_top.value(),
            'readerMarginRight': self.margin_right.value(),
            'readerMarginBottom': self.margin_bottom.value(),
            'readerMarginLeft': self.margin_left.value(),
            'readerBackgroundColor': self.background.text().strip() or '#ffffff',
            'readerTextColor': self.foreground.text().strip() or '#222222',
            'readerLinkColor': self.link.text().strip() or '#315f9f',
        }
        for key in ('readerBackgroundColor', 'readerTextColor', 'readerLinkColor'):
            if not QColor(values[key]).isValid():
                raise ValueError(_tr('{key} 不是有效颜色', self.state.storage.get('interfaceLanguage')).format(key=key))
        self.state.storage_set(values)
        print(f'[LingKuma calibre {VERSION_STR}] page appearance saved:', values)
        if callable(self.on_applied):
            self.on_applied(dict(values))

    def apply_safe(self):
        try:
            self.apply()
        except Exception as error:
            QMessageBox.critical(self, _tr('无法应用书页设置', self.state.storage.get('interfaceLanguage')), str(error))

    def save_and_close(self):
        try:
            self.apply(); self.accept()
        except Exception as error:
            QMessageBox.critical(self, _tr('无法保存书页设置', self.state.storage.get('interfaceLanguage')), str(error))


class SettingsDialog(QDialog):
    def __init__(self, parent=None, on_saved=None, initial_page=0):
        super().__init__(parent)
        self.state = get_state()
        self.on_saved = on_saved
        self.controls = {}
        self._unavailable_numeric_values = {}
        self._numeric_base_suffixes = {}
        self._opacity_edited = set()
        self._prompt1_edited = False
        self._prompt2_edited = False
        self._analysis_prompt_edited = False
        self._ai_profiles_dirty = False
        self._ai_profiles = None
        self._ai_profiles_readonly = False
        self._tts_preview_page = None
        self._tts_preview_generation = 0
        self._tts_preview_timer = None
        self._edge_preview_request_id = None
        self._gpt_tts_reply = None
        self._gpt_tts_manager = None
        self.word_page = 1
        self.setWindowTitle('LingKuma for calibre 设置')
        self.setMinimumSize(1050, 720)
        self.resize(1180, 800)
        self.setStyleSheet(STYLE)

        outer = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel('LingKuma for calibre')
        title.setObjectName('pageTitle')
        subtitle = QLabel('完整语言学习、阅读器、AI、词库和同步设置')
        subtitle.setObjectName('muted')
        header.addWidget(title)
        header.addSpacing(12)
        header.addWidget(subtitle)
        header.addStretch(1)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.nav = QListWidget()
        self.nav.setFixedWidth(220)
        self.stack = QStackedWidget()
        splitter.addWidget(self.nav)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, 1)

        pages = [
            ('基础设置', self._page_basic),
            ('整句翻译与单词爆炸', self._page_explosion),
            ('查词弹窗', self._page_popup),
            ('AI / API 配置', self._page_ai),
            ('TTS 配置', self._page_tts),
            ('数据库与 WebDAV', self._page_data),
            ('单词列表', self._page_vocabulary),
            ('学习统计', self._page_statistics),
            ('阅读器', self._page_reader),
            ('关于', self._page_about),
        ]
        for label, builder in pages:
            self.nav.addItem(label)
            self.stack.addWidget(self._scroll_page(label, builder))
        self.statistics_page_index = next(index for index, (label, _) in enumerate(pages) if label == '学习统计')
        self.nav.currentRowChanged.connect(self._show_settings_page)
        self.nav.setCurrentRow(max(0, min(initial_page, len(pages) - 1)))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存并应用')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.load_controls()
        self._install_settings_wheel_guards()
        language = self.controls['interfaceLanguage'][1]
        _localize_static_widgets(self, language.currentData())
        if hasattr(self, '_word_page_info_values'):
            self._set_word_page_info(language.currentData())
        self.dictionary_status.setText(self._dictionary_status_text(language.currentData()))
        language.currentIndexChanged.connect(self._preview_ui_language)

    def _install_settings_wheel_guards(self):
        controls = [widget for _, widget in self.controls.values()
                    if isinstance(widget, (QSpinBox, QDoubleSpinBox, QComboBox))]
        controls.extend((self.ai_profile_select, self.ai_profile_fields['apiTemperature'],
                         self.word_filter, self.word_page_size, self.word_import_mode,
                         self.word_import_language, self.word_import_status,
                         self.sentence_keep_count))
        for control in controls:
            targets = [control]
            if control.lineEdit() is not None:
                targets.append(control.lineEdit())
            for target in targets:
                target.setProperty('_lk_settings_wheel_guard', True)
                target.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel and obj.property('_lk_settings_wheel_guard'):
            control = obj if isinstance(obj, (QSpinBox, QDoubleSpinBox, QComboBox)) else obj.parentWidget()
            if isinstance(control, QComboBox) and control.view().isVisible():
                return False
            parent = control.parentWidget() if control is not None else None
            while parent is not None and not isinstance(parent, QScrollArea):
                parent = parent.parentWidget()
            if parent is not None:
                viewport = parent.viewport()
                position = QPointF(obj.mapTo(viewport, event.position().toPoint()))
                forwarded = QWheelEvent(position, event.globalPosition(), event.pixelDelta(),
                                         event.angleDelta(), event.buttons(), event.modifiers(),
                                         event.phase(), event.inverted())
                QApplication.sendEvent(viewport, forwarded)
                return True
        return super().eventFilter(obj, event)

    def _preview_ui_language(self, _index):
        language = self.controls['interfaceLanguage'][1].currentData()
        _localize_static_widgets(self, language)
        self._refresh_legacy_hints(language)
        if hasattr(self, '_word_page_info_values'):
            self._set_word_page_info(language)
        if self.dictionary_status.property('_lk_i18n_dynamic_mode'):
            self.dictionary_status.setText(self._dictionary_status_text(language))
        for index, label in enumerate(('未分级', '陌生', '初识', '学习中', '较熟悉', '已掌握')):
            item = self.stats_status_table.item(index, 0)
            if item:
                item.setText(_tr(f'{index} {label}', language))
        self._update_about_text(language)

    def _refresh_legacy_hints(self, language):
        for key, (kind, widget) in self.controls.items():
            if kind == 'combo':
                index = widget.property('_lk_legacy_item_index')
                if index is not None and 0 <= int(index) < widget.count():
                    value = widget.itemData(int(index))
                    widget.setItemText(int(index), _tr('原有值（当前不可选：{value}）', language).format(value=str(value)[:40]))
            elif key in self._unavailable_numeric_values:
                value = self._unavailable_numeric_values[key]
                widget.setSuffix(_tr(self._numeric_base_suffixes[key], language) +
                                 _tr('（保留旧值 {value}）', language).format(value=value))
                widget.setToolTip(_tr('当前选项范围为 {minimum}–{maximum}。旧值 {value} 将保留；修改此项后使用新值。', language).format(
                    minimum=widget.minimum(), maximum=widget.maximum(), value=value))
        widget = self.ai_profile_fields['apiTemperature']
        if widget.toolTip():
            active = self._ai_profiles.get('activeProfileId')
            profile = next((item for item in self._ai_profiles['profiles'] if item.get('id') == active), None)
            if profile is not None:
                value = profile.get('apiTemperature')
                widget.setSuffix(_tr('（保留旧值 {value}）', language).format(value=value))
                widget.setToolTip(_tr('当前选项范围为 {minimum}–{maximum}。旧值 {value} 将保留；修改此项后使用新值。', language).format(
                    minimum=widget.minimum(), maximum=widget.maximum(), value=value))

    def _scroll_page(self, title, builder):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        heading = QLabel(title)
        heading.setObjectName('pageTitle')
        layout.addWidget(heading)
        builder(layout)
        layout.addStretch(1)
        scroll.setWidget(body)
        return scroll

    def _show_settings_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == self.statistics_page_index:
            self.refresh_statistics()

    def _group(self, layout, title):
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(group)
        return form

    def _bool(self, form, key, label, help_text=''):
        widget = QCheckBox(help_text or '启用')
        self.controls[key] = ('bool', widget)
        form.addRow(label, widget)
        return widget

    def _text(self, form, key, label, password=False, placeholder=''):
        widget = QLineEdit()
        widget.setPlaceholderText(placeholder)
        if password:
            widget.setEchoMode(QLineEdit.EchoMode.Password)
        self.controls[key] = ('text', widget)
        form.addRow(label, widget)
        return widget

    def _shortcut(self, form, key, label):
        widget = self._text(form, key, label, placeholder='一个字符，或输入 Tab / Space 等按键名')
        widget.setMaxLength(16)
        self.controls[key] = ('shortcut', widget)
        return widget

    def _multiline(self, form, key, label, placeholder=''):
        widget = QPlainTextEdit()
        widget.setPlaceholderText(placeholder)
        widget.setMinimumHeight(100)
        self.controls[key] = ('multiline', widget)
        if key == 'aiTranslationPrompt':
            widget.textChanged.connect(lambda: setattr(self, '_prompt1_edited', True))
        if key == 'aiTranslationPrompt2':
            widget.textChanged.connect(lambda: setattr(self, '_prompt2_edited', True))
        if key == 'aiSentenceAnalysisPrompt':
            widget.textChanged.connect(lambda: setattr(self, '_analysis_prompt_edited', True))
        form.addRow(label, widget)
        return widget

    def _combo(self, form, key, label, options):
        widget = QComboBox()
        for text, value in options:
            widget.addItem(text, value)
        self.controls[key] = ('combo', widget)
        form.addRow(label, widget)
        return widget

    def _editable_combo(self, form, key, label, options):
        widget = self._combo(form, key, label, options)
        widget.setEditable(True)
        widget.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        widget.setProperty('_lk_i18n_preserve_edit', True)
        self.controls[key] = ('editable_combo', widget)
        return widget

    def _int(self, form, key, label, low, high, suffix=''):
        widget = QSpinBox()
        widget.setRange(low, high)
        suffix = _tr(suffix)
        widget.setSuffix(suffix)
        self.controls[key] = ('int', widget)
        self._numeric_base_suffixes[key] = suffix
        widget.valueChanged.connect(lambda _value, saved_key=key, control=widget: self._numeric_value_edited(saved_key, control))
        widget.lineEdit().textEdited.connect(lambda _text, saved_key=key, control=widget: self._numeric_value_edited(saved_key, control))
        form.addRow(label, widget)
        return widget

    def _float(self, form, key, label, low, high, step=.1):
        widget = QDoubleSpinBox()
        widget.setRange(low, high)
        widget.setSingleStep(step)
        widget.setDecimals(2)
        self.controls[key] = ('float', widget)
        self._numeric_base_suffixes[key] = widget.suffix()
        widget.valueChanged.connect(lambda _value, saved_key=key, control=widget: self._numeric_value_edited(saved_key, control))
        widget.lineEdit().textEdited.connect(lambda _text, saved_key=key, control=widget: self._numeric_value_edited(saved_key, control))
        form.addRow(label, widget)
        return widget

    def _opacity(self, form, key, label):
        widget = self._int(form, key, label, 0, 100, ' %')
        color_widget = self.controls[_OPACITY_COLORS[key]][1]

        def changed(value):
            self._opacity_edited.add(key)
            color = color_widget.text()
            if re.fullmatch(r'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', color):
                alpha = int(value * 2.55 + .5)
                color_widget.setText(color[:7] + f'{alpha:02X}')

        def color_edited(text):
            percent = _color_opacity(text)
            if percent is not None:
                widget.blockSignals(True)
                widget.setValue(percent)
                widget.blockSignals(False)
                self._opacity_edited.discard(key)

        widget.valueChanged.connect(changed)
        color_widget.textEdited.connect(color_edited)
        return widget

    def _numeric_value_edited(self, key, widget):
        if key in self._unavailable_numeric_values:
            self._unavailable_numeric_values.pop(key)
            widget.setSuffix(self._numeric_base_suffixes[key])
            widget.setToolTip('')

    def _page_basic(self, layout):
        form = self._group(layout, '基础设置')
        self._combo(form, 'interfaceLanguage', '界面语言', [
            ('自动（跟随 Calibre）', 'auto'), ('中文', 'zh'), ('繁體中文', 'zh_TW'),
            ('English', 'en'), ('Deutsch', 'de'), ('Français', 'fr'),
            ('Español', 'es'), ('日本語', 'ja'), ('한국어', 'ko'),
            ('Русский', 'ru'), ('Italiano', 'it'),
        ])
        self._bool(form, 'enablePlugin', '单词高亮（总开关）', 'LingKuma 原版总开关：关闭后高亮、查词和整句翻译都会停止')
        self._bool(form, 'wordHighlightFloatingButtonEnabled', 'Kuma 小按钮', '在阅读页面显示开关和明暗按钮')
        self._combo(form, 'wordHighlightFloatingButtonScope', '小按钮控制范围', [('所有阅读器', 'global'), ('当前阅读器', 'page')])
        self._bool(form, 'highlightAlphabeticEnabled', '英文高亮')
        self._bool(form, 'highlightChineseEnabled', '中文高亮')
        self._bool(form, 'highlightJapaneseEnabled', '日语高亮')
        self._bool(form, 'highlightKoreanEnabled', '韩语高亮')
        self._bool(form, 'autoDetectJapaneseKanji', '自动识别日语汉字')
        self._bool(form, 'useKuromojiTokenizer', '日语 Kuromoji 分词（实验）')
        self._bool(form, 'autoLoadKuromojiForJapanese', '日语页面自动加载 Kuromoji')
        self._editable_combo(form, 'translationConfig.targetLanguage', '目标语言', [
            ('简体中文', 'zh-CN'), ('繁体中文', 'zh-TW'), ('英语', 'en'),
            ('德语', 'de'), ('法语', 'fr'), ('西班牙语', 'es'),
            ('日语', 'ja'), ('韩语', 'ko'), ('俄语', 'ru'), ('意大利语', 'it'),
        ])
        bionic = self._group(layout, 'Bionic Reading（长文可能影响性能）')
        self._bool(bionic, 'bionicEnabled', '启用 Bionic Reading（默认关闭）')
        self._combo(bionic, 'bionicFontFamily', '字体', [
            ('自动', 'auto'), ('LXGW WenKai', "'LXGWWenKai', serif"),
            ('Fanwood', "'Fanwood', serif"), ('Arial', 'Arial, sans-serif'),
            ('Times New Roman', "'Times New Roman', serif"),
            ('Courier New', "'Courier New', monospace"), ('Georgia', 'Georgia, serif'),
            ('Verdana', 'Verdana, sans-serif'), ('Trebuchet MS', "'Trebuchet MS', sans-serif"),
            ('Segoe UI', "'Segoe UI', sans-serif"), ('Open Sans', "'Open Sans', sans-serif"),
            ('Roboto', 'Roboto, sans-serif'),
            ('Helvetica Neue', "'Helvetica Neue', Helvetica, sans-serif"),
        ])
        self._int(bionic, 'bionicFontSize', '字号', 8, 64, ' px')
        ruler = self._group(layout, 'Reading Ruler（阅读标尺）')
        self._bool(ruler, 'readingRuler', '启用 Reading Ruler（默认关闭）')
        self._bool(ruler, 'rulerSettings.isInverted', '反色遮罩')
        self._combo(ruler, 'rulerSettings.widthMode', '宽度模式', [
            ('自动', 'auto'), ('全屏', 'screen'), ('自定义', 'custom'),
        ])
        self._int(ruler, 'rulerSettings.customWidth', '自定义宽度', 50, 2400, ' px')
        self._int(ruler, 'rulerSettings.height', '标尺高度', 10, 100, ' px')
        self._float(ruler, 'rulerSettings.opacity', '透明度', 0, 1, .05)
        self._text(ruler, 'rulerSettings.color', '颜色', placeholder='#6f6f6f')
        pos = self._group(layout, 'POS Highlight（词性高亮）')
        self._bool(pos, 'posHighlightEnabled', '启用 POS Highlight（默认关闭）')
        self._combo(pos, 'posHighlightLanguage', '语言', [
            ('英语', 'english'), ('德语', 'german'), ('自动', 'auto'),
        ])
        self._bool(pos, 'posHighlightVerbEnabled', '高亮动词')
        self._bool(pos, 'posHighlightVerbBackgroundEnabled', '动词背景色')
        self._text(pos, 'posHighlightVerbBackgroundColor', '动词背景颜色', placeholder='#FF6B6B40')
        self._opacity(pos, 'posHighlightVerbBackgroundOpacity', '动词背景透明度')
        self._bool(pos, 'posHighlightVerbUnderlineEnabled', '动词下划线')
        self._combo(pos, 'posHighlightVerbUnderlineStyle', '动词下划线样式', [
            ('波浪线', 'wavy'), ('实线', 'solid'), ('点线', 'dotted'), ('虚线', 'dashed'),
        ])
        self._text(pos, 'posHighlightVerbUnderlineColor', '动词下划线颜色', placeholder='#FF6B6B')
        self._int(pos, 'posHighlightVerbUnderlineThickness', '动词下划线粗细', 1, 6, ' px')
        self._combo(pos, 'posHighlightVerbUnderlinePosition', '动词下划线位置', [
            ('底部', 'bottom'), ('顶部', 'top'),
        ])
        self._bool(pos, 'posHighlightPrepositionEnabled', '高亮介词')
        self._bool(pos, 'posHighlightPrepositionBackgroundEnabled', '介词背景色')
        self._text(pos, 'posHighlightPrepositionBackgroundColor', '介词背景颜色', placeholder='#f2935440')
        self._opacity(pos, 'posHighlightPrepositionBackgroundOpacity', '介词背景透明度')
        self._bool(pos, 'posHighlightPrepositionUnderlineEnabled', '介词下划线')
        self._combo(pos, 'posHighlightPrepositionUnderlineStyle', '介词下划线样式', [
            ('波浪线', 'wavy'), ('实线', 'solid'), ('点线', 'dotted'), ('虚线', 'dashed'),
        ])
        self._text(pos, 'posHighlightPrepositionUnderlineColor', '介词下划线颜色', placeholder='#f29354')
        self._int(pos, 'posHighlightPrepositionUnderlineThickness', '介词下划线粗细', 1, 6, ' px')
        self._combo(pos, 'posHighlightPrepositionUnderlinePosition', '介词下划线位置', [
            ('底部', 'bottom'), ('顶部', 'top'),
        ])
        ai = self._group(layout, '自动语言学习')
        self._bool(ai, 'autoRequestAITranslations', '自动生成第一条中文释义')
        self._bool(ai, 'autoRequestAITranslations2', '自动生成第二条中文释义')
        self._bool(ai, 'autoAddAITranslations', '自动保存 AI 释义')
        self._bool(ai, 'autoAddAITranslationsFromUnknown', '为新词保存 AI 释义')
        self._bool(ai, 'autoAddExampleSentences', '自动保存例句')
        self._int(ai, 'autoAddSentencesLimit', '每词自动保存例句上限', 0, 20)

    def _page_explosion(self, layout):
        form = self._group(layout, '整句翻译与单词爆炸')
        self._bool(form, 'wordExplosionEnabled', '启用整句翻译面板')
        self._combo(form, 'wordExplosionTriggerMode', '触发方式', [('点击单词', 'click'), ('悬停', 'hover')])
        self._combo(form, 'wordExplosionPositionMode', '面板位置', [('自动', 'auto'), ('手动拖动', 'manual')])
        self._combo(form, 'wordExplosionLayout', '面板排列', [('纵向', 'vertical'), ('横向', 'horizontal')])
        self._combo(form, 'wordExplosionWordsLayout', '单词排列', [('一列', 'single-column'), ('两列', 'double-column'), ('三列', 'triple-column')])
        self._combo(form, 'wordExplosionTranslationCount', '每个词显示释义', [('全部', 'all'), ('1 条', '1'), ('2 条', '2'), ('3 条', '3')])
        self._int(form, 'explosionSentenceTranslationCount', '整句译文数量', 1, 2)
        self._int(form, 'wordExplosionFontSize', '字号', 10, 32, ' px')
        self._int(form, 'wordExplosionMaxWidth', '最大宽度', 320, 1600, ' px')
        self._bool(form, 'wordExplosionPreferUp', '优先显示在上方')
        self._bool(form, 'wordExplosionHighlightSentence', '高亮原句')
        self._bool(form, 'showExplosionSentence', '在面板中显示英文原句')
        self._bool(form, 'explosionPriorityMode', '单词爆炸优先模式')
        self._bool(form, 'explosionHighlightWithTTS', '朗读时逐词高亮')
        self._bool(form, 'explosionHighlightNoTTS', '静音时逐词高亮')
        self._bool(form, 'explosionTTSOnly', '只朗读，不逐词高亮')
        self._int(form, 'explosionHighlightSpeed', '逐词高亮速度', 10, 500, ' ms').setSingleStep(10)
        self._bool(form, 'showKnownSentenceAnimation', '显示熟句动画')
        line = self._group(layout, '句子标记')
        self._text(line, 'wordExplosionHighlightColor', '句子高亮颜色', placeholder='#955FBD40')
        self._opacity(line, 'wordExplosionHighlightOpacity', '句子高亮透明度')
        self._bool(line, 'wordExplosionUnderlineEnabled', '显示下划线')
        self._combo(line, 'wordExplosionUnderlineStyle', '下划线样式', [('实线', 'solid'), ('波浪线', 'wavy'), ('点线', 'dotted')])
        self._combo(line, 'wordExplosionUnderlinePosition', '下划线位置', [('下方', 'bottom'), ('上方', 'top'), ('上下都有', 'both')])
        self._text(line, 'wordExplosionUnderlineColor', '下划线颜色', placeholder='#955FBD80')
        self._opacity(line, 'wordExplosionUnderlineOpacity', '下划线透明度')
        self._int(line, 'wordExplosionUnderlineThickness', '下划线粗细', 1, 12, ' px')

    def _page_popup(self, layout):
        form = self._group(layout, '查词弹窗行为')
        self._bool(form, 'clickOnlyTooltip', '只在点击时显示')
        self._bool(form, 'autoExpandTooltip', '自动展开完整弹窗')
        self._bool(form, 'autoCloseTooltip', '点击其他位置自动关闭')
        self._bool(form, 'autoRefreshTooltip', '再次点击时刷新')
        self._bool(form, 'defaultExpandTooltip', '默认显示详细内容')
        self._bool(form, 'defaultExpandSententsTooltip', '默认展开句子区域')
        self._bool(form, 'defaultExpandCapsule', '默认展开释义胶囊')
        self._bool(form, 'preferPopupAbove', '优先在单词上方显示')
        self._bool(form, 'selectionPopupPreferDown', '选词弹窗优先显示在下方')
        self._int(form, 'tooltipGap', '单词与弹窗间距', 0, 200, ' px')
        self._int(form, 'selectionPopupGap', '选词弹窗间距', 0, 200, ' px')
        visual = self._group(layout, '外观')
        self._combo(visual, 'tooltipThemeMode', '主题', [('自动', 'auto'), ('浅色', 'light'), ('深色', 'dark')])
        self._bool(visual, 'tooltipBackground.enabled', '图案背景')
        self._combo(visual, 'tooltipBackground.defaultType', '内置背景类型', [('随机 SVG 图案', 'svg')])
        self._bool(visual, 'liquidGlassEnabled', '液态玻璃效果')
        self._bool(visual, 'analysisGlassEnabled', '分析面板玻璃效果')
        self._float(visual, 'devicePixelRatio', '设备像素缩放', .5, 4, .1)
        self._combo(visual, 'glassEffectType', '玻璃类型', [('关闭', 'none'), ('轻度', 'light'), ('完整', 'full')])
        capsules = self._group(layout, '自定义胶囊')
        self._multiline(capsules, 'customCapsules', 'JSON', '[{"label":"例子","prompt":"……"}]')
        restore = QPushButton('恢复被缩小的弹窗')
        restore.clicked.connect(self._restore_popup)
        layout.addWidget(restore)
        shortcuts = self._group(layout, '阅读快捷键')
        for key, label in (
            ('wordQueryKey', '查词'), ('copySentenceKey', '复制句子'),
            ('analysisWindowKey', '分析窗口'), ('sentenceExplosionKey', '句子爆炸'),
            *((f'wordStatusKeys.{status}', f'词汇状态 {status}') for status in range(6)),
            ('wordStatusKeys.toggle', '切换词汇状态'),
            ('wordStatusKeys.addAITranslation', '添加 AI 释义'),
            ('wordStatusKeys.closeTooltip', '关闭弹窗'),
        ):
            self._shortcut(shortcuts, key, label)

    def _page_ai(self, layout):
        note = QLabel('普通单词译文和整句翻译优先使用专用翻译引擎；第二条语境解释、词性标签和自由分析仍由 AI 完成。')
        note.setWordWrap(True); note.setObjectName('muted'); layout.addWidget(note)
        translator = self._group(layout, '快速翻译引擎')
        self._combo(translator, 'translationConfig.provider', '翻译服务', [
            ('Google Web Translate（免 Key，实验性）', 'google-web'),
            ('Microsoft Translator（需自己的 Key）', 'microsoft'),
            ('Google Cloud Translation（需自己的 Key）', 'google-cloud'),
            ('LingKuma AI（最完整但较慢）', 'lingkuma-ai'),
        ])
        self._bool(translator, 'translationConfig.fallbackToAI', '翻译服务失败时回退到 LingKuma AI')
        self._int(translator, 'translationConfig.timeoutSeconds', '翻译超时', 3, 60, ' 秒')
        self._text(translator, 'translationConfig.microsoftKey', 'Microsoft Key', password=True)
        self._text(translator, 'translationConfig.microsoftRegion', 'Microsoft Region')
        self._text(translator, 'translationConfig.microsoftEndpoint', 'Microsoft Endpoint')
        self._text(translator, 'translationConfig.googleCloudApiKey', 'Google Cloud API Key', password=True)
        warning = QLabel('Google Web Translate 不需要 Key，速度通常快于生成式 AI，但它不是面向第三方插件承诺稳定性的正式接口；若失效，可切换到 Microsoft/Google Cloud 官方接口或启用 AI 回退。')
        warning.setWordWrap(True); warning.setObjectName('muted'); layout.addWidget(warning)

        fast = self._group(layout, 'Calibre 请求调度')
        self._bool(fast, 'calibreFastAIEnabled', '启用快速调度（推荐）')
        self._bool(fast, 'calibreBatchWordTranslations', '整句生词合并翻译')
        self._int(fast, 'calibreBatchMaxWords', '每批最多单词数', 5, 60)
        self._int(fast, 'calibreAIConcurrency', '同时进行的详细 AI 请求', 1, 8)
        profiles = self._group(layout, 'AI 配置档')
        self.ai_profile_warning = QLabel('配置档数据超出当前编辑范围或不完整；原始数据已保留，当前窗口不会改写配置档。')
        self.ai_profile_warning.setWordWrap(True)
        self.ai_profile_warning.setObjectName('muted')
        self.ai_profile_warning.hide()
        profiles.addRow(self.ai_profile_warning)
        self.ai_profile_select = QComboBox()
        self.ai_profile_select.setProperty('_lk_i18n_preserve_items', True)
        profiles.addRow('当前配置档', self.ai_profile_select)
        self._bool(profiles, 'aiConfig.enableApiPolling', '轮询已启用的配置档')
        action_row = QWidget()
        action_layout = QHBoxLayout(action_row)
        action_layout.setContentsMargins(0, 0, 0, 0)
        self.ai_profile_buttons = {}
        for key, label, handler in [
            ('add', '新增配置档', lambda: self._add_ai_profile(False)),
            ('copy', '复制配置档', lambda: self._add_ai_profile(True)),
            ('delete', '删除配置档', self._delete_ai_profile),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            action_layout.addWidget(button)
            self.ai_profile_buttons[key] = button
        profiles.addRow(action_row)
        self.ai_profile_fields = {}
        for key, label in [('name', '配置档名称'), ('apiBaseURL', '配置档 API 地址'),
                           ('apiModel', '配置档模型'), ('apiKey', '配置档 API Key')]:
            widget = QLineEdit()
            if key == 'apiKey':
                widget.setEchoMode(QLineEdit.EchoMode.Password)
            widget.textChanged.connect(lambda _text, field=key: self._ai_profile_field_changed(field))
            self.ai_profile_fields[key] = widget
            profiles.addRow(label, widget)
        temperature = QDoubleSpinBox()
        temperature.setRange(0, 2)
        temperature.setSingleStep(.1)
        temperature.setDecimals(2)
        temperature.valueChanged.connect(lambda _value: self._ai_profile_field_changed('apiTemperature'))
        temperature.lineEdit().textEdited.connect(lambda _text: self._ai_profile_field_changed('apiTemperature'))
        self.ai_profile_fields['apiTemperature'] = temperature
        profiles.addRow('配置档 Temperature', temperature)
        for key, label in [('enablePolling', '加入轮询'), ('excludeTemperature', '不发送 Temperature')]:
            widget = QCheckBox()
            widget.toggled.connect(lambda _value, field=key: self._ai_profile_field_changed(field))
            self.ai_profile_fields[key] = widget
            profiles.addRow(label, widget)
        custom_body = QPlainTextEdit()
        custom_body.setMinimumHeight(75)
        custom_body.setPlaceholderText('每行 key=JSON')
        custom_body.textChanged.connect(lambda: self._ai_profile_field_changed('customRequestBody'))
        self.ai_profile_fields['customRequestBody'] = custom_body
        profiles.addRow('自定义请求参数', custom_body)
        self.ai_profile_select.currentIndexChanged.connect(self._select_ai_profile)
        fallback_note = QLabel('当前配置档填写 API 地址后优先使用该配置档；留空时使用下方原有接口设置，仍为空则使用 LingKuma 默认服务。')
        fallback_note.setWordWrap(True)
        fallback_note.setObjectName('muted')
        layout.addWidget(fallback_note)
        form = self._group(layout, '原有单接口回退设置')
        self._text(form, 'aiConfig.apiBaseURL', 'API 地址', placeholder='留空使用 LingKuma 默认服务')
        self._text(form, 'aiConfig.apiModel', '模型')
        self._text(form, 'aiConfig.apiKey', 'API Key', password=True)
        self._float(form, 'aiConfig.apiTemperature', 'Temperature', 0, 2, .1)
        prompts = self._group(layout, '可选提示词覆盖')
        self._multiline(prompts, 'aiTranslationPrompt', '第一条中文释义提示词', '留空使用 LingKuma 原始提示词')
        self._multiline(prompts, 'aiTranslationPrompt2', '第二条中文释义提示词', '留空使用 LingKuma 原始提示词')
        self._multiline(prompts, 'aiTagAnalysisPrompt', '词性与标签提示词', '留空使用 LingKuma 原始提示词')
        self._multiline(prompts, 'aiSentenceTranslationPrompt', '整句翻译提示词', '留空使用 LingKuma 原始提示词')
        self._multiline(prompts, 'aiSentenceAnalysisPrompt', '句子分析提示词', '留空使用 LingKuma 原始提示词')
        advanced_prompts = self._group(layout, '高级提示词')
        self._multiline(advanced_prompts, 'aiConfig.aiLanguageDetectionPrompt', '语言检测提示词', '留空使用 LingKuma 原始提示词')

    def _page_tts(self, layout):
        form = self._group(layout, '朗读总设置')
        self._bool(form, 'enableWordTTS', '单词朗读')
        self._bool(form, 'enableAutoWordTTS', '自动朗读单词')
        self._bool(form, 'enableSentenceTTS', '句子朗读')
        self._bool(form, 'sentenceTTSAutoDetectLanguage', '句子朗读自动识别语言')
        providers = [('系统本地语音', 'local'), ('Edge TTS', 'edge'), ('GPT TTS', 'gpt'), ('自定义 URL 1', 'custom'), ('自定义 URL 2', 'custom2')]
        self._combo(form, 'wordTTSProvider', '单词语音渠道', providers)
        self._combo(form, 'sentenceTTSProvider', '句子语音渠道', providers)
        selected_preview = QPushButton('测试当前单词语音')
        selected_preview.clicked.connect(self.test_selected_word_tts)
        form.addRow(selected_preview)
        stop_preview = QPushButton('停止试听')
        stop_preview.clicked.connect(self.stop_tts_preview)
        form.addRow(stop_preview)
        local = self._group(layout, '系统本地语音')
        self._text(local, 'localTTSVoice', '语音名称', placeholder='留空自动选择')
        self._float(local, 'localTTSRate', '速度', .2, 3, .1)
        self._float(local, 'localTTSPitch', '音调', 0, 2, .1)
        preview = QPushButton(_tr('测试本地语音'))
        preview.clicked.connect(self.test_local_tts)
        local.addRow(preview)
        edge = self._group(layout, 'Edge TTS')
        self._bool(edge, 'edgeTTSAutoVoice', '自动选择语音')
        self._text(edge, 'edgeTTSVoice', '语音')
        self._float(edge, 'edgeTTSRate', '速度', -100, 100, 5)
        self._float(edge, 'edgeTTSVolume', '音量', -100, 100, 5)
        self._float(edge, 'edgeTTSPitch', '音调', -100, 100, 5)
        edge_preview = QPushButton(_tr('测试 Edge TTS'))
        edge_preview.clicked.connect(self._start_edge_tts_preview)
        edge.addRow(edge_preview)
        gpt = self._group(layout, 'GPT TTS')
        self._text(gpt, 'gptTTSBaseURL', 'API 地址')
        self._text(gpt, 'gptTTSApiKey', 'API Key', password=True)
        self._text(gpt, 'gptTTSModel', '模型')
        self._text(gpt, 'gptTTSVoice', '声音')
        self._float(gpt, 'gptTTSSpeed', '速度', .25, 4, .1)
        self._combo(gpt, 'gptTTSResponseFormat', '音频格式', [('MP3', 'mp3'), ('WAV', 'wav'), ('OPUS', 'opus'), ('AAC', 'aac'), ('FLAC', 'flac')])
        self._multiline(gpt, 'gptTTSInstructions', '朗读指令', '例如：Speak clearly and naturally.')
        gpt_preview = QPushButton(_tr('测试 GPT TTS'))
        gpt_preview.clicked.connect(self._start_gpt_tts_preview)
        gpt.addRow(gpt_preview)
        custom = self._group(layout, '自定义单词音频')
        self._text(custom, 'wordAudioUrlTemplate', 'URL 模板 1', placeholder='使用 {word}、{lang}')
        self._text(custom, 'wordAudioUrlTemplate2', 'URL 模板 2', placeholder='使用 {word}、{lang}')
        self._multiline(custom, 'audioUrlNotebook', '模板说明 / 备注')

    def _page_data(self, layout):
        dictionary = self._group(layout, '词典')
        use_default = QPushButton('使用默认词典')
        self.dictionary_default_button = use_default
        self.dictionary_status = QLabel()
        self.dictionary_status.setProperty('_lk_i18n_dynamic_mode', True)
        self.dictionary_status.setText(self._dictionary_status_text())
        dictionary.addRow(use_default, self.dictionary_status)
        use_default.clicked.connect(self.select_default_dictionary)
        use_custom = QPushButton('使用自定义词典')
        self.dictionary_custom_button = use_custom
        dictionary.addRow(use_custom)
        use_custom.clicked.connect(self.select_custom_dictionary)
        self.dictionary_import_button = QPushButton('导入自定义词典')
        dictionary.addRow(self.dictionary_import_button)
        self.dictionary_import_button.clicked.connect(self.import_custom_dictionary)
        self.dictionary_refresh_button = QPushButton('刷新词典状态')
        dictionary.addRow(self.dictionary_refresh_button)
        self.dictionary_refresh_button.clicked.connect(self.refresh_dictionary_status)
        local = self._group(layout, '本地数据库')
        backup = QPushButton('导出完整备份')
        restore_merge = QPushButton('导入并合并')
        restore_replace = QPushButton('导入并替换')
        clear_words = QPushButton('清空词库')
        row = QWidget(); row_l = QHBoxLayout(row); row_l.setContentsMargins(0, 0, 0, 0)
        for button in (backup, restore_merge, restore_replace, clear_words): row_l.addWidget(button)
        local.addRow(row)
        backup.clicked.connect(self.export_backup)
        restore_merge.clicked.connect(lambda: self.import_backup(True))
        restore_replace.clicked.connect(lambda: self.import_backup(False))
        clear_words.clicked.connect(self.clear_vocabulary)
        webdav = self._group(layout, 'WebDAV 多设备同步')
        self._text(webdav, 'webdavConfig.url', 'WebDAV 地址', placeholder='https://dav.example.com/folder/')
        self._text(webdav, 'webdavConfig.username', '用户名')
        self._text(webdav, 'webdavConfig.password', '密码', password=True)
        self._text(webdav, 'webdavConfig.filename', '备份文件名')
        buttons = QWidget(); bl = QHBoxLayout(buttons); bl.setContentsMargins(0, 0, 0, 0)
        for text, handler in [('测试连接', self.webdav_test), ('上传当前数据', self.webdav_upload), ('下载并合并', lambda: self.webdav_download(True)), ('下载并替换', lambda: self.webdav_download(False))]:
            button = QPushButton(text); button.clicked.connect(handler); bl.addWidget(button)
        webdav.addRow(buttons)
        epub = self._group(layout, 'EPUB 文本修复')
        self._bool(epub, 'epubSoftHyphenCleanup', '移除软连字符')
        self._bool(epub, 'epubHyphenRepair', '修复换行断词')

    def _page_vocabulary(self, layout):
        bar = QHBoxLayout()
        self.word_search = QLineEdit(); self.word_search.setPlaceholderText('搜索单词、释义或标签')
        self.word_filter = QComboBox(); self.word_filter.addItem('全部状态', 'all')
        for index, label in enumerate(('未分级', '陌生', '初识', '学习中', '较熟悉', '已掌握')):
            self.word_filter.addItem(f'{index} {label}', str(index))
        refresh = QPushButton('刷新')
        bar.addWidget(self.word_search, 1); bar.addWidget(self.word_filter); bar.addWidget(refresh)
        layout.addLayout(bar)
        pages = QHBoxLayout()
        pages.addWidget(QLabel('每页'))
        self.word_page_size = QComboBox()
        for size in (20, 50, 100):
            self.word_page_size.addItem(str(size), size)
        pages.addWidget(self.word_page_size)
        self.word_prev = QPushButton('上一页')
        self.word_next = QPushButton('下一页')
        self.word_page_info = QLabel()
        pages.addWidget(self.word_prev)
        pages.addWidget(self.word_next)
        pages.addWidget(self.word_page_info)
        pages.addStretch(1)
        layout.addLayout(pages)
        self.word_table = QTableWidget(0, 5)
        self.word_table.setHorizontalHeaderLabels(['单词', '状态', '中文释义', '标签', '例句数'])
        self.word_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.word_table.setAlternatingRowColors(True)
        self.word_table.setMinimumHeight(430)
        self.word_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.word_table)
        actions = QHBoxLayout()
        save = QPushButton('保存表格修改'); delete = QPushButton('删除所选词'); import_words = QPushButton('导入已知单词'); export_words = QPushButton('导出学习数据')
        self.adopt_meaning_button = QPushButton('采用释义')
        self.edit_meaning_button = QPushButton('修改释义')
        self.delete_meaning_button = QPushButton('删除释义')
        self.adopt_meaning_button.setEnabled(False)
        self.edit_meaning_button.setEnabled(False)
        self.delete_meaning_button.setEnabled(False)
        actions.addWidget(save); actions.addWidget(self.adopt_meaning_button); actions.addWidget(self.edit_meaning_button); actions.addWidget(self.delete_meaning_button); actions.addWidget(delete); actions.addWidget(import_words); actions.addWidget(export_words); actions.addStretch(1)
        layout.addLayout(actions)
        import_group = self._group(layout, '导入词汇')
        self.word_import_text = QPlainTextEdit()
        self.word_import_text.setPlaceholderText('粘贴 LingKuma JSON，或每行输入一个单词')
        self.word_import_text.setMinimumHeight(95)
        import_group.addRow(self.word_import_text)
        self.word_import_mode = QComboBox()
        self.word_import_mode.addItem('合并', 'merge')
        self.word_import_mode.addItem('替换全部词库', 'replace')
        import_group.addRow('导入方式', self.word_import_mode)
        self.word_import_language = QComboBox()
        for code, name in (('en', 'English'), ('de', 'Deutsch'), ('fr', 'Français'),
                           ('es', 'Español'), ('it', 'Italiano'), ('ja', '日本語'),
                           ('ko', '한국어'), ('ru', 'Русский'), ('custom', '自定义')):
            self.word_import_language.addItem(name, code)
        import_group.addRow('纯词表语言', self.word_import_language)
        self.word_import_custom_language = QLineEdit()
        self.word_import_custom_language.setPlaceholderText('两个字母，例如 nl')
        self.word_import_custom_language.setMaxLength(2)
        import_group.addRow('自定义语言代码', self.word_import_custom_language)
        self.word_import_status = QComboBox()
        for value, label in (('5', '完全掌握'), ('4', '几乎掌握'), ('3', '较熟悉'),
                             ('2', '继续学习'), ('1', '学习中'), ('0', '未知')):
            self.word_import_status.addItem(f'{value} {label}', value)
        import_group.addRow('纯词表状态', self.word_import_status)
        import_actions = QWidget(); import_buttons = QHBoxLayout(import_actions)
        choose_file = QPushButton('选择文件'); clear_input = QPushButton('清空输入')
        import_buttons.addWidget(choose_file); import_buttons.addWidget(clear_input)
        import_group.addRow(import_actions)
        self.word_search.textChanged.connect(self._reset_vocabulary_page)
        self.word_filter.currentIndexChanged.connect(self._reset_vocabulary_page)
        self.word_page_size.currentIndexChanged.connect(self._reset_vocabulary_page)
        self.word_prev.clicked.connect(lambda: self._change_vocabulary_page(-1))
        self.word_next.clicked.connect(lambda: self._change_vocabulary_page(1))
        refresh.clicked.connect(self.refresh_vocabulary)
        save.clicked.connect(self.save_vocabulary_table)
        self.adopt_meaning_button.clicked.connect(self.adopt_selected_meaning)
        self.edit_meaning_button.clicked.connect(self.edit_selected_meaning)
        self.delete_meaning_button.clicked.connect(self.delete_selected_meaning)
        self.word_table.itemSelectionChanged.connect(self._update_adopt_meaning_enabled)
        self.word_table.itemChanged.connect(self._update_adopt_meaning_enabled)
        delete.clicked.connect(self.delete_selected_words)
        import_words.clicked.connect(self.import_words)
        export_words.clicked.connect(self.export_learning_data)
        choose_file.clicked.connect(self.choose_word_import_file)
        clear_input.clicked.connect(self.word_import_text.clear)
        self.refresh_vocabulary()

    def _page_statistics(self, layout):
        refresh = QPushButton('刷新')
        refresh.clicked.connect(self.refresh_statistics)
        layout.addWidget(refresh)
        status_group = self._group(layout, '按词汇状态')
        self.stats_status_table = QTableWidget(6, 2)
        self.stats_status_table.setHorizontalHeaderLabels(['状态', '单词数'])
        self.stats_status_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_status_table.setMinimumHeight(265)
        status_group.addRow(self.stats_status_table)
        language_group = self._group(layout, '按语言')
        self.stats_language_table = QTableWidget(0, 2)
        self.stats_language_table.setHorizontalHeaderLabels(['语言', '单词数'])
        self.stats_language_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_language_table.setMinimumHeight(160)
        language_group.addRow(self.stats_language_table)
        self.stats_empty_label = QLabel('词库为空。')
        language_group.addRow(self.stats_empty_label)
        cleanup = self._group(layout, '例句清理')
        self.sentence_keep_count = QSpinBox()
        self.sentence_keep_count.setRange(0, 20)
        self.sentence_keep_count.setValue(3)
        cleanup.addRow('每个词最多保留的例句数量', self.sentence_keep_count)
        trim = QPushButton('清理多余例句')
        trim.clicked.connect(self.trim_sentences)
        cleanup.addRow(trim)
        self.refresh_statistics()

    def refresh_statistics(self):
        words = self.state.get_all_words()
        status_counts = [0] * 6
        language_counts = {}
        for record in words.values():
            status_counts[int(normalize_status(record.get('status')))] += 1
            language = str(record.get('language') or 'auto')
            language_counts[language] = language_counts.get(language, 0) + 1
        for index, count in enumerate(status_counts):
            label = ('未分级', '陌生', '初识', '学习中', '较熟悉', '已掌握')[index]
            self.stats_status_table.setItem(index, 0, QTableWidgetItem(f'{index} {_tr(label)}'))
            self.stats_status_table.setItem(index, 1, QTableWidgetItem(str(count)))
        languages = sorted(language_counts.items(), key=lambda item: (-item[1], item[0]))
        self.stats_language_table.setRowCount(len(languages))
        self.stats_empty_label.setVisible(not languages)
        for index, (language, count) in enumerate(languages):
            self.stats_language_table.setItem(index, 0, QTableWidgetItem(language))
            self.stats_language_table.setItem(index, 1, QTableWidgetItem(str(count)))

    def _page_reader(self, layout):
        form = self._group(layout, 'LingKuma 阅读器')
        self._combo(form, 'readerLayoutMode', '页面排版', [
            ('跟随 Calibre 阅读器', 'calibre'),
            ('保留 EPUB 原书排版', 'original'),
            ('自定义书页', 'custom'),
        ])
        self._combo(form, 'readerTheme', '自定义阅读主题', [('羊皮纸', 'paper'), ('白色', 'light'), ('深色', 'dark'), ('自定义颜色', 'custom')])
        self._text(form, 'readerCustomFontFamily', '自定义字体名称', placeholder='例如 Georgia / Microsoft YaHei')
        self._int(form, 'readerFontSize', '正文字号', 8, 72, ' px')
        self._float(form, 'readerLineHeight', '行距', .8, 4, .05)
        self._int(form, 'readerContentWidth', '正文宽度', 400, 2200, ' px')
        margins = self._group(layout, '自定义页边距与颜色')
        self._int(margins, 'readerMarginTop', '上边距', 0, 300, ' px')
        self._int(margins, 'readerMarginRight', '右边距', 0, 300, ' px')
        self._int(margins, 'readerMarginBottom', '下边距', 0, 300, ' px')
        self._int(margins, 'readerMarginLeft', '左边距', 0, 300, ' px')
        self._text(margins, 'readerBackgroundColor', '页面背景色', placeholder='#f8f0dc')
        self._text(margins, 'readerTextColor', '文字颜色', placeholder='#4a372b')
        self._text(margins, 'readerLinkColor', '链接颜色', placeholder='#6c4d2e')
        behavior = self._group(layout, '阅读行为')
        self._bool(behavior, 'readerRememberPosition', '记住每本书阅读位置')
        self._bool(behavior, 'readerAutoConvert', '自动将其他格式转换为 EPUB')
        note = QLabel('阅读窗口工具栏新增“书页设置”（Ctrl+Shift+P），可以在读书时直接修改字体、正文宽度、页边距和页面颜色并立即应用。LingKuma Reader 是独立窗口，因此不会弹出 Calibre 原生 ebook-viewer 的设置面板。')
        note.setWordWrap(True); note.setObjectName('muted'); layout.addWidget(note)

    def _page_about(self, layout):
        group = QGroupBox('关于')
        box = QVBoxLayout(group)
        self.about_text = QLabel()
        self.about_text.setProperty('_lk_i18n_preserve_html', True)
        self._update_about_text()
        self.about_text.setWordWrap(True); self.about_text.setOpenExternalLinks(True)
        box.addWidget(self.about_text)
        layout.addWidget(group)

    def _update_about_text(self, language=None):
        self.about_text.setText(
            f'<b>{PRODUCT} {VERSION_STR}</b><br><br>'
            + _tr('基于开源项目 LingKuma 1.1.1，将原有高亮、查词弹窗、AI 中文释义、整句翻译、词库、例句与 TTS 代码复用于 Calibre 桌面环境。', language)
            + '<br><br>'
            + _tr('本移植版使用独立适配层提供 Chrome storage/runtime 接口；上游 LingKuma 代码和许可证保留在插件包内。', language)
        )

    def load_controls(self):
        storage = self.state.storage
        language = storage.get('interfaceLanguage')
        self._unavailable_numeric_values = {}
        self._opacity_edited.clear()
        self._prompt1_edited = False
        self._prompt2_edited = False
        self._analysis_prompt_edited = False
        for key, (kind, widget) in self.controls.items():
            value = _get_nested(storage, key)
            if key == 'aiTranslationPrompt':
                widget.blockSignals(True)
                widget.setPlainText(str(self.state.ai_config_for_content().get('aiPrompt') or ''))
                widget.blockSignals(False)
                continue
            if key == 'aiTranslationPrompt2':
                widget.blockSignals(True)
                widget.setPlainText(str(self.state.ai_config_for_content().get('aiPrompt2') or ''))
                widget.blockSignals(False)
                continue
            if key == 'aiSentenceAnalysisPrompt':
                widget.blockSignals(True)
                widget.setPlainText(str(self.state.ai_config_for_content().get('aiAnalysisPrompt') or ''))
                widget.blockSignals(False)
                continue
            if kind == 'bool': widget.setChecked(bool(value))
            elif kind in {'text', 'multiline', 'shortcut'}:
                text = json.dumps(value, ensure_ascii=False, indent=2) if key == 'customCapsules' and isinstance(value, list) else str(value or '')
                if kind == 'shortcut':
                    widget.setMaxLength(max(16, len(text)))
                widget.setPlainText(text) if kind == 'multiline' else widget.setText(text)
            elif kind == 'combo':
                index = widget.findData(value)
                if index < 0 and value is not None:
                    # An older release may have saved a choice the current host
                    # cannot execute. Keep that explicit choice until the user
                    # selects a supported one; editing another field must not
                    # silently turn it into the first option.
                    widget.addItem(_tr('原有值（当前不可选：{value}）', language).format(value=str(value)[:40]), value)
                    index = widget.count() - 1
                    widget.setProperty('_lk_legacy_item_index', index)
                widget.setCurrentIndex(index if index >= 0 else 0)
            elif kind == 'editable_combo':
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    widget.setCurrentIndex(-1)
                    widget.setEditText(str(value or ''))
            elif kind in {'int', 'float'}:
                if key in _OPACITY_COLORS:
                    percent = _color_opacity(_get_nested(storage, _OPACITY_COLORS[key]))
                    widget.blockSignals(True)
                    widget.setValue(percent if percent is not None else 100)
                    widget.blockSignals(False)
                    continue
                numeric_value = int(value or 0) if kind == 'int' else float(value or 0)
                widget.setSuffix(self._numeric_base_suffixes[key])
                widget.setToolTip('')
                widget.setValue(numeric_value)
                if value is not None and widget.value() != numeric_value:
                    # Qt clamps values outside the current range. An unrelated
                    # save must not replace a previously saved explicit value.
                    self._unavailable_numeric_values[key] = value
                    widget.setSuffix(self._numeric_base_suffixes[key] + _tr('（保留旧值 {value}）', language).format(value=value))
                    widget.setToolTip(_tr('当前选项范围为 {minimum}–{maximum}。旧值 {value} 将保留；修改此项后使用新值。', language).format(
                        minimum=widget.minimum(), maximum=widget.maximum(), value=value))
        self._load_ai_profiles()

    def _load_ai_profiles(self):
        raw = self.state.storage.get('customApiProfiles')
        self._ai_profiles = json.loads(json.dumps(raw)) if isinstance(raw, dict) else {}
        profiles = self._ai_profiles.get('profiles')
        self._ai_profiles_readonly = raw is not None and not isinstance(raw, dict)
        if isinstance(profiles, list):
            valid = [item for item in profiles if isinstance(item, dict) and str(item.get('id') or '')]
            ids = [str(item['id']) for item in valid]
            if len(valid) != len(profiles) or len(set(ids)) != len(ids) or len(valid) > 20:
                self._ai_profiles_readonly = True
                profiles = valid
                self._ai_profiles['profiles'] = profiles
        elif profiles is not None:
            self._ai_profiles_readonly = True
        if not isinstance(profiles, list) or not profiles:
            ai = self.state.storage.get('aiConfig') or {}
            profiles = [{
                'id': 'default', 'name': 'Default',
                'apiBaseURL': ai.get('apiBaseURL', ''), 'apiModel': ai.get('apiModel', ''),
                'apiKey': ai.get('apiKey', ''), 'apiTemperature': ai.get('apiTemperature', 1),
                'enablePolling': True, 'excludeTemperature': False, 'customRequestBody': '',
            }]
            self._ai_profiles = {'profiles': profiles, 'activeProfileId': 'default'}
        active = self._ai_profiles.get('activeProfileId')
        if not any(isinstance(item, dict) and item.get('id') == active for item in profiles):
            self._ai_profiles['activeProfileId'] = profiles[0].get('id')
        self._ai_profiles_dirty = False
        self.ai_profile_warning.setVisible(self._ai_profiles_readonly)
        self._refresh_ai_profile_select()
        self._show_ai_profile()

    def _refresh_ai_profile_select(self):
        profiles = self._ai_profiles['profiles']
        self.ai_profile_select.blockSignals(True)
        self.ai_profile_select.clear()
        for profile in profiles:
            self.ai_profile_select.addItem(str(profile.get('name') or profile.get('id') or 'Profile'), profile.get('id'))
        self.ai_profile_select.setCurrentIndex(self.ai_profile_select.findData(self._ai_profiles['activeProfileId']))
        self.ai_profile_select.blockSignals(False)
        self.ai_profile_select.setEnabled(not self._ai_profiles_readonly)
        self.ai_profile_buttons['add'].setEnabled(not self._ai_profiles_readonly and len(profiles) < 20)
        self.ai_profile_buttons['copy'].setEnabled(not self._ai_profiles_readonly and len(profiles) < 20)
        self.ai_profile_buttons['delete'].setEnabled(not self._ai_profiles_readonly and len(profiles) > 1)
        for widget in self.ai_profile_fields.values():
            widget.setEnabled(not self._ai_profiles_readonly)

    def _add_ai_profile(self, copy_current):
        if self._ai_profiles_readonly:
            return
        profiles = self._ai_profiles['profiles']
        if len(profiles) >= 20:
            return
        active = self._ai_profiles['activeProfileId']
        source = next((item for item in profiles if item.get('id') == active), {})
        used = {str(item.get('id')) for item in profiles}
        number = 1
        while f'profile-{number}' in used:
            number += 1
        profile = json.loads(json.dumps(source)) if copy_current else {
            'apiBaseURL': '', 'apiModel': '', 'apiKey': '', 'apiTemperature': 1,
            'enablePolling': False, 'excludeTemperature': False, 'customRequestBody': '',
        }
        profile['id'] = f'profile-{number}'
        profile['name'] = f"{source.get('name') or 'Profile'} copy" if copy_current else f'Profile {len(profiles) + 1}'
        profiles.append(profile)
        self._ai_profiles['activeProfileId'] = profile['id']
        self._ai_profiles_dirty = True
        self._refresh_ai_profile_select()
        self._show_ai_profile()

    def _delete_ai_profile(self):
        if self._ai_profiles_readonly:
            return
        profiles = self._ai_profiles['profiles']
        if len(profiles) <= 1:
            return
        active = self._ai_profiles['activeProfileId']
        index = next((position for position, item in enumerate(profiles) if item.get('id') == active), 0)
        profiles.pop(index)
        self._ai_profiles['activeProfileId'] = profiles[min(index, len(profiles) - 1)]['id']
        self._ai_profiles_dirty = True
        self._refresh_ai_profile_select()
        self._show_ai_profile()

    def _show_ai_profile(self):
        active = self._ai_profiles.get('activeProfileId')
        profile = next((item for item in self._ai_profiles['profiles'] if item.get('id') == active), None)
        if profile is None:
            return
        for key, widget in self.ai_profile_fields.items():
            widget.blockSignals(True)
            value = profile.get(key)
            if isinstance(widget, QCheckBox):
                widget.setChecked(value is True)
            elif isinstance(widget, QDoubleSpinBox):
                try: numeric = float(value if value is not None else 1)
                except (TypeError, ValueError): numeric = 1
                widget.setSuffix('')
                widget.setToolTip('')
                widget.setValue(numeric)
                if value is not None and widget.value() != numeric:
                    language = self.controls['interfaceLanguage'][1].currentData()
                    widget.setSuffix(_tr('（保留旧值 {value}）', language).format(value=value))
                    widget.setToolTip(_tr('当前选项范围为 {minimum}–{maximum}。旧值 {value} 将保留；修改此项后使用新值。', language).format(
                        minimum=widget.minimum(), maximum=widget.maximum(), value=value))
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(str(value or ''))
            else:
                widget.setText(str(value or ''))
            widget.blockSignals(False)

    def _select_ai_profile(self, index):
        if index < 0 or self._ai_profiles is None or self._ai_profiles_readonly:
            return
        self._ai_profiles['activeProfileId'] = self.ai_profile_select.itemData(index)
        self._ai_profiles_dirty = True
        self._show_ai_profile()

    def _ai_profile_field_changed(self, key):
        if self._ai_profiles is None or self._ai_profiles_readonly:
            return
        active = self._ai_profiles['activeProfileId']
        profile = next((item for item in self._ai_profiles['profiles'] if item.get('id') == active), None)
        if profile is None:
            return
        widget = self.ai_profile_fields[key]
        if isinstance(widget, QCheckBox): value = widget.isChecked()
        elif isinstance(widget, QDoubleSpinBox): value = widget.value()
        elif isinstance(widget, QPlainTextEdit): value = widget.toPlainText()
        else: value = widget.text()
        profile[key] = value
        if key == 'apiTemperature':
            widget.setSuffix('')
            widget.setToolTip('')
        if key == 'name':
            self.ai_profile_select.setItemText(self.ai_profile_select.currentIndex(), str(value or active))
        self._ai_profiles_dirty = True

    def collect_controls(self):
        values = json.loads(json.dumps(self.state.storage, ensure_ascii=False))
        for key, (kind, widget) in self.controls.items():
            if key == 'aiTranslationPrompt' and not self._prompt1_edited:
                continue
            if key == 'aiTranslationPrompt2' and not self._prompt2_edited:
                continue
            if key == 'aiSentenceAnalysisPrompt' and not self._analysis_prompt_edited:
                continue
            if kind == 'bool': value = widget.isChecked()
            elif kind == 'text': value = widget.text().strip()
            elif kind == 'shortcut': value = widget.text()
            elif kind == 'multiline':
                value = widget.toPlainText().strip()
                if key == 'customCapsules':
                    try: value = json.loads(value or '[]')
                    except json.JSONDecodeError as error: raise ValueError(_tr('自定义胶囊 JSON 无效：{error}', self.controls['interfaceLanguage'][1].currentData()).format(error=error))
            elif kind == 'combo': value = widget.currentData()
            elif kind == 'editable_combo':
                index = widget.currentIndex()
                value = widget.itemData(index) if index >= 0 and widget.currentText() == widget.itemText(index) else widget.currentText().strip()
            elif kind in {'int', 'float'}: value = self._unavailable_numeric_values.get(key, widget.value())
            _set_nested(values, key, value)
        if self._ai_profiles_dirty:
            values['customApiProfiles'] = json.loads(json.dumps(self._ai_profiles))
        if self._prompt1_edited:
            prompt = values['aiTranslationPrompt']
            values['aiPrompt'] = prompt
            _set_nested(values, 'aiConfig.aiPrompt', prompt)
        if self._prompt2_edited:
            prompt = values['aiTranslationPrompt2']
            values['aiPrompt2'] = prompt
            _set_nested(values, 'aiConfig.aiPrompt2', prompt)
        if self._analysis_prompt_edited:
            prompt = values['aiSentenceAnalysisPrompt']
            values['aiAnalysisPrompt'] = prompt
            _set_nested(values, 'aiConfig.aiAnalysisPrompt', prompt)
        for opacity_key in self._opacity_edited:
            color_key = _OPACITY_COLORS[opacity_key]
            color = str(values.get(color_key) or '')
            if not re.fullmatch(r'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', color):
                raise ValueError(_tr('颜色格式无效：{key}；需要 #RRGGBB 或 #RRGGBBAA', self.controls['interfaceLanguage'][1].currentData()).format(key=color_key))
            alpha = int(values[opacity_key] * 2.55 + .5)
            values[color_key] = color[:7] + f'{alpha:02X}'
        self._validate_shortcuts(values)
        return values

    def _validate_shortcuts(self, values):
        named = {'tab', 'capslock', 'enter', 'escape', 'backspace', 'delete',
                 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'}
        changed = set()
        for key, (kind, _) in self.controls.items():
            if kind != 'shortcut':
                continue
            raw = _get_nested(values, key)
            if raw == _get_nested(self.state.storage, key):
                continue
            normalized = ' ' if raw == ' ' or str(raw).strip().lower() == 'space' else str(raw).strip().lower()
            allow_named = key in {'wordQueryKey', 'copySentenceKey', 'analysisWindowKey',
                                  'sentenceExplosionKey', 'wordStatusKeys.addAITranslation',
                                  'wordStatusKeys.closeTooltip'}
            if (len(normalized) != 1 or normalized.isspace()) and not (allow_named and normalized in named) and normalized != ' ':
                raise ValueError(_tr('快捷键无效：{key}', self.controls['interfaceLanguage'][1].currentData()).format(key=key))
            _set_nested(values, key, normalized)
            changed.add(key)
        reserved = str(values.get('sidePanelKey') or 'r').strip().lower()
        used = {reserved: 'sidePanelKey'}
        for key, (kind, _) in self.controls.items():
            if kind != 'shortcut':
                continue
            value = _get_nested(values, key)
            normalized = ' ' if value == ' ' or str(value).strip().lower() == 'space' else str(value).strip().lower()
            prior = used.get(normalized)
            if prior and (key in changed or prior in changed):
                raise ValueError(_tr('快捷键冲突：{key} 与 {prior}', self.controls['interfaceLanguage'][1].currentData()).format(key=key, prior=prior))
            used.setdefault(normalized, key)

    def save_and_accept(self):
        try:
            values = self.collect_controls()
            self.state.storage_set(values)
            if callable(self.on_saved): self.on_saved()
            self.accept()
        except Exception as error:
            QMessageBox.critical(self, _tr('无法保存设置', self.controls['interfaceLanguage'][1].currentData()), str(error))

    def _dictionary_status_text(self, language=None):
        config = self.state.storage.get('dictionaryConfig') or {}
        return _tr('当前：自定义词典' if config.get('mode') == 'custom' else '当前：默认词典', language)

    def select_default_dictionary(self):
        try:
            config = self.state.storage.get('dictionaryConfig') or {}
            self.state.storage_set({'dictionaryConfig': {**config, 'mode': 'default'}})
            self.dictionary_status.setProperty('_lk_i18n_dynamic_mode', True)
            self.dictionary_status.setText(self._dictionary_status_text(self.controls['interfaceLanguage'][1].currentData()))
            if callable(self.on_saved):
                self.on_saved()
        except Exception as error:
            QMessageBox.critical(self, _tr('无法保存设置', self.controls['interfaceLanguage'][1].currentData()), str(error))

    def select_custom_dictionary(self):
        try:
            config = self.state.storage.get('dictionaryConfig') or {}
            self.state.storage_set({'dictionaryConfig': {**config, 'mode': 'custom'}})
            self.dictionary_status.setProperty('_lk_i18n_dynamic_mode', True)
            self.dictionary_status.setText(self._dictionary_status_text(self.controls['interfaceLanguage'][1].currentData()))
            if callable(self.on_saved):
                self.on_saved()
        except Exception as error:
            QMessageBox.critical(self, _tr('无法保存设置', self.controls['interfaceLanguage'][1].currentData()), str(error))

    def import_custom_dictionary(self):
        path, _ = QFileDialog.getOpenFileName(self, _tr('导入自定义词典', self.controls['interfaceLanguage'][1].currentData()), '', _tr('LingKuma 词典 (*.lkdict)', self.controls['interfaceLanguage'][1].currentData()))
        if not path:
            return
        from calibre_plugins.lingkuma_calibre.dictionary_import import DictionaryImport
        self.dictionary_import_button.setEnabled(False)
        self.dictionary_default_button.setEnabled(False)
        self.dictionary_custom_button.setEnabled(False)

        def finished(result, error):
            self.dictionary_import_button.setEnabled(True)
            self.dictionary_default_button.setEnabled(True)
            self.dictionary_custom_button.setEnabled(True)
            if error:
                QMessageBox.critical(self, _tr('导入自定义词典', self.controls['interfaceLanguage'][1].currentData()), str(error))
                return
            self.dictionary_status.setProperty('_lk_i18n_dynamic_mode', True)
            self.dictionary_status.setText(self._dictionary_status_text(self.controls['interfaceLanguage'][1].currentData()))
            if callable(self.on_saved):
                self.on_saved()
            QMessageBox.information(self, _tr('导入自定义词典', self.controls['interfaceLanguage'][1].currentData()), _tr('自定义词典已导入。', self.controls['interfaceLanguage'][1].currentData()))

        try:
            worker = DictionaryImport(self.state, Path(__file__).resolve().parent / 'resources', path, finished)
            worker.start()
        except Exception as error:
            self.dictionary_import_button.setEnabled(True)
            self.dictionary_default_button.setEnabled(True)
            self.dictionary_custom_button.setEnabled(True)
            QMessageBox.critical(self, _tr('导入自定义词典', self.controls['interfaceLanguage'][1].currentData()), str(error))

    def refresh_dictionary_status(self):
        from calibre_plugins.lingkuma_calibre.dictionary_import import DictionaryStatus
        self.dictionary_refresh_button.setEnabled(False)

        def finished(result, error):
            self.dictionary_refresh_button.setEnabled(True)
            self.dictionary_status.setProperty('_lk_i18n_dynamic_mode', False)
            if error or not isinstance(result, dict):
                self.dictionary_status.setText(_tr('词典状态不可用', self.controls['interfaceLanguage'][1].currentData()))
                return
            pair = ' → '.join(filter(None, (result.get('sourceLanguage'), result.get('targetLanguage'))))
            reason = result.get('reason')
            if reason == 'NO_CATALOG_PAIR':
                reason = _tr('未确定当前语言组合', self.controls['interfaceLanguage'][1].currentData())
            self.dictionary_status.setText(' · '.join(filter(None, (
                str(result.get('mode') or 'default').upper(),
                str(result.get('status') or 'UNAVAILABLE').upper(),
                str(result.get('dictionaryID') or ''), pair, str(reason or ''),
            ))))

        try:
            worker = DictionaryStatus(self.state, Path(__file__).resolve().parent / 'resources', finished)
            worker.start()
        except Exception:
            self.dictionary_refresh_button.setEnabled(True)
            self.dictionary_status.setProperty('_lk_i18n_dynamic_mode', False)
            self.dictionary_status.setText(_tr('词典状态不可用', self.controls['interfaceLanguage'][1].currentData()))

    def _restore_popup(self):
        self.state.storage_set({'tooltipMinimized': False})
        language = self.controls['interfaceLanguage'][1].currentData()
        QMessageBox.information(self, _tr('已恢复', language), _tr('最小化状态已清除。重新点击单词后会显示完整弹窗。', language))

    def _set_word_page_info(self, language=None):
        page, pages, count = self._word_page_info_values
        self.word_page_info.setText(_tr('第 {page} / {pages} 页，共 {count} 条', language).format(
            page=page, pages=pages, count=count))

    def refresh_vocabulary(self):
        if not hasattr(self, 'word_table'): return
        query = self.word_search.text().strip().lower()
        status = self.word_filter.currentData()
        rows = []
        for word, record in self.state.get_all_words().items():
            if status != 'all' and str(record.get('status', '0')) != str(status): continue
            haystack = ' '.join([word, str(record.get('term', '')), *(record.get('translations') or []), *(record.get('tags') or [])]).lower()
            if query and query not in haystack: continue
            rows.append((word, record))
        rows.sort(key=lambda item: str(item[1].get('term') or item[0]).lower())
        page_size = int(self.word_page_size.currentData() or 20)
        page_count = max(1, (len(rows) + page_size - 1) // page_size)
        self.word_page = max(1, min(self.word_page, page_count))
        self.word_prev.setEnabled(self.word_page > 1)
        self.word_next.setEnabled(self.word_page < page_count)
        self._word_page_info_values = (self.word_page, page_count, len(rows))
        self._set_word_page_info(self.controls['interfaceLanguage'][1].currentData())
        start = (self.word_page - 1) * page_size
        rows = rows[start:start + page_size]
        self._word_translation_snapshot = {
            word: '；'.join(rec.get('translations') or []) for word, rec in rows}
        self.word_table.blockSignals(True)
        self.word_table.setRowCount(len(rows))
        for row, (word, rec) in enumerate(rows):
            values = [rec.get('term') or word, str(rec.get('status', '0')), '；'.join(rec.get('translations') or []), '；'.join(rec.get('tags') or []), str(len(rec.get('sentences') or []))]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value)); item.setData(Qt.ItemDataRole.UserRole, word)
                if col in {0, 2, 4}: item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.word_table.setItem(row, col, item)
        self.word_table.blockSignals(False)
        self.word_table.resizeColumnsToContents()
        self._update_adopt_meaning_enabled()

    def _update_adopt_meaning_enabled(self):
        selected = self.word_table.selectionModel().selectedRows()
        item = self.word_table.item(selected[0].row(), 2) if len(selected) == 1 else None
        enabled = bool(item and item.text().strip())
        self.adopt_meaning_button.setEnabled(enabled)
        self.edit_meaning_button.setEnabled(enabled)
        self.delete_meaning_button.setEnabled(enabled)

    def _selected_meaning_record(self):
        selected = self.word_table.selectionModel().selectedRows()
        if len(selected) != 1:
            return None
        row = selected[0].row()
        word = self.word_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        record = self.state.get_word(word)
        if not record or not record.get('translations'):
            return None
        language = self.controls['interfaceLanguage'][1].currentData()
        if self.word_table.item(row, 2).text() != self._word_translation_snapshot.get(word, ''):
            QMessageBox.information(self, _tr('保存表格修改', language),
                                    _tr('词库已变化，请刷新后再保存。', language))
            return None
        return row, word, list(record['translations']), language

    def _change_selected_meaning(self, delete=False):
        context = self._selected_meaning_record()
        if context is None:
            return
        row, word, candidates, language = context
        title = '删除释义' if delete else '修改释义'
        choices = [f'{index + 1}. {meaning}' for index, meaning in enumerate(candidates)]
        choice, accepted = QInputDialog.getItem(
            self, _tr(title, language), _tr('选择要修改的释义', language),
            choices, 0, False)
        if not accepted or choice not in choices:
            return
        position = choices.index(choice)
        meaning = candidates[position]
        if delete:
            if QMessageBox.question(self, _tr(title, language),
                                    _tr('删除选中的释义？', language)) != QMessageBox.StandardButton.Yes:
                return
            replacement = None
        else:
            replacement, accepted = QInputDialog.getText(
                self, _tr(title, language), _tr('释义内容', language),
                QLineEdit.EchoMode.Normal, meaning)
            if not accepted or not replacement.strip():
                return
        updated = self.state.change_translation(word, position, candidates, replacement)
        if not updated:
            QMessageBox.information(self, _tr(title, language),
                                    _tr('词库已变化，请刷新后再保存。', language))
            return
        display = '；'.join(updated.get('translations') or [])
        self._word_translation_snapshot[word] = display
        self.word_table.item(row, 2).setText(display)

    def edit_selected_meaning(self):
        self._change_selected_meaning()

    def delete_selected_meaning(self):
        self._change_selected_meaning(delete=True)

    def adopt_selected_meaning(self):
        selected = self.word_table.selectionModel().selectedRows()
        if len(selected) != 1:
            return
        row = selected[0].row()
        word = self.word_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        record = self.state.get_word(word)
        if not record:
            return
        candidate_text = self.word_table.item(row, 2).text()
        if candidate_text != self._word_translation_snapshot.get(word, ''):
            language = self.controls['interfaceLanguage'][1].currentData()
            QMessageBox.information(self, _tr('采用释义', language), _tr('保存表格修改', language))
            return
        candidates = list(record.get('translations') or [])
        if not candidates:
            return
        language = self.controls['interfaceLanguage'][1].currentData()
        meaning, accepted = QInputDialog.getItem(
            self, _tr('采用释义', language), _tr('选择要采用的释义', language),
            candidates, 0, False)
        if not accepted or meaning not in candidates:
            return
        adopted = self.state.adopt_translation(word, meaning, candidates)
        if adopted:
            display = '；'.join(adopted['translations'])
            self._word_translation_snapshot[word] = display
            self.word_table.item(row, 2).setText(display)

    def _reset_vocabulary_page(self, *_args):
        self.word_page = 1
        self.refresh_vocabulary()

    def _change_vocabulary_page(self, direction):
        self.word_page += direction
        self.refresh_vocabulary()

    def save_vocabulary_table(self):
        language = self.controls['interfaceLanguage'][1].currentData()
        for row in range(self.word_table.rowCount()):
            status = self.word_table.item(row, 1).text().strip()
            if status not in {'0', '1', '2', '3', '4', '5'}:
                word = self.word_table.item(row, 0).text()
                QMessageBox.critical(self, _tr('词汇状态无效', language), _tr('单词 {word} 的状态必须是 0–5。', language).format(word=word))
                return
            word_key = self.word_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            record = self.state.get_word(word_key)
            if record:
                shown = self.word_table.item(row, 2).text()
                snapshot = self._word_translation_snapshot.get(word_key, shown)
                if shown != snapshot and '；'.join(record.get('translations') or []) != snapshot:
                    QMessageBox.information(self, _tr('保存表格修改', language),
                                            _tr('词库已变化，请刷新后再保存。', language))
                    return
        for row in range(self.word_table.rowCount()):
            word = self.word_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            rec = self.state.get_word(word)
            if not rec: continue
            status = self.word_table.item(row, 1).text().strip()
            translation_text = self.word_table.item(row, 2).text()
            tag_text = self.word_table.item(row, 3).text()
            details = {}
            if translation_text != self._word_translation_snapshot.get(word, translation_text):
                details['translations'] = [x.strip() for x in translation_text.replace(';', '；').split('；') if x.strip()]
            if tag_text != '；'.join(rec.get('tags') or []):
                details['tags'] = [x.strip() for x in tag_text.replace(';', '；').split('；') if x.strip()]
            if details:
                self.state.update_language(word, details)
                self._word_translation_snapshot[word] = translation_text
            if status != str(rec.get('status', '0')):
                self.state.update_status(word, status)
        QMessageBox.information(self, _tr('保存完成', language), _tr('词库修改已经保存。', language))

    def delete_selected_words(self):
        rows = sorted({index.row() for index in self.word_table.selectionModel().selectedRows()}, reverse=True)
        if not rows: return
        language = self.controls['interfaceLanguage'][1].currentData()
        if QMessageBox.question(self, _tr('确认删除', language), _tr('删除所选 {count} 个单词？', language).format(count=len(rows))) != QMessageBox.StandardButton.Yes: return
        for row in rows:
            word = self.word_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.state.delete_word(word)
        self.refresh_vocabulary()

    def export_backup(self):
        language = self.controls['interfaceLanguage'][1].currentData()
        path, _ = QFileDialog.getSaveFileName(self, _tr('导出 LingKuma 备份', language), 'lingkuma-calibre-backup.json', 'JSON (*.json)')
        if not path: return
        Path(path).write_text(json.dumps(self.state.export_data(), ensure_ascii=False, indent=2), encoding='utf-8')
        QMessageBox.information(self, _tr('导出完成', language), path)

    def export_learning_data(self):
        language = self.controls['interfaceLanguage'][1].currentData()
        path, _ = QFileDialog.getSaveFileName(self, _tr('导出学习数据', language), 'lingkuma-learning.json', 'JSON (*.json)')
        if not path: return
        destination = Path(path)
        temporary = None
        try:
            data = json.dumps(self.state.export_learning_data(), ensure_ascii=False, indent=2)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                             prefix=f'.{destination.name}.', suffix='.tmp',
                                             delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            os.replace(temporary, destination)
            QMessageBox.information(self, _tr('导出完成', language), path)
        except Exception as error:
            QMessageBox.critical(self, _tr('导出失败', language), str(error))
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def import_backup(self, merge=True):
        language = self.controls['interfaceLanguage'][1].currentData()
        path, _ = QFileDialog.getOpenFileName(self, _tr('导入 LingKuma 数据', language), '', _tr('LingKuma 数据 (*.json *.txt *.csv);;所有文件 (*)', language))
        if not path: return
        if not merge and QMessageBox.question(
                self, _tr('覆盖确认', self.controls['interfaceLanguage'][1].currentData()),
                _tr('导入并替换会更新本地设置并替换全部词库，是否继续？', self.controls['interfaceLanguage'][1].currentData())) != QMessageBox.StandardButton.Yes:
            return
        try:
            count = self.state.import_data(Path(path).read_text(encoding='utf-8-sig'), merge=merge)
            self.load_controls(); self.refresh_vocabulary()
            QMessageBox.information(self, _tr('导入完成', language), _tr('已处理 {count} 条词汇记录。', language).format(count=count))
        except Exception as error:
            QMessageBox.critical(self, _tr('导入失败', language), str(error))

    def choose_word_import_file(self):
        language = self.controls['interfaceLanguage'][1].currentData()
        path, _ = QFileDialog.getOpenFileName(self, _tr('选择词汇文件', language), '',
                                              _tr('词汇文件 (*.json *.txt *.csv);;所有文件 (*)', language))
        if path:
            try:
                content = Path(path).read_text(encoding='utf-8-sig')
                if Path(path).suffix.lower() == '.csv':
                    reader = csv.DictReader(io.StringIO(content))
                    if not reader.fieldnames or 'word' not in reader.fieldnames:
                        raise ValueError(_tr('CSV 需要 word 表头', language))
                    rows = [row for row in reader if row.get('word')]
                    content = json.dumps([row['word'] for row in rows] if reader.fieldnames == ['word'] else rows,
                                         ensure_ascii=False)
                self.word_import_text.setPlainText(content)
            except Exception as error:
                QMessageBox.critical(self, _tr('导入失败', language), str(error))

    def import_words(self):
        interface_language = self.controls['interfaceLanguage'][1].currentData()
        try:
            language = self.word_import_language.currentData()
            if language == 'custom':
                language = self.word_import_custom_language.text()
            merge = self.word_import_mode.currentData() == 'merge'
            payload = self.word_import_text.toPlainText()
            if not merge and QMessageBox.question(
                    self, _tr('覆盖确认', interface_language), _tr('替换将删除当前全部词汇记录，是否继续？', interface_language)) != QMessageBox.StandardButton.Yes:
                return
            count = self.state.import_words_only(payload, merge=merge,
                                                 language=language,
                                                 status=self.word_import_status.currentData())
            self.refresh_vocabulary()
            self.refresh_statistics()
            QMessageBox.information(self, _tr('导入完成', interface_language), _tr('已处理 {count} 条词汇记录。', interface_language).format(count=count))
        except Exception as error:
            QMessageBox.critical(self, _tr('导入失败', interface_language), str(error))

    def clear_vocabulary(self):
        language = self.controls['interfaceLanguage'][1].currentData()
        if QMessageBox.question(self, _tr('确认清空', language), _tr('这会删除全部本地词汇记录，是否继续？', language)) == QMessageBox.StandardButton.Yes:
            try:
                self.state.clear_words()
            except Exception as error:
                QMessageBox.critical(self, _tr('清空失败', language), str(error))
                return
            self.refresh_vocabulary()
            self.refresh_statistics()
            if callable(self.on_saved):
                self.on_saved()

    def trim_sentences(self):
        language = self.controls['interfaceLanguage'][1].currentData()
        keep_count = self.sentence_keep_count.value()
        prompt = _tr('确定要将每个词的例句保留为前 {count} 条吗？此操作不可撤销。', language).format(count=keep_count)
        if QMessageBox.question(self, _tr('确认清理例句', language), prompt) != QMessageBox.StandardButton.Yes:
            return
        try:
            removed = self.state.trim_sentences(keep_count)
        except Exception as error:
            QMessageBox.critical(self, _tr('清理例句失败', language), str(error))
            return
        self.refresh_vocabulary()
        QMessageBox.information(self, _tr('例句清理完成', language),
                                _tr('已删除 {count} 条多余例句。', language).format(count=removed))

    def _current_webdav(self):
        values = self.collect_controls()
        return _get_nested(values, 'webdavConfig', {})

    def test_local_tts(self):
        try:
            self._speak_local_tts("Hahaha, this is a local TTS test. I'm a robot, but I have feelings too! Teehee, ribbit ribbit, gurgle gurgle, ding dong, oh my goodness, this is absolutely hilarious!")
        except Exception as error:
            QMessageBox.critical(self, _tr('本地 TTS 测试失败', self.controls['interfaceLanguage'][1].currentData()), str(error))

    def _speak_local_tts(self, text):
        self.stop_tts_preview()
        if not QTextToSpeech.availableEngines():
            raise RuntimeError(_tr('当前系统没有可用的本地 TTS', self.controls['interfaceLanguage'][1].currentData()))
        speech = getattr(self, '_local_tts', None)
        if speech is None:
            speech = QTextToSpeech(self)
            self._local_tts = speech
        preferred = self.controls['localTTSVoice'][1].text().strip()
        if preferred and preferred.lower() != 'auto':
            voice = next((voice for voice in speech.availableVoices()
                          if voice.name() == preferred), None)
            if voice is not None:
                speech.setVoice(voice)
        speech.setRate(max(-1, min(1, self.controls['localTTSRate'][1].value() - 1)))
        speech.setPitch(max(-1, min(1, self.controls['localTTSPitch'][1].value() - 1)))
        speech.stop()
        speech.say(text)

    def test_selected_word_tts(self):
        provider = self.controls['wordTTSProvider'][1].currentData()
        if provider == 'local':
            try:
                self._speak_local_tts('Hello')
            except Exception as error:
                QMessageBox.critical(self, _tr('本地 TTS 测试失败', self.controls['interfaceLanguage'][1].currentData()), str(error))
        elif provider == 'edge':
            self._start_edge_tts_preview()
        elif provider == 'gpt':
            self._start_gpt_tts_preview()
        else:
            self.stop_tts_preview()
            QMessageBox.information(self, 'TTS', _tr('当前语音渠道不支持试听', self.controls['interfaceLanguage'][1].currentData()))

    def _edge_preview_html(self):
        roots = (Path(__file__).resolve().parent / 'resources',
                 PLUGIN_DIR / f'runtime-{VERSION_STR}' / 'resources')
        files = ('upstream/src/plugin/edge_tts.js', 'adapter/edge_tts_bridge.js')
        root = next((candidate for candidate in roots
                     if all((candidate / name).is_file() for name in files)), None)
        if root is None:
            raise RuntimeError(_tr('Edge TTS 资源不可用', self.controls['interfaceLanguage'][1].currentData()))
        scripts = ['<script>globalThis.__LINGKUMA_CALIBRE_READER__=true;</script>']
        for name in files:
            source = (root / name).read_text(encoding='utf-8').replace('</script', '<\\/script')
            scripts.append('<script>' + source + '</script>')
        return '<!doctype html><html><head><meta charset="utf-8"></head><body>' + ''.join(scripts) + '</body></html>'

    def _start_edge_tts_preview(self):
        self.stop_tts_preview()
        language = self.controls['interfaceLanguage'][1].currentData()
        try:
            voice = (self.controls['edgeTTSVoice'][1].text().strip()
                     if not self.controls['edgeTTSAutoVoice'][1].isChecked() else '')
            options = {
                'text': 'Hello', 'language': 'en-US',
                'voice': voice or 'en-US-AriaNeural',
                'rate': _edge_preview_percent(self.controls['edgeTTSRate'][1].value()),
                'volume': _edge_preview_percent(self.controls['edgeTTSVolume'][1].value()),
                'pitch': _edge_preview_percent(self.controls['edgeTTSPitch'][1].value()),
            }
            request_id = secrets.token_urlsafe(18)
            options['requestId'] = request_id
            self._edge_preview_request_id = request_id
            generation = self._tts_preview_generation
            results = queue.Queue(maxsize=1)
            def synthesize():
                try:
                    results.put((fetch_edge_tts_audio(options), None))
                except Exception as error:
                    key = str(error).strip()
                    if key not in {'Edge TTS connection failed', 'Edge TTS synthesis failed',
                                   'Edge TTS audio playback failed', 'Edge TTS preview failed'}:
                        key = 'Edge TTS preview failed'
                    results.put((None, key))
            threading.Thread(target=synthesize, daemon=True, name='LingKuma Edge preview').start()
            timer = QTimer(self)
            self._tts_preview_timer = timer
            timer.setInterval(100)
            timer.timeout.connect(lambda: self._poll_edge_host_preview(generation, results))
            timer.start()
            QTimer.singleShot(26000, lambda: self._edge_preview_timeout(generation))
        except Exception as error:
            self.stop_tts_preview()
            QMessageBox.critical(self, _tr('Edge TTS 试听失败', language),
                                 _tr('Edge TTS preview failed', language))

    def _poll_edge_host_preview(self, generation, results):
        if generation != self._tts_preview_generation:
            return
        try:
            result, error = results.get_nowait()
        except queue.Empty:
            return
        self._edge_preview_request_id = None
        if error or not result or result.get('mimeType') != 'audio/mpeg' or not result.get('audioBase64'):
            self._edge_preview_failed(error or 'Edge TTS synthesis failed', generation)
            return
        timer = self._tts_preview_timer
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._tts_preview_timer = None
        page = QWebEnginePage(self)
        self._tts_preview_page = page
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        page.loadFinished.connect(lambda ok: self._edge_preview_audio_loaded(ok, generation, result))
        page.setHtml('<!doctype html><html><body></body></html>', QUrl('http://127.0.0.1/'))

    def _edge_preview_audio_loaded(self, ok, generation, result):
        if generation != self._tts_preview_generation:
            return
        if not ok:
            self._edge_preview_failed('Edge TTS audio playback failed', generation)
            return
        uri = 'data:audio/mpeg;base64,' + result['audioBase64']
        script = ('(() => { const generation = ' + str(generation) + ';'
                  'const audio = new Audio(' + json.dumps(uri) + ');'
                  'globalThis.__lkEdgePreviewAudio = audio;'
                  'audio.addEventListener("error", () => {globalThis.__lkPreviewResult={generation,state:"error",error:"Edge TTS audio playback failed"};});'
                  'audio.addEventListener("ended", () => {globalThis.__lkPreviewResult={generation,state:"ended"};});'
                  'audio.play().then(() => {globalThis.__lkPreviewResult={generation,state:"started"};})'
                  '.catch(() => {globalThis.__lkPreviewResult={generation,state:"error",error:"Edge TTS audio playback failed"};}); })()')
        self._tts_preview_page.runJavaScript(script)
        timer = QTimer(self)
        self._tts_preview_timer = timer
        timer.setInterval(150)
        timer.timeout.connect(lambda: self._poll_edge_tts_preview(generation))
        timer.start()
        QTimer.singleShot(26000, lambda: self._edge_preview_timeout(generation))

    def _edge_preview_loaded(self, ok, generation, options):
        if generation != self._tts_preview_generation:
            return
        if not ok:
            self._edge_preview_failed('WebEngine page failed to load', generation)
            return
        script = ('(() => { const generation = ' + str(generation) + ';'
                  'const bridge = globalThis.__LINGKUMA_CALIBRE_EDGE_TTS__;'
                  'if (!bridge) { globalThis.__lkPreviewResult={generation,state:"error",error:"Edge TTS bridge unavailable"}; return; }'
                  'bridge.play(' + json.dumps(options, ensure_ascii=False) + ')'
                  '.then(result => { globalThis.__lkPreviewResult={generation,state:result?.success?"started":"stopped"}; })'
                  '.catch(error => { const message = error?.message || "Edge TTS preview failed";'
                  'globalThis.__lkPreviewResult={generation,state:"error",error:message}; }); })()')
        self._tts_preview_page.runJavaScript(script)
        timer = QTimer(self)
        self._tts_preview_timer = timer
        timer.setInterval(150)
        timer.timeout.connect(lambda: self._poll_edge_tts_preview(generation))
        timer.start()
        QTimer.singleShot(25000, lambda: self._edge_preview_timeout(generation))

    def _poll_edge_tts_preview(self, generation):
        page = self._tts_preview_page
        if generation == self._tts_preview_generation and page is not None:
            page.runJavaScript('JSON.stringify(globalThis.__lkPreviewResult || {})',
                               lambda value: self._edge_preview_result(value, generation))

    def _edge_preview_result(self, value, generation):
        if generation != self._tts_preview_generation or not value:
            return
        try:
            result = json.loads(value)
        except (TypeError, ValueError):
            return
        if result.get('generation') != generation:
            return
        if result.get('state') == 'error':
            self._edge_preview_failed(result.get('error') or 'Edge TTS failed', generation)
        elif result.get('state') in {'started', 'stopped', 'ended'} and self._tts_preview_timer is not None:
            self._tts_preview_timer.stop()

    def _edge_preview_timeout(self, generation):
        if generation == self._tts_preview_generation and self._tts_preview_timer is not None and self._tts_preview_timer.isActive():
            self._edge_preview_failed('Edge TTS timed out', generation)

    def _edge_preview_failed(self, error, generation):
        if generation != self._tts_preview_generation:
            return
        language = self.controls['interfaceLanguage'][1].currentData()
        self.stop_tts_preview()
        message = str(error or '').strip()
        if message not in {'Edge TTS connection failed', 'Edge TTS synthesis failed',
                           'Edge TTS audio playback failed', 'Edge TTS preview failed'}:
            message = 'Edge TTS preview failed'
        QMessageBox.critical(self, _tr('Edge TTS 试听失败', language), _tr(message, language))

    def _start_gpt_tts_preview(self):
        self.stop_tts_preview()
        language = self.controls['interfaceLanguage'][1].currentData()
        try:
            values = self.collect_controls()
            options = {
                'apiEndpoint': values['gptTTSBaseURL'],
                'apiKey': values['gptTTSApiKey'],
                'text': 'Hello',
                'model': values['gptTTSModel'],
                'voice': values['gptTTSVoice'],
                'instructions': values['gptTTSInstructions'],
                'responseFormat': values['gptTTSResponseFormat'],
                'speed': values['gptTTSSpeed'],
            }
            endpoint, headers, body, mime = prepare_gpt_tts_request(options)
        except ValueError as error:
            QMessageBox.critical(self, _tr('GPT TTS 试听失败', language),
                                 _tr(str(error), language))
            return
        generation = self._tts_preview_generation
        if self._gpt_tts_manager is None:
            self._gpt_tts_manager = QNetworkAccessManager(self)
        request = QNetworkRequest(QUrl(endpoint))
        request.setTransferTimeout(25000)
        for key, value in headers.items():
            request.setRawHeader(key.encode('ascii'), value.encode('utf-8'))
        reply = self._gpt_tts_manager.post(request, body)
        self._gpt_tts_reply = reply
        reply.finished.connect(lambda: self._gpt_preview_response(reply, generation, mime))

    def _gpt_preview_response(self, reply, generation, mime):
        if self._gpt_tts_reply is reply:
            self._gpt_tts_reply = None
        if generation != self._tts_preview_generation:
            reply.deleteLater()
            return
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        error = reply.error()
        failed = error != QNetworkReply.NetworkError.NoError
        audio = bytes(reply.readAll()) if not failed and status == 200 else b''
        reply.deleteLater()
        if failed or status != 200:
            self._gpt_preview_failed('GPT TTS network request failed' + (f' (HTTP {status})' if status else ''), generation)
            return
        if not audio or len(audio) > MAX_AUDIO_BYTES:
            self._gpt_preview_failed('GPT TTS returned empty or oversized audio', generation)
            return
        data_uri = 'data:' + mime + ';base64,' + base64.b64encode(audio).decode('ascii')
        page = QWebEnginePage(self)
        self._tts_preview_page = page
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        page.loadFinished.connect(lambda ok: self._gpt_preview_loaded(ok, generation, data_uri))
        page.setHtml('<!doctype html><html><body></body></html>', QUrl('http://127.0.0.1/'))

    def _gpt_preview_loaded(self, ok, generation, data_uri):
        if generation != self._tts_preview_generation:
            return
        if not ok:
            self._gpt_preview_failed('GPT TTS audio page failed to load', generation)
            return
        script = ('(() => { const generation = ' + str(generation) + ';'
                  'const audio = new Audio(' + json.dumps(data_uri) + ');'
                  'globalThis.__lkGptPreviewAudio = audio;'
                  'audio.addEventListener("error", () => {globalThis.__lkPreviewResult={generation,state:"error",error:"GPT TTS audio playback failed"};});'
                  'audio.addEventListener("ended", () => {globalThis.__lkPreviewResult={generation,state:"ended"};});'
                  'audio.play().then(() => {globalThis.__lkPreviewResult={generation,state:"playing"};})'
                  '.catch(() => {globalThis.__lkPreviewResult={generation,state:"error",error:"GPT TTS audio playback failed"};}); })()')
        self._tts_preview_page.runJavaScript(script)
        timer = QTimer(self)
        self._tts_preview_timer = timer
        timer.setInterval(150)
        timer.timeout.connect(lambda: self._poll_gpt_tts_preview(generation))
        timer.start()
        QTimer.singleShot(25000, lambda: self._gpt_preview_timeout(generation))

    def _poll_gpt_tts_preview(self, generation):
        page = self._tts_preview_page
        if generation == self._tts_preview_generation and page is not None:
            page.runJavaScript('JSON.stringify(globalThis.__lkPreviewResult || {})',
                               lambda value: self._gpt_preview_result(value, generation))

    def _gpt_preview_result(self, value, generation):
        if generation != self._tts_preview_generation or not value:
            return
        try:
            result = json.loads(value)
        except (TypeError, ValueError):
            return
        if result.get('generation') != generation:
            return
        if result.get('state') == 'error':
            self._gpt_preview_failed(result.get('error'), generation)
        elif result.get('state') == 'ended' and self._tts_preview_timer is not None:
            self._tts_preview_timer.stop()

    def _gpt_preview_timeout(self, generation):
        if generation == self._tts_preview_generation and self._tts_preview_timer is not None and self._tts_preview_timer.isActive():
            self._gpt_preview_failed('GPT TTS audio playback timed out', generation)

    def _gpt_preview_failed(self, error, generation):
        if generation != self._tts_preview_generation:
            return
        language = self.controls['interfaceLanguage'][1].currentData()
        self.stop_tts_preview()
        message = str(error or 'GPT TTS audio playback failed')
        base, sep, status = message.partition(' (HTTP ')
        QMessageBox.critical(self, _tr('GPT TTS 试听失败', language),
                             _tr(base, language) + (sep + status if sep else ''))

    def stop_tts_preview(self):
        self._tts_preview_generation += 1
        request_id = self._edge_preview_request_id
        self._edge_preview_request_id = None
        if request_id:
            cancel_edge_tts_audio(request_id)
        reply = self._gpt_tts_reply
        self._gpt_tts_reply = None
        if reply is not None:
            reply.abort()
            reply.deleteLater()
        timer = self._tts_preview_timer
        self._tts_preview_timer = None
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        page = self._tts_preview_page
        self._tts_preview_page = None
        if page is not None:
            page.runJavaScript('globalThis.__LINGKUMA_CALIBRE_EDGE_TTS__?.stop();')
            page.runJavaScript('globalThis.__lkEdgePreviewAudio?.pause();')
            page.runJavaScript('globalThis.__lkGptPreviewAudio?.pause();')
            page.deleteLater()
        speech = getattr(self, '_local_tts', None)
        if speech is not None:
            speech.stop()

    def done(self, result):
        self.stop_tts_preview()
        super().done(result)

    def webdav_test(self):
        try:
            config = self._current_webdav()
            directory_url = _webdav_directory_url(config)
            headers = _webdav_headers(config)
            headers.update({'Depth': '0', 'Content-Type': 'application/xml; charset=utf-8'})
            body = b'<?xml version="1.0"?><propfind xmlns="DAV:"><prop><resourcetype/></prop></propfind>'
            request = urllib.request.Request(directory_url, data=body,
                                             method='PROPFIND', headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                confirmed = status == 207 and _webdav_collection_confirmed(response, directory_url)
            if not confirmed:
                raise ValueError(_tr('WebDAV 目录未返回有效响应（HTTP {status}）。', self.controls['interfaceLanguage'][1].currentData()).format(status=status))
            QMessageBox.information(self, 'WebDAV', _tr('服务器可以访问（HTTP {status}）。', self.controls['interfaceLanguage'][1].currentData()).format(status=status))
        except Exception as error: QMessageBox.critical(self, _tr('WebDAV 连接失败', self.controls['interfaceLanguage'][1].currentData()), _webdav_error_text(error, self.controls['interfaceLanguage'][1].currentData()))

    def webdav_upload(self):
        try:
            config = self._current_webdav()
            data = json.dumps(self.state.export_learning_data(), ensure_ascii=False, indent=2).encode('utf-8')
            status, _ = _webdav_request(config, 'PUT', data, timeout=60)
            if status not in {200, 201, 204}:
                raise ValueError(_tr('WebDAV 上传未确认成功（HTTP {status}）。', self.controls['interfaceLanguage'][1].currentData()).format(status=status))
            QMessageBox.information(self, _tr('上传完成', self.controls['interfaceLanguage'][1].currentData()), _tr('WebDAV 返回 HTTP {status}。', self.controls['interfaceLanguage'][1].currentData()).format(status=status))
        except Exception as error: QMessageBox.critical(self, _tr('上传失败', self.controls['interfaceLanguage'][1].currentData()), _webdav_error_text(error, self.controls['interfaceLanguage'][1].currentData()))

    def webdav_download(self, merge=True):
        if not merge and QMessageBox.question(self, _tr('覆盖确认', self.controls['interfaceLanguage'][1].currentData()), _tr('下载并替换会覆盖本地设置和词库，是否继续？', self.controls['interfaceLanguage'][1].currentData())) != QMessageBox.StandardButton.Yes: return
        try:
            config = self._current_webdav()
            status, data = _webdav_request(config, 'GET', timeout=60)
            if status != 200:
                raise ValueError(_tr('WebDAV 下载未确认成功（HTTP {status}）。', self.controls['interfaceLanguage'][1].currentData()).format(status=status))
            payload = json.loads(data.decode('utf-8'))
            count = self.state.import_webdav_learning_data(payload, merge=merge)
            self.load_controls(); self.refresh_vocabulary(); self.refresh_statistics()
            if callable(self.on_saved):
                self.on_saved()
            QMessageBox.information(self, _tr('下载完成', self.controls['interfaceLanguage'][1].currentData()), _tr('已处理 {count} 条词汇记录。', self.controls['interfaceLanguage'][1].currentData()).format(count=count))
        except Exception as error: QMessageBox.critical(self, _tr('下载失败', self.controls['interfaceLanguage'][1].currentData()), _webdav_error_text(error, self.controls['interfaceLanguage'][1].currentData()))


class ConfigWidget(QWidget):
    """Small Calibre Preferences→Plugins bridge to the full native dialog."""
    def __init__(self, on_saved=None):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel('LingKuma 使用独立的完整原生设置窗口。点击下面的按钮进行配置。')
        label.setWordWrap(True)
        button = QPushButton('打开 LingKuma 完整设置')
        button.clicked.connect(lambda: SettingsDialog(self, on_saved=on_saved).exec())
        layout.addWidget(label); layout.addWidget(button); layout.addStretch(1)
        _localize_static_widgets(self)

    def save_settings(self):
        get_state().save()
