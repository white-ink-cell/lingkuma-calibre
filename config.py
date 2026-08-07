# -*- coding: utf-8 -*-
"""Native calibre settings, vocabulary and data-management UI."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from calibre.utils.config import config_dir
from calibre.utils.localization import get_lang
from qt.core import (
    QAbstractItemView,
    QCheckBox,
    QColor,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)

from calibre_plugins.lingkuma_calibre.compat import calibre_viewer_preferences
from calibre_plugins.lingkuma_calibre.state import StateStore, normalize_word
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


def _webdav_url(config):
    base = str(config.get('url') or '').strip()
    if not base:
        raise ValueError('请先填写 WebDAV 地址')
    filename = str(config.get('filename') or 'lingkuma-calibre-backup.json').strip()
    if base.lower().endswith('.json'):
        return base
    return base.rstrip('/') + '/' + urllib.parse.quote(filename)


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
    request = urllib.request.Request(url, data=data, method=method, headers=_webdav_headers(config, include_json=data is not None))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()



# Calibre adapter UI localization.  This is intentionally isolated from the
# reader/runtime code: it only changes labels shown by the native Qt settings
# windows.  Chinese Calibre stays Chinese; other UI languages fall back to
# English so the port is usable outside a Chinese desktop.
_UI_EN = {
    '书页设置': 'Page appearance', '保存': 'Save', '应用': 'Apply', '选择颜色': 'Choose color',
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
    '刷新': 'Refresh', '单词': 'Word', '状态': 'Status', '中文释义': 'Translations', '标签': 'Tags', '例句数': 'Examples', '保存表格修改': 'Save table changes', '删除所选词': 'Delete selected words', '导入已知单词': 'Import known words',
    'LingKuma 阅读器': 'LingKuma Reader', '自定义阅读主题': 'Custom reader theme', '自定义字体名称': 'Custom font family', '例如 Georgia / Microsoft YaHei': 'e.g. Georgia / Microsoft YaHei',
    '自定义页边距与颜色': 'Custom margins & colors', '上边距': 'Top margin', '右边距': 'Right margin', '下边距': 'Bottom margin', '左边距': 'Left margin', '页面背景色': 'Page background', '阅读行为': 'Reading behavior',
    '记住每本书阅读位置': 'Remember reading position per book', '自动将其他格式转换为 EPUB': 'Automatically convert other formats to EPUB',
    '阅读窗口工具栏新增“书页设置”（Ctrl+Shift+P），可以在读书时直接修改字体、正文宽度、页边距和页面颜色并立即应用。LingKuma Reader 是独立窗口，因此不会弹出 Calibre 原生 ebook-viewer 的设置面板。': 'The reader toolbar includes “Page appearance” (Ctrl+Shift+P), which changes font, text width, margins and page colors immediately. LingKuma Reader is a separate window, so Calibre’s native ebook-viewer settings panel is not opened.',
    '基于开源项目 LingKuma 1.1.0，将原有高亮、查词弹窗、AI 中文释义、整句翻译、词库、例句与 TTS 代码复用于 Calibre 桌面环境。': 'Based on the open-source LingKuma 1.1.0 project, reusing its highlighting, word tooltip, AI translation, sentence translation, vocabulary, examples and TTS in the Calibre desktop environment.',
    '本移植版使用独立适配层提供 Chrome storage/runtime 接口；上游 LingKuma 代码和许可证保留在插件包内。': 'This port provides Chrome storage/runtime compatibility through a separate adapter layer; upstream LingKuma code and licenses remain bundled unchanged.',
    'LingKuma 使用独立的完整原生设置窗口。点击下面的按钮进行配置。': 'LingKuma uses a separate full native settings window. Click the button below to configure it.', '打开 LingKuma 完整设置': 'Open LingKuma settings',
}


def _ui_language_mode() -> str:
    """Return adapter-owned settings UI language: zh or en.

    The reader/upstream UI is intentionally untouched. Manual override is stored
    in state.json; auto follows Calibre's interface language.
    """
    try:
        mode = str(get_state().storage.get('interfaceLanguage') or 'auto').strip().lower()
    except Exception:
        mode = 'auto'
    if mode in {'zh', 'zh-cn', 'zh_cn', 'chinese'}:
        return 'zh'
    if mode in {'en', 'english'}:
        return 'en'
    try:
        return 'zh' if str(get_lang() or '').lower().replace('-', '_').startswith('zh') else 'en'
    except Exception:
        return 'en'


def _ui_is_chinese() -> bool:
    return _ui_language_mode() == 'zh'


def _tr(text: str) -> str:
    return text if _ui_is_chinese() else _UI_EN.get(text, text)


def _localize_static_widgets(root) -> None:
    """Translate only adapter-owned Qt labels; never touches reader/upstream state."""
    if _ui_is_chinese():
        return
    root.setWindowTitle(_tr(root.windowTitle())) if hasattr(root, 'windowTitle') else None
    for widget in root.findChildren(QWidget):
        if isinstance(widget, QLabel):
            widget.setText(_tr(widget.text()))
        elif isinstance(widget, QGroupBox):
            widget.setTitle(_tr(widget.title()))
        elif isinstance(widget, QPushButton):
            widget.setText(_tr(widget.text()))
        elif isinstance(widget, QCheckBox):
            widget.setText(_tr(widget.text()))
        elif isinstance(widget, QLineEdit):
            widget.setPlaceholderText(_tr(widget.placeholderText()))
        elif isinstance(widget, QPlainTextEdit):
            widget.setPlaceholderText(_tr(widget.placeholderText()))
        elif isinstance(widget, QComboBox):
            for index in range(widget.count()):
                widget.setItemText(index, _tr(widget.itemText(index)))
        elif isinstance(widget, QListWidget):
            for index in range(widget.count()):
                item = widget.item(index)
                item.setText(_tr(item.text()))
        elif isinstance(widget, QTableWidget):
            for index in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(index)
                if item:
                    item.setText(_tr(item.text()))


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
        color = QColorDialog.getColor(initial, self, '选择颜色')
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
                raise ValueError(f'{key} 不是有效颜色')
        self.state.storage_set(values)
        print(f'[LingKuma calibre {VERSION_STR}] page appearance saved:', values)
        if callable(self.on_applied):
            self.on_applied(dict(values))

    def apply_safe(self):
        try:
            self.apply()
        except Exception as error:
            QMessageBox.critical(self, '无法应用书页设置', str(error))

    def save_and_close(self):
        try:
            self.apply(); self.accept()
        except Exception as error:
            QMessageBox.critical(self, '无法保存书页设置', str(error))


class SettingsDialog(QDialog):
    def __init__(self, parent=None, on_saved=None, initial_page=0):
        super().__init__(parent)
        self.state = get_state()
        self.on_saved = on_saved
        self.controls = {}
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
            ('阅读器', self._page_reader),
            ('关于', self._page_about),
        ]
        for label, builder in pages:
            self.nav.addItem(label)
            self.stack.addWidget(self._scroll_page(label, builder))
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(max(0, min(initial_page, len(pages) - 1)))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存并应用')
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.load_controls()
        _localize_static_widgets(self)

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

    def _multiline(self, form, key, label, placeholder=''):
        widget = QPlainTextEdit()
        widget.setPlaceholderText(placeholder)
        widget.setMinimumHeight(100)
        self.controls[key] = ('multiline', widget)
        form.addRow(label, widget)
        return widget

    def _combo(self, form, key, label, options):
        widget = QComboBox()
        for text, value in options:
            widget.addItem(text, value)
        self.controls[key] = ('combo', widget)
        form.addRow(label, widget)
        return widget

    def _language_combo(self, form, key, label):
        widget = QComboBox()
        widget.setEditable(True)
        options = [
            ('简体中文 / Simplified Chinese', 'zh-CN'),
            ('繁體中文 / Traditional Chinese', 'zh-TW'),
            ('English', 'en'), ('Deutsch', 'de'), ('Français', 'fr'),
            ('Español', 'es'), ('日本語', 'ja'), ('한국어', 'ko'),
            ('Русский', 'ru'), ('Italiano', 'it'), ('Português', 'pt'),
        ]
        for text, value in options:
            widget.addItem(text, value)
        widget.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.controls[key] = ('lang_combo', widget)
        form.addRow(label, widget)
        return widget

    def _int(self, form, key, label, low, high, suffix=''):
        widget = QSpinBox()
        widget.setRange(low, high)
        widget.setSuffix(suffix)
        self.controls[key] = ('int', widget)
        form.addRow(label, widget)
        return widget

    def _float(self, form, key, label, low, high, step=.1):
        widget = QDoubleSpinBox()
        widget.setRange(low, high)
        widget.setSingleStep(step)
        widget.setDecimals(2)
        self.controls[key] = ('float', widget)
        form.addRow(label, widget)
        return widget

    def _page_basic(self, layout):
        form = self._group(layout, '基础设置')
        self._combo(form, 'interfaceLanguage', '界面语言', [('自动（跟随 Calibre）', 'auto'), ('中文', 'zh'), ('English', 'en')])
        lang_note = QLabel('保存后重新打开设置窗口生效')
        lang_note.setWordWrap(True); lang_note.setObjectName('muted'); layout.addWidget(lang_note)
        self._bool(form, 'enablePlugin', '单词高亮（总开关）', 'LingKuma 原版总开关：关闭后高亮、查词和整句翻译都会停止')
        self._bool(form, 'wordHighlightFloatingButtonEnabled', 'Kuma 小按钮', '在阅读页面显示开关和明暗按钮')
        self._bool(form, 'highlightAlphabeticEnabled', '英文高亮')
        self._bool(form, 'highlightChineseEnabled', '中文高亮')
        self._bool(form, 'highlightJapaneseEnabled', '日语高亮')
        self._bool(form, 'highlightKoreanEnabled', '韩语高亮')
        self._bool(form, 'autoDetectJapaneseKanji', '自动识别日语汉字')
        self._bool(form, 'useKuromojiTokenizer', '日语 Kuromoji 分词（实验）')
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
        self._combo(form, 'wordExplosionTriggerMode', '触发方式', [('点击单词', 'click'), ('双击', 'dblclick'), ('选择文字', 'selection')])
        self._combo(form, 'wordExplosionPositionMode', '面板位置', [('自动', 'auto'), ('上方', 'top'), ('下方', 'bottom')])
        self._combo(form, 'wordExplosionWordsLayout', '单词排列', [('一列', 'single-column'), ('两列', 'double-column'), ('三列', 'triple-column')])
        self._combo(form, 'wordExplosionTranslationCount', '每个词显示释义', [('全部', 'all'), ('1 条', '1'), ('2 条', '2')])
        self._int(form, 'explosionSentenceTranslationCount', '整句译文数量', 1, 5)
        self._int(form, 'wordExplosionFontSize', '字号', 10, 32, ' px')
        self._int(form, 'wordExplosionMaxWidth', '最大宽度', 320, 1600, ' px')
        self._bool(form, 'wordExplosionPreferUp', '优先显示在上方')
        self._bool(form, 'wordExplosionHighlightSentence', '高亮原句')
        self._bool(form, 'showExplosionSentence', '在面板中显示英文原句')
        line = self._group(layout, '句子标记')
        self._text(line, 'wordExplosionHighlightColor', '句子高亮颜色', placeholder='#955FBD40')
        self._bool(line, 'wordExplosionUnderlineEnabled', '显示下划线')
        self._combo(line, 'wordExplosionUnderlineStyle', '下划线样式', [('实线', 'solid'), ('虚线', 'dashed'), ('点线', 'dotted')])
        self._text(line, 'wordExplosionUnderlineColor', '下划线颜色', placeholder='#955FBD80')
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
        self._bool(form, 'selectionPopupPreferDown', '选区弹窗优先向下显示')
        self._int(form, 'tooltipGap', '单词与弹窗间距', -20, 80, ' px')
        self._int(form, 'selectionPopupGap', '选词弹窗间距', 0, 80, ' px')
        visual = self._group(layout, '外观')
        self._combo(visual, 'tooltipThemeMode', '主题', [('自动', 'auto'), ('浅色', 'light'), ('深色', 'dark')])
        self._bool(visual, 'tooltipBackground.enabled', '图案背景')
        self._bool(visual, 'liquidGlassEnabled', '液态玻璃效果')
        self._bool(visual, 'analysisGlassEnabled', '分析面板玻璃效果')
        self._combo(visual, 'glassEffectType', '玻璃类型', [('关闭', 'none'), ('轻度', 'light'), ('完整', 'full')])
        capsules = self._group(layout, '自定义胶囊')
        self._multiline(capsules, 'customCapsules', 'JSON', '[{"label":"例子","prompt":"……"}]')
        restore = QPushButton('恢复被缩小的弹窗')
        restore.clicked.connect(self._restore_popup)
        layout.addWidget(restore)

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
        self._language_combo(translator, 'translationConfig.targetLanguage', '目标语言')
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
        form = self._group(layout, '详细解释使用的 OpenAI 兼容接口')
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
        advanced_prompts = self._group(layout, '高级')
        self._multiline(advanced_prompts, 'aiConfig.aiLanguageDetectionPrompt', '语言检测提示词', '留空使用 LingKuma 原始提示词')

    def _page_tts(self, layout):
        form = self._group(layout, '朗读总设置')
        self._bool(form, 'enableWordTTS', '单词朗读')
        self._bool(form, 'enableSentenceTTS', '句子朗读')
        self._bool(form, 'sentenceTTSAutoDetectLanguage', '句子朗读自动识别语言')
        providers = [('系统本地语音', 'local'), ('Edge TTS', 'edge'), ('GPT TTS', 'gpt'), ('自定义 URL 1', 'custom'), ('自定义 URL 2', 'custom2')]
        self._combo(form, 'wordTTSProvider', '单词语音渠道', providers)
        self._combo(form, 'sentenceTTSProvider', '句子语音渠道', providers)
        local = self._group(layout, '系统本地语音')
        self._text(local, 'localTTSVoice', '语音名称', placeholder='留空自动选择')
        self._float(local, 'localTTSRate', '速度', .2, 3, .1)
        self._float(local, 'localTTSPitch', '音调', 0, 2, .1)
        edge = self._group(layout, 'Edge TTS')
        self._bool(edge, 'edgeTTSAutoVoice', '自动选择语音')
        self._text(edge, 'edgeTTSVoice', '语音')
        self._float(edge, 'edgeTTSRate', '速度', -100, 100, 5)
        self._float(edge, 'edgeTTSVolume', '音量', -100, 100, 5)
        self._float(edge, 'edgeTTSPitch', '音调', -100, 100, 5)
        gpt = self._group(layout, 'GPT TTS')
        self._text(gpt, 'gptTTSBaseURL', 'API 地址')
        self._text(gpt, 'gptTTSApiKey', 'API Key', password=True)
        self._text(gpt, 'gptTTSModel', '模型')
        self._text(gpt, 'gptTTSVoice', '声音')
        self._float(gpt, 'gptTTSSpeed', '速度', .25, 4, .1)
        self._combo(gpt, 'gptTTSResponseFormat', '音频格式', [('MP3', 'mp3'), ('WAV', 'wav'), ('OPUS', 'opus'), ('AAC', 'aac'), ('FLAC', 'flac')])
        self._multiline(gpt, 'gptTTSInstructions', '朗读指令', '例如：Speak clearly and naturally.')
        custom = self._group(layout, '自定义单词音频')
        self._text(custom, 'wordAudioUrlTemplate', 'URL 模板 1', placeholder='使用 {word}、{lang}')
        self._text(custom, 'wordAudioUrlTemplate2', 'URL 模板 2', placeholder='使用 {word}、{lang}')
        self._multiline(custom, 'audioUrlNotebook', '模板说明 / 备注')

    def _page_data(self, layout):
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
        self.word_table = QTableWidget(0, 5)
        self.word_table.setHorizontalHeaderLabels(['单词', '状态', '中文释义', '标签', '例句数'])
        self.word_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.word_table.setAlternatingRowColors(True)
        self.word_table.setMinimumHeight(430)
        self.word_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.word_table)
        actions = QHBoxLayout()
        save = QPushButton('保存表格修改'); delete = QPushButton('删除所选词'); import_words = QPushButton('导入已知单词')
        actions.addWidget(save); actions.addWidget(delete); actions.addWidget(import_words); actions.addStretch(1)
        layout.addLayout(actions)
        self.word_search.textChanged.connect(self.refresh_vocabulary)
        self.word_filter.currentIndexChanged.connect(self.refresh_vocabulary)
        refresh.clicked.connect(self.refresh_vocabulary)
        save.clicked.connect(self.save_vocabulary_table)
        delete.clicked.connect(self.delete_selected_words)
        import_words.clicked.connect(lambda: self.import_backup(True))
        self.refresh_vocabulary()

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
        text = QLabel(
            f'<b>{PRODUCT} {VERSION_STR}</b><br><br>'
            '基于开源项目 LingKuma 1.1.0，将原有高亮、查词弹窗、AI 中文释义、整句翻译、词库、例句与 TTS 代码复用于 Calibre 桌面环境。<br><br>'
            '本移植版使用独立适配层提供 Chrome storage/runtime 接口；上游 LingKuma 代码和许可证保留在插件包内。'
        )
        text.setWordWrap(True); text.setOpenExternalLinks(True)
        box.addWidget(text)
        layout.addWidget(group)

    def load_controls(self):
        storage = self.state.storage
        for key, (kind, widget) in self.controls.items():
            value = _get_nested(storage, key)
            if kind == 'bool': widget.setChecked(bool(value))
            elif kind in {'text', 'multiline'}:
                text = json.dumps(value, ensure_ascii=False, indent=2) if key == 'customCapsules' and isinstance(value, list) else str(value or '')
                widget.setPlainText(text) if kind == 'multiline' else widget.setText(text)
            elif kind == 'combo':
                index = widget.findData(value)
                widget.setCurrentIndex(index if index >= 0 else 0)
            elif kind == 'lang_combo':
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    widget.setEditText(str(value or 'zh-CN'))
            elif kind == 'int': widget.setValue(int(value or 0))
            elif kind == 'float': widget.setValue(float(value or 0))

    def collect_controls(self):
        values = json.loads(json.dumps(self.state.storage, ensure_ascii=False))
        for key, (kind, widget) in self.controls.items():
            if kind == 'bool': value = widget.isChecked()
            elif kind == 'text': value = widget.text().strip()
            elif kind == 'multiline':
                value = widget.toPlainText().strip()
                if key == 'customCapsules':
                    try: value = json.loads(value or '[]')
                    except json.JSONDecodeError as error: raise ValueError(f'自定义胶囊 JSON 无效：{error}')
            elif kind == 'combo': value = widget.currentData()
            elif kind == 'lang_combo': value = str(widget.currentData() or widget.currentText() or '').strip() or 'zh-CN'
            elif kind == 'int': value = widget.value()
            else: value = widget.value()
            _set_nested(values, key, value)
        return values

    def save_and_accept(self):
        try:
            values = self.collect_controls()
            self.state.storage_set(values)
            if callable(self.on_saved): self.on_saved()
            self.accept()
        except Exception as error:
            QMessageBox.critical(self, '无法保存设置', str(error))

    def _restore_popup(self):
        self.state.storage_set({'tooltipMinimized': False})
        QMessageBox.information(self, '已恢复', '最小化状态已清除。重新点击单词后会显示完整弹窗。')

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
        rows = rows[:2000]
        self.word_table.blockSignals(True)
        self.word_table.setRowCount(len(rows))
        for row, (word, rec) in enumerate(rows):
            values = [rec.get('term') or word, str(rec.get('status', '0')), '；'.join(rec.get('translations') or []), '；'.join(rec.get('tags') or []), str(len(rec.get('sentences') or []))]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value)); item.setData(Qt.ItemDataRole.UserRole, word)
                if col in {0, 4}: item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.word_table.setItem(row, col, item)
        self.word_table.blockSignals(False)
        self.word_table.resizeColumnsToContents()

    def save_vocabulary_table(self):
        for row in range(self.word_table.rowCount()):
            word = self.word_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            rec = self.state.get_word(word)
            if not rec: continue
            status = self.word_table.item(row, 1).text().strip()
            translations = [x.strip() for x in self.word_table.item(row, 2).text().replace(';', '；').split('；') if x.strip()]
            tags = [x.strip() for x in self.word_table.item(row, 3).text().replace(';', '；').split('；') if x.strip()]
            self.state.update_language(word, {'translations': translations, 'tags': tags})
            self.state.update_status(word, status)
        QMessageBox.information(self, '保存完成', '词库修改已经保存。')

    def delete_selected_words(self):
        rows = sorted({index.row() for index in self.word_table.selectionModel().selectedRows()}, reverse=True)
        if not rows: return
        if QMessageBox.question(self, '确认删除', f'删除所选 {len(rows)} 个单词？') != QMessageBox.StandardButton.Yes: return
        for row in rows:
            word = self.word_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.state.delete_word(word)
        self.refresh_vocabulary()

    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, '导出 LingKuma 备份', 'lingkuma-calibre-backup.json', 'JSON (*.json)')
        if not path: return
        Path(path).write_text(json.dumps(self.state.export_data(), ensure_ascii=False, indent=2), encoding='utf-8')
        QMessageBox.information(self, '导出完成', path)

    def import_backup(self, merge=True):
        path, _ = QFileDialog.getOpenFileName(self, '导入 LingKuma 数据', '', 'LingKuma 数据 (*.json *.txt *.csv);;所有文件 (*)')
        if not path: return
        try:
            count = self.state.import_data(Path(path).read_text(encoding='utf-8-sig'), merge=merge)
            self.load_controls(); self.refresh_vocabulary()
            QMessageBox.information(self, '导入完成', f'已处理 {count} 条词汇记录。')
        except Exception as error:
            QMessageBox.critical(self, '导入失败', str(error))

    def clear_vocabulary(self):
        if QMessageBox.question(self, '确认清空', '这会删除全部本地词汇记录，是否继续？') == QMessageBox.StandardButton.Yes:
            self.state.clear_words(); self.refresh_vocabulary()

    def _current_webdav(self):
        values = self.collect_controls()
        return _get_nested(values, 'webdavConfig', {})

    def webdav_test(self):
        try:
            config = self._current_webdav()
            request = urllib.request.Request(_webdav_url(config), method='HEAD', headers=_webdav_headers(config))
            try:
                with urllib.request.urlopen(request, timeout=30) as response: status = response.status
            except urllib.error.HTTPError as error:
                if error.code in {404, 405}: status = error.code
                else: raise
            QMessageBox.information(self, 'WebDAV', f'服务器可以访问（HTTP {status}）。')
        except Exception as error: QMessageBox.critical(self, 'WebDAV 连接失败', str(error))

    def webdav_upload(self):
        try:
            config = self._current_webdav()
            data = json.dumps(self.state.export_data(), ensure_ascii=False, indent=2).encode('utf-8')
            status, _ = _webdav_request(config, 'PUT', data)
            QMessageBox.information(self, '上传完成', f'WebDAV 返回 HTTP {status}。')
        except Exception as error: QMessageBox.critical(self, '上传失败', str(error))

    def webdav_download(self, merge=True):
        if not merge and QMessageBox.question(self, '覆盖确认', '下载并替换会覆盖本地设置和词库，是否继续？') != QMessageBox.StandardButton.Yes: return
        try:
            config = self._current_webdav()
            _status, data = _webdav_request(config, 'GET')
            count = self.state.import_data(json.loads(data.decode('utf-8')), merge=merge)
            self.load_controls(); self.refresh_vocabulary()
            QMessageBox.information(self, '下载完成', f'已处理 {count} 条词汇记录。')
        except Exception as error: QMessageBox.critical(self, '下载失败', str(error))


class ConfigWidget(QWidget):
    """Small Calibre Preferences→Plugins bridge to the full native dialog."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel('LingKuma 使用独立的完整原生设置窗口。点击下面的按钮进行配置。')
        label.setWordWrap(True)
        button = QPushButton('打开 LingKuma 完整设置')
        button.clicked.connect(lambda: SettingsDialog(self).exec())
        layout.addWidget(label); layout.addWidget(button); layout.addStretch(1)
        _localize_static_widgets(self)

    def save_settings(self):
        get_state().save()
