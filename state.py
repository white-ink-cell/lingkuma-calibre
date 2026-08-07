# -*- coding: utf-8 -*-
"""Persistent LingKuma state and browser-background API for calibre.

The upstream JavaScript remains in resources/upstream.  This module replaces
Chrome storage, IndexedDB and the extension service worker with a small,
thread-safe JSON store.
"""

from __future__ import annotations

import base64
import hashlib
import copy
import html
import json
import os
import random
import re
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from calibre_plugins.lingkuma_calibre.version import USER_AGENT, VERSION_STR

SCHEMA_VERSION = 1

DEFAULT_TTS_CONFIG: dict[str, Any] = {
    'wordTTSProvider': 'local',
    'sentenceTTSProvider': 'local',
    'localTTSVoice': '',
    'localTTSRate': 1,
    'localTTSPitch': 1,
    'edgeTTSAutoVoice': True,
    'edgeTTSVoice': '',
    'edgeTTSRate': 0,
    'edgeTTSVolume': 0,
    'edgeTTSPitch': 0,
    'wordAudioUrlTemplate': '',
    'wordAudioUrlTemplate2': '',
    'audioUrlNotebook': '',
}

TTS_CONFIG_KEYS = tuple(DEFAULT_TTS_CONFIG)
GPT_TTS_KEYS = (
    'gptTTSBaseURL', 'gptTTSApiKey', 'gptTTSModel', 'gptTTSVoice',
    'gptTTSResponseFormat', 'gptTTSSpeed', 'gptTTSInstructions',
)

DEFAULT_STORAGE: dict[str, Any] = {
    'interfaceLanguage': 'auto',
    'enablePlugin': True,
    'wordHighlightFloatingButtonEnabled': True,
    'wordHighlightFloatingButtonScope': 'global',
    'wordHighlightFloatingButtonPosition': None,
    'highlightPageThemeOverrides': {},
    'wordHighlightPageTabOverrides': {},
    'pluginBlacklistWebsites': '',
    'highlightAlphabeticEnabled': True,
    'highlightChineseEnabled': False,
    'highlightJapaneseEnabled': False,
    'highlightKoreanEnabled': False,
    'autoDetectJapaneseKanji': True,
    'useKuromojiTokenizer': False,
    'autoLoadKuromojiForJapanese': False,
    'autoRequestAITranslations': True,
    'autoRequestAITranslations2': True,
    'autoAddAITranslations': False,
    'autoAddAITranslationsFromUnknown': True,
    'autoAddExampleSentences': False,
    'autoAddSentencesLimit': 1,
    'clickOnlyTooltip': True,
    'autoExpandTooltip': False,
    'autoCloseTooltip': False,
    'autoRefreshTooltip': False,
    'defaultExpandTooltip': False,
    'defaultExpandSententsTooltip': True,
    'defaultExpandCapsule': True,
    'preferPopupAbove': False,
    'selectionPopupPreferDown': False,
    'tooltipGap': 0,
    'selectionPopupGap': 10,
    'tooltipMinimized': False,
    'explosionPriorityMode': False,
    'wordQueryKey': 'q',
    'copySentenceKey': 'w',
    'analysisWindowKey': 'e',
    'sidePanelKey': 'r',
    'sentenceExplosionKey': 't',
    'wordStatusKeys': {
        '0': '`', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5',
        'toggle': ' ', 'addAITranslation': 'tab', 'closeTooltip': 'capslock',
    },
    'sidebarWidth': 400,
    'wordExplosionEnabled': True,
    'wordExplosionTriggerMode': 'click',
    'wordExplosionPositionMode': 'auto',
    'wordExplosionFontSize': 14,
    'wordExplosionMaxWidth': 772,
    'wordExplosionPreferUp': True,
    'wordExplosionLayout': 'vertical',
    'wordExplosionWordsLayout': 'triple-column',
    'wordExplosionTranslationCount': 'all',
    'explosionSentenceTranslationCount': 1,
    'wordExplosionHighlightSentence': True,
    'wordExplosionHighlightColor': '#955FBD40',
    'wordExplosionUnderlineEnabled': False,
    'wordExplosionUnderlineStyle': 'solid',
    'wordExplosionUnderlinePosition': 'bottom',
    'wordExplosionUnderlineColor': '#955FBD80',
    'wordExplosionUnderlineThickness': 3,
    'showExplosionSentence': False,
    'highlightSpeed': 100,
    'explosionHighlightSpeed': 100,
    'sentenceNavigatorEnabled': True,
    'liquidGlassEnabled': False,
    'analysisGlassEnabled': False,
    'tooltipThemeMode': 'auto',
    'tooltipBackground': {'enabled': True, 'useCustom': False, 'defaultType': 'svg'},
    'enableWaifu': False,
    'readingRuler': False,
    'sidePanelBtn': False,
    'useOrionTTS': False,
    'cloudConfig': {'cloudDbEnabled': False, 'cloudDualWrite': False},
    'cloudDbEnabled': False,
    'cloudDualWrite': False,
    'cloudSelfHosted': False,
    'cloudServerUrl': '',
    'webdavConfig': {'url': '', 'username': '', 'password': '', 'filename': 'lingkuma-calibre-backup.json'},
    'settingsPanelTheme': 'light',
    'ttsConfig': copy.deepcopy(DEFAULT_TTS_CONFIG),
    'wordTTSProvider': 'local',
    'sentenceTTSProvider': 'local',
    'enableWordTTS': True,
    'enableSentenceTTS': True,
    'sentenceTTSAutoDetectLanguage': True,
    'enableAutoWordTTS': False,
    'localTTSVoice': '',
    'localTTSRate': 1,
    'localTTSPitch': 1,
    'edgeTTSAutoVoice': True,
    'edgeTTSVoice': '',
    'edgeTTSRate': 0,
    'edgeTTSVolume': 0,
    'edgeTTSPitch': 0,
    'gptTTSBaseURL': '',
    'gptTTSApiKey': '',
    'gptTTSModel': 'gpt-4o-mini-tts',
    'gptTTSVoice': 'alloy',
    'gptTTSResponseFormat': 'mp3',
    'gptTTSSpeed': 1,
    'gptTTSInstructions': '',
    'wordAudioUrlTemplate': '',
    'wordAudioUrlTemplate2': '',
    'devicePixelRatio': 1,
    'glassEffectType': 'rough',
    'customCapsules': [],
    'epubSoftHyphenCleanup': True,
    'epubHyphenRepair': True,
    'readerPreserveBookStyles': True,
    'readerLayoutMode': 'calibre',
    'calibreFastAIEnabled': True,
    'calibreBatchWordTranslations': True,
    'calibreBatchMaxWords': 30,
    'calibreAIConcurrency': 3,
    'translationConfig': {
        'provider': 'google-web',
        'targetLanguage': 'zh-CN',
        'fallbackToAI': True,
        'timeoutSeconds': 15,
        'googleCloudApiKey': '',
        'microsoftKey': '',
        'microsoftRegion': '',
        'microsoftEndpoint': 'https://api.cognitive.microsofttranslator.com',
    },
    'readerTheme': 'original',
    'readerFontSize': 20,
    'readerLineHeight': 1.65,
    'readerContentWidth': 860,
    'readerFontFamily': 'book',
    'readerCustomFontFamily': '',
    'readerMarginTop': 40,
    'readerMarginRight': 60,
    'readerMarginBottom': 40,
    'readerMarginLeft': 60,
    'readerBackgroundColor': '#f8f0dc',
    'readerTextColor': '#4a372b',
    'readerLinkColor': '#6c4d2e',
    'readerAutoConvert': True,
    'readerRememberPosition': True,
    'aiConfig': {
        'aiChannel': 'diy',
        'apiBaseURL': '',
        'apiModel': '',
        'apiKey': '',
        'apiTemperature': 1,
        'aiLanguageDetectionPrompt': '',
        'gptTTSBaseURL': '',
        'gptTTSApiKey': '',
        'gptTTSModel': 'gpt-4o-mini-tts',
        'gptTTSVoice': 'alloy',
        'gptTTSResponseFormat': 'mp3',
        'gptTTSSpeed': 1,
        'gptTTSInstructions': '',
    },
}

DEFAULT_AI_KEYS_B64 = (
    'YmFlMjdlNDQyODgyNGZlOGExNjFlZTc0ZDYyZWIzM2YubW5uOEVoNEplVG9kcmY0bg==',
    'ODUwZTNlMmEzYmVkNDg2N2I2MGIzZWI2NmUyMDAyNjMuYWhSOGhxYkJvaG1wRG81eg==',
    'MGZmMDYwNTZlODhhNGNlMmI1ZTA4NzIxZTNjNGNkNmQuMnV0djhRaDVlZU1jcnJHcA==',
    'YzZhYzJlYjllMTJiNGJiNWEwZDczYzliNzZkODEzNzAuRnpITlNoZnFteEx4MHV4WA==',
    'ZjAwMmZlNTUzNGQ4NDYxNWEyM2VjOTlhODM1ZDZiM2UuR2h1NVRrSmVDS0xiSGhMZA==',
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def deep_merge(default: Any, value: Any) -> Any:
    if isinstance(default, dict) and isinstance(value, dict):
        out = {k: deep_copy(v) for k, v in default.items()}
        for key, val in value.items():
            out[key] = deep_merge(out[key], val) if key in out else deep_copy(val)
        return out
    return deep_copy(value)


def normalize_word(value: Any) -> str:
    word = str(value or '').strip()
    word = re.sub(r"^[\s.,;:!?()\[\]{}“”‘’\"']+|[\s.,;:!?()\[\]{}“”‘’\"']+$", '', word)
    return re.sub(r'\s+', ' ', word).lower()


_CALIBRE_SENTENCE_REFRESH_WORDS = frozenset({
    'a', 'an', 'the', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'of', 'in', 'on', 'at', 'for', 'to', 'from', 'with', 'by', 'as',
    'and', 'or', 'but', 'if', 'that', 'this', 'these', 'those',
    'have', 'has', 'had', 'do', 'does', 'did', 'not',
    'i', 'me', 'my', 'mine', 'you', 'your', 'yours', 'he', 'him', 'his',
    'she', 'her', 'hers', 'it', 'its', 'we', 'us', 'our', 'ours',
    'they', 'them', 'their', 'theirs', 'who', 'whom', 'whose', 'which',
    'what', 'when', 'where', 'why', 'how',
})


def _looks_like_legacy_sentence_translation(word: str, values: Any) -> bool:
    """Detect display values polluted by old AI prompt/neighbor-word leakage.

    This is intentionally non-destructive: callers use it only to decide whether
    a fresh display translation is needed.  The stored vocabulary record is left
    untouched.
    """
    if not isinstance(values, list) or not values:
        return True
    markers = (
        '中文翻译', '翻译进行中', '暂无翻译', '翻译失败', '判断句子',
        '完整短语', '独立单词', '禁止事项', '情况一', '情况二',
    )
    escaped = re.escape(word)
    for raw in values:
        text = str(raw or '').strip()
        if not text:
            return True
        if '\n' in text or any(marker in text for marker in markers):
            return True
        if word and re.search(rf'(^|[\s,，;；]){escaped}\s*[:：]', text, flags=re.I):
            return True
    return False


def normalize_status(value: Any) -> str:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = 0
    return str(max(0, min(5, number)))


def normalize_sentence(item: Any) -> dict[str, str] | None:
    if isinstance(item, str):
        sentence = item.strip()
        return {'sentence': sentence, 'translation': '', 'url': ''} if sentence else None
    if isinstance(item, dict):
        sentence = str(item.get('sentence') or '').strip()
        if not sentence:
            return None
        return {
            'sentence': sentence,
            'translation': str(item.get('translation') or ''),
            'url': str(item.get('url') or ''),
        }
    return None


def fresh_record(word: str, original: str | None = None) -> dict[str, Any]:
    now = utc_now()
    return {
        'word': word,
        'term': str(original or word),
        'status': '0',
        'language': 'auto',
        'translations': [],
        'tags': [],
        'sentences': [],
        'statusHistory': {},
        'isCustom': False,
        'createdAt': now,
        'updatedAt': now,
    }


def normalize_record(word: str, raw: Any = None) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    rec = fresh_record(word, raw.get('term') or raw.get('word') or word)
    rec.update(deep_copy(raw))
    rec['word'] = word
    rec['term'] = str(rec.get('term') or raw.get('word') or word)
    rec['status'] = normalize_status(rec.get('status'))
    rec['language'] = str(rec.get('language') or 'auto')
    rec['translations'] = [str(x) for x in rec.get('translations', []) if x] if isinstance(rec.get('translations'), list) else []
    rec['tags'] = [str(x) for x in rec.get('tags', []) if x] if isinstance(rec.get('tags'), list) else []
    rec['sentences'] = [x for x in (normalize_sentence(v) for v in rec.get('sentences', [])) if x]
    rec['statusHistory'] = rec.get('statusHistory') if isinstance(rec.get('statusHistory'), dict) else {}
    rec['isCustom'] = rec.get('isCustom') is True
    rec['createdAt'] = rec.get('createdAt') or utc_now()
    rec['updatedAt'] = rec.get('updatedAt') or utc_now()
    return rec


def merge_records(local_raw: Any, remote_raw: Any, word: str) -> dict[str, Any]:
    local = normalize_record(word, local_raw)
    remote = normalize_record(word, remote_raw)
    newer = remote if remote.get('updatedAt', '') > local.get('updatedAt', '') else local
    sentences: dict[str, dict[str, str]] = {}
    for item in local['sentences'] + remote['sentences']:
        sentences[item['sentence']] = item
    merged = dict(local)
    merged.update(newer)
    merged['translations'] = list(dict.fromkeys(local['translations'] + remote['translations']))
    merged['tags'] = list(dict.fromkeys(local['tags'] + remote['tags']))
    merged['sentences'] = list(sentences.values())
    merged['statusHistory'] = {**local['statusHistory'], **remote['statusHistory']}
    merged['isCustom'] = local['isCustom'] or remote['isCustom']
    return normalize_record(word, merged)


class StateStore:
    def __init__(self, state_path: str | Path):
        self.path = Path(state_path)
        self.lock = threading.RLock()
        self.storage = deep_copy(DEFAULT_STORAGE)
        self.words: dict[str, dict[str, Any]] = {}
        self.progress: dict[str, dict[str, Any]] = {}
        self.loaded = False
        self.recovery_notice = ''
        self._ai_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._ai_cache_lock = threading.RLock()
        self._ai_semaphore = threading.BoundedSemaphore(3)
        self._translation_cache: dict[str, tuple[float, str]] = {}
        self._translation_cache_lock = threading.RLock()
        self.load()

    def _synchronize_config_locked(self, explicit_storage: dict[str, Any] | None = None) -> None:
        """Keep upstream nested config objects and native flat controls identical.

        LingKuma's original TTS runtime reads ``ttsConfig`` and GPT speech
        fields from ``aiConfig``.  The native calibre settings dialog uses
        flat keys for simpler widgets.  Supporting both shapes prevents a
        provider change in one surface from being invisible to the other.
        """
        explicit_storage = explicit_storage if isinstance(explicit_storage, dict) else {}

        nested_tts = deep_merge(DEFAULT_TTS_CONFIG, self.storage.get('ttsConfig') or {})
        explicit_nested_tts = explicit_storage.get('ttsConfig') if isinstance(explicit_storage.get('ttsConfig'), dict) else {}
        for key in TTS_CONFIG_KEYS:
            if key in explicit_storage:
                nested_tts[key] = deep_copy(explicit_storage[key])
            elif key in explicit_nested_tts:
                nested_tts[key] = deep_copy(explicit_nested_tts[key])
            elif key in self.storage:
                nested_tts[key] = deep_copy(self.storage[key])
            self.storage[key] = deep_copy(nested_tts.get(key, DEFAULT_TTS_CONFIG[key]))
        self.storage['ttsConfig'] = nested_tts

        ai = deep_merge(DEFAULT_STORAGE['aiConfig'], self.storage.get('aiConfig') or {})
        explicit_ai = explicit_storage.get('aiConfig') if isinstance(explicit_storage.get('aiConfig'), dict) else {}
        for key in GPT_TTS_KEYS:
            if key in explicit_storage:
                ai[key] = deep_copy(explicit_storage[key])
            elif key in explicit_ai:
                ai[key] = deep_copy(explicit_ai[key])
            elif key in self.storage:
                ai[key] = deep_copy(self.storage[key])
            self.storage[key] = deep_copy(ai.get(key, DEFAULT_STORAGE['aiConfig'][key]))
        self.storage['aiConfig'] = ai

    def _load_payload_locked(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            parsed = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(parsed, dict):
                raise ValueError('state root must be an object')
            return parsed
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = self.path.with_name(f'{self.path.name}.corrupt-{stamp}.bak')
            try:
                shutil.copy2(self.path, backup)
            except Exception as backup_error:
                raise RuntimeError(
                    f'LingKuma state is unreadable and could not be preserved: {self.path}'
                ) from backup_error
            self.recovery_notice = f'Recovered unreadable state to {backup.name} ({type(error).__name__})'
            return {}

    def load(self) -> None:
        with self.lock:
            parsed = self._load_payload_locked()
            raw_storage = parsed.get('storage') if isinstance(parsed.get('storage'), dict) else {}
            self.storage = deep_merge(DEFAULT_STORAGE, raw_storage)
            self._synchronize_config_locked(raw_storage)
            # Adapter migrations must never rewrite LingKuma UI/business policy.
            # 1.1.0 records only adapter metadata; upstream settings are preserved
            # exactly as loaded (including highlight scope, theme and minimized state).
            try:
                calibre_migration = int(self.storage.get('calibreAdapterMigrationVersion') or 0)
            except (TypeError, ValueError):
                calibre_migration = 0
            if calibre_migration < 110:
                self.storage['calibreAdapterMigrationVersion'] = 110
            self.words = {}
            for key, raw in (parsed.get('words') or {}).items():
                word = normalize_word(key or (raw or {}).get('word'))
                if word:
                    self.words[word] = normalize_record(word, raw)
            self.progress = parsed.get('progress') if isinstance(parsed.get('progress'), dict) else {}
            self.loaded = True
            self._save_locked()

    def _save_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'format': 'lingkuma-calibre-state',
            'schemaVersion': SCHEMA_VERSION,
            'updatedAt': utc_now(),
            'storage': self.storage,
            'words': self.words,
            'progress': self.progress,
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        temp = self.path.with_name(
            f'{self.path.name}.tmp-{os.getpid()}-{threading.get_ident()}'
        )
        try:
            with temp.open('xb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
            # Best-effort directory sync on platforms that support opening a directory.
            # The file replacement above is already atomic; this only strengthens
            # crash durability and must not make normal Windows saves fail.
            try:
                directory_fd = os.open(str(self.path.parent), getattr(os, 'O_DIRECTORY', 0))
            except (OSError, AttributeError):
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                except OSError:
                    pass
                finally:
                    os.close(directory_fd)
        except Exception:
            try:
                temp.unlink(missing_ok=True)
            except Exception:
                pass
            raise

    def save(self) -> None:
        with self.lock:
            self._save_locked()

    def storage_get(self, keys: Any = None) -> dict[str, Any]:
        with self.lock:
            if keys is None:
                return deep_copy(self.storage)
            if isinstance(keys, str):
                return {keys: deep_copy(self.storage.get(keys))}
            if isinstance(keys, list):
                return {str(k): deep_copy(self.storage.get(str(k))) for k in keys}
            if isinstance(keys, dict):
                return {str(k): deep_copy(self.storage.get(str(k), default)) for k, default in keys.items()}
            return {}

    def storage_set(self, values: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, dict):
            return {}
        with self.lock:
            before = deep_copy(self.storage)
            for key, value in values.items():
                self.storage[str(key)] = deep_copy(value)
            self._synchronize_config_locked(values)
            changes = {}
            for key in set(before) | set(self.storage):
                old_value = before.get(key)
                new_value = self.storage.get(key)
                if old_value != new_value:
                    changes[str(key)] = {'oldValue': deep_copy(old_value), 'newValue': deep_copy(new_value)}
            self._save_locked()
            return changes

    def storage_remove(self, keys: Any) -> dict[str, Any]:
        if isinstance(keys, str):
            keys = [keys]
        with self.lock:
            before = deep_copy(self.storage)
            for raw_key in keys or []:
                key = str(raw_key)
                self.storage.pop(key, None)
                if key in TTS_CONFIG_KEYS and isinstance(self.storage.get('ttsConfig'), dict):
                    self.storage['ttsConfig'].pop(key, None)
                if key in GPT_TTS_KEYS and isinstance(self.storage.get('aiConfig'), dict):
                    self.storage['aiConfig'].pop(key, None)
                if key == 'ttsConfig':
                    for nested_key in TTS_CONFIG_KEYS:
                        self.storage.pop(nested_key, None)
                if key == 'aiConfig':
                    for nested_key in GPT_TTS_KEYS:
                        self.storage.pop(nested_key, None)
            self.storage = deep_merge(DEFAULT_STORAGE, self.storage)
            self._synchronize_config_locked({})
            changes = {}
            for key in set(before) | set(self.storage):
                if before.get(key) != self.storage.get(key):
                    changes[key] = {'oldValue': deep_copy(before.get(key)), 'newValue': deep_copy(self.storage.get(key))}
            self._save_locked()
            return changes

    def storage_clear(self) -> dict[str, Any]:
        with self.lock:
            before = deep_copy(self.storage)
            self.storage = deep_copy(DEFAULT_STORAGE)
            self._synchronize_config_locked({})
            changes = {}
            for key in set(before) | set(self.storage):
                old_value = before.get(key)
                new_value = self.storage.get(key)
                if old_value != new_value:
                    change = {'oldValue': deep_copy(old_value)}
                    if key in self.storage:
                        change['newValue'] = deep_copy(new_value)
                    changes[str(key)] = change
            self._save_locked()
            return changes

    def get_word(self, value: Any, create: bool = False) -> dict[str, Any]:
        word = normalize_word(value)
        if not word:
            return {}
        with self.lock:
            if create and word not in self.words:
                self.words[word] = fresh_record(word, str(value or word))
            return deep_copy(self.words.get(word) or {})

    def get_all_words(self) -> dict[str, dict[str, Any]]:
        with self.lock:
            return deep_copy(self.words)

    def status_map(self, values: list[Any] | None = None) -> dict[str, dict[str, Any]]:
        with self.lock:
            candidates = [normalize_word(v) for v in values] if values is not None else list(self.words)
            out = {}
            for word in candidates:
                rec = self.words.get(word)
                if rec:
                    out[word] = {'word': rec.get('term') or word, 'status': rec['status'], 'isCustom': rec['isCustom']}
            return out

    def update_status(self, value: Any, status: Any, language: Any = None, is_custom: Any = None) -> dict[str, Any]:
        word = normalize_word(value)
        if not word:
            return {}
        with self.lock:
            rec = self.words.get(word) or fresh_record(word, str(value or word))
            rec['status'] = normalize_status(status)
            if language:
                rec['language'] = str(language)
            if is_custom is not None:
                rec['isCustom'] = bool(is_custom)
            rec.setdefault('statusHistory', {})[utc_now()] = rec['status']
            rec['updatedAt'] = utc_now()
            self.words[word] = normalize_record(word, rec)
            self._save_locked()
            return deep_copy(self.words[word])

    def update_language(self, value: Any, details: Any) -> dict[str, Any]:
        word = normalize_word(value)
        if not word:
            return {}
        with self.lock:
            rec = self.words.get(word) or fresh_record(word, str(value or word))
            if isinstance(details, str):
                rec['language'] = details
            elif isinstance(details, dict):
                for key, val in details.items():
                    if key in {'word'}:
                        continue
                    rec[key] = deep_copy(val)
            rec['updatedAt'] = utc_now()
            self.words[word] = normalize_record(word, rec)
            self._save_locked()
            return deep_copy(self.words[word])

    def add_translation(self, value: Any, translation: Any) -> None:
        text = str(translation or '').strip()
        if not text:
            return
        word = normalize_word(value)
        with self.lock:
            rec = self.words.get(word) or fresh_record(word, str(value or word))
            rec.setdefault('translations', [])
            if text not in rec['translations']:
                rec['translations'].append(text)
            rec['updatedAt'] = utc_now()
            self.words[word] = normalize_record(word, rec)
            self._save_locked()

    def remove_translation(self, value: Any, translation: Any) -> None:
        word, text = normalize_word(value), str(translation or '')
        with self.lock:
            rec = self.words.get(word)
            if rec:
                rec['translations'] = [x for x in rec.get('translations', []) if x != text]
                rec['updatedAt'] = utc_now()
                self._save_locked()

    def add_tag(self, value: Any, tag: Any) -> None:
        text = str(tag or '').strip()
        if not text:
            return
        word = normalize_word(value)
        with self.lock:
            rec = self.words.get(word) or fresh_record(word, str(value or word))
            if text not in rec['tags']:
                rec['tags'].append(text)
            rec['updatedAt'] = utc_now()
            self.words[word] = normalize_record(word, rec)
            self._save_locked()

    def remove_tag(self, value: Any, tag: Any) -> None:
        word, text = normalize_word(value), str(tag or '')
        with self.lock:
            rec = self.words.get(word)
            if rec:
                rec['tags'] = [x for x in rec.get('tags', []) if x != text]
                rec['updatedAt'] = utc_now()
                self._save_locked()

    def add_sentence(self, value: Any, sentence: Any, translation: Any = '', url: Any = '') -> None:
        word = normalize_word(value)
        item = normalize_sentence({'sentence': sentence, 'translation': translation, 'url': url})
        if not word or not item:
            return
        with self.lock:
            rec = self.words.get(word) or fresh_record(word, str(value or word))
            by_text = {x['sentence']: x for x in rec.get('sentences', [])}
            by_text[item['sentence']] = item
            rec['sentences'] = list(by_text.values())
            rec['updatedAt'] = utc_now()
            self.words[word] = normalize_record(word, rec)
            self._save_locked()

    def remove_sentence(self, value: Any, sentence: Any) -> None:
        word, text = normalize_word(value), str(sentence or '')
        with self.lock:
            rec = self.words.get(word)
            if rec:
                rec['sentences'] = [x for x in rec.get('sentences', []) if x.get('sentence') != text]
                rec['updatedAt'] = utc_now()
                self._save_locked()

    def delete_word(self, value: Any) -> None:
        with self.lock:
            self.words.pop(normalize_word(value), None)
            self._save_locked()

    def clear_words(self) -> None:
        with self.lock:
            self.words = {}
            self._save_locked()

    def restore_words(self, data: Any, merge: bool = True) -> int:
        if isinstance(data, dict) and isinstance(data.get('words'), dict):
            data = data['words']
        if isinstance(data, list):
            data = {normalize_word(x.get('word') if isinstance(x, dict) else x): x for x in data}
        if not isinstance(data, dict):
            raise ValueError('未找到可导入的词汇记录')
        changed = 0
        with self.lock:
            if not merge:
                self.words = {}
            for key, raw in data.items():
                word = normalize_word(key or (raw or {}).get('word') if isinstance(raw, dict) else key)
                if not word:
                    continue
                incoming = normalize_record(word, raw if isinstance(raw, dict) else {'word': word, 'status': 5})
                self.words[word] = merge_records(self.words.get(word), incoming, word) if merge and word in self.words else incoming
                changed += 1
            self._save_locked()
        return changed

    def import_data(self, payload: Any, merge: bool = True, plain_status: int = 5) -> int:
        if isinstance(payload, str):
            text = payload.strip()
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                words = [x.strip() for x in re.split(r'[\r\n,;]+', text) if x.strip()]
                payload = {normalize_word(w): {'word': normalize_word(w), 'term': w, 'status': plain_status} for w in words}
        if isinstance(payload, dict) and isinstance(payload.get('storage'), dict):
            self.storage_set(payload['storage'])
        return self.restore_words(payload, merge=merge)

    def export_data(self) -> dict[str, Any]:
        with self.lock:
            return {
                'format': 'lingkuma-calibre-export',
                'version': 1,
                'schemaVersion': SCHEMA_VERSION,
                'exportedAt': utc_now(),
                'storage': deep_copy(self.storage),
                'words': deep_copy(self.words),
                'progress': deep_copy(self.progress),
            }

    def get_progress(self, book_key: str) -> dict[str, Any]:
        with self.lock:
            return deep_copy(self.progress.get(str(book_key)) or {})

    def set_progress(self, book_key: str, chapter: int, scroll_ratio: float = 0.0) -> None:
        with self.lock:
            self.progress[str(book_key)] = {
                'chapter': max(0, int(chapter)),
                'scrollRatio': max(0.0, min(1.0, float(scroll_ratio))),
                'updatedAt': utc_now(),
            }
            self._save_locked()

    def ai_configs(self) -> list[dict[str, Any]]:
        return [
            {
                'apiBaseURL': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                'apiModel': 'GLM-4-Flash',
                'apiKey': base64.b64decode(key).decode('utf-8'),
                'source': 'LingKuma built-in free BigModel pool',
            }
            for key in DEFAULT_AI_KEYS_B64
        ]

    def effective_ai_config(self) -> dict[str, Any]:
        ai = self.storage.get('aiConfig') or {}
        if str(ai.get('apiBaseURL') or '').strip():
            return {
                'apiBaseURL': str(ai.get('apiBaseURL')).strip(),
                'apiModel': str(ai.get('apiModel') or '').strip(),
                'apiKey': str(ai.get('apiKey') or '').strip(),
                'temperature': float(ai.get('apiTemperature', 1)),
                'source': 'custom',
            }
        config = self.ai_configs()[0]
        return {**config, 'temperature': 1.0}

    def ai_config_for_content(self) -> dict[str, Any]:
        ai = deep_copy(self.storage.get('aiConfig') or {})
        effective = self.effective_ai_config()
        return {
            **ai,
            'apiBaseURL': effective['apiBaseURL'],
            'apiModel': effective['apiModel'],
            'apiKey': effective['apiKey'],
            'apiTemperature': effective.get('temperature', 1),
            'usingLingKumaFreeAI': effective.get('source') != 'custom',
        }

    @staticmethod
    def _extract_ai_content(data: Any) -> str:
        try:
            content = data['choices'][0]['message']['content']
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return ''.join(x if isinstance(x, str) else str(x.get('text') or '') for x in content)
        except (KeyError, IndexError, TypeError):
            pass
        return str(data.get('output_text') or '') if isinstance(data, dict) else ''

    def _post_ai(self, config: dict[str, Any], request_data: dict[str, Any]) -> dict[str, Any]:
        url = str(config.get('apiBaseURL') or '').rstrip('/')
        if not url:
            raise RuntimeError('AI 服务地址为空')
        if not re.search(r'/(chat/completions|responses)$', url, re.I):
            url += '/chat/completions'
        body = {
            'model': request_data.get('model') or config.get('apiModel') or 'GLM-4-Flash',
            'messages': request_data.get('messages') or [],
            'stream': False,
            'temperature': request_data.get('temperature', config.get('temperature', 1)),
        }
        headers = {'Content-Type': 'application/json', 'User-Agent': 'LingKuma-calibre/1.0'}
        if config.get('apiKey'):
            headers['Authorization'] = f"Bearer {config['apiKey']}"
        req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))
        if isinstance(data, dict) and data.get('error'):
            raise RuntimeError(str(data['error'].get('message') or data['error']))
        if not self._extract_ai_content(data):
            raise RuntimeError('AI 服务没有返回可识别的内容')
        return data

    def _ai_cache_key(self, request_data: dict[str, Any]) -> str:
        effective = self.effective_ai_config()
        compact = {
            'provider': [effective.get('apiBaseURL'), effective.get('apiModel'), effective.get('source')],
            'model': request_data.get('model'),
            'messages': request_data.get('messages') or [],
            'temperature': request_data.get('temperature', 1),
        }
        raw = json.dumps(compact, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def _cached_ai(self, request_data: dict[str, Any]) -> dict[str, Any] | None:
        key = self._ai_cache_key(request_data)
        with self._ai_cache_lock:
            item = self._ai_cache.get(key)
            if item and time.monotonic() - item[0] < 1800:
                return deep_copy(item[1])
            if item:
                self._ai_cache.pop(key, None)
        return None

    def _remember_ai(self, request_data: dict[str, Any], response: dict[str, Any]) -> None:
        key = self._ai_cache_key(request_data)
        with self._ai_cache_lock:
            if len(self._ai_cache) > 256:
                oldest = sorted(self._ai_cache.items(), key=lambda item: item[1][0])[:64]
                for old_key, _ in oldest:
                    self._ai_cache.pop(old_key, None)
            self._ai_cache[key] = (time.monotonic(), deep_copy(response))

    @staticmethod
    def _parse_batch_translation(content: str, requested: list[str]) -> dict[str, dict[str, str]]:
        text = str(content or '').strip()
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.I | re.S).strip()
        candidate: Any = None
        try:
            candidate = json.loads(text)
        except Exception:
            match = re.search(r'\{.*\}', text, flags=re.S)
            if match:
                try:
                    candidate = json.loads(match.group(0))
                except Exception:
                    candidate = None
        if isinstance(candidate, dict) and isinstance(candidate.get('translations'), dict):
            candidate = candidate['translations']
        result: dict[str, dict[str, str]] = {}
        if isinstance(candidate, dict):
            for raw_word, raw_value in candidate.items():
                word = normalize_word(raw_word)
                if word not in requested:
                    continue
                if isinstance(raw_value, dict):
                    translation = str(raw_value.get('translation') or raw_value.get('zh') or raw_value.get('meaning') or '').strip()
                    pos = str(raw_value.get('pos') or raw_value.get('partOfSpeech') or '').strip()
                else:
                    translation, pos = str(raw_value or '').strip(), ''
                if translation:
                    result[word] = {'translation': translation, 'pos': pos}
        if not result:
            # Conservative line fallback: ``word: translation``.
            for line in text.splitlines():
                match = re.match(r'\s*["\']?([^:"\']+)["\']?\s*[:：-]\s*(.+?)\s*$', line)
                if not match:
                    continue
                word = normalize_word(match.group(1))
                if word in requested:
                    result[word] = {'translation': match.group(2).strip(' ,"\''), 'pos': ''}
        return result

    def translation_config(self) -> dict[str, Any]:
        return deep_merge(DEFAULT_STORAGE['translationConfig'], self.storage.get('translationConfig') or {})

    @staticmethod
    def _target_language_name(target: str) -> str:
        value = str(target or 'zh-CN').strip() or 'zh-CN'
        names = {
            'zh-cn': 'Simplified Chinese', 'zh-hans': 'Simplified Chinese', 'zh': 'Chinese',
            'zh-tw': 'Traditional Chinese', 'zh-hant': 'Traditional Chinese',
            'en': 'English', 'en-us': 'English', 'en-gb': 'English',
            'de': 'German', 'fr': 'French', 'es': 'Spanish', 'ja': 'Japanese',
            'ko': 'Korean', 'ru': 'Russian', 'it': 'Italian', 'pt': 'Portuguese',
        }
        return names.get(value.lower(), value)

    @staticmethod
    def _source_language_hint(text: str, context: str = '') -> str:
        """Return a conservative source-language hint for adapter-created records.

        LingKuma's original AI language detector stores ISO-style source language
        codes.  The Calibre batch translator previously defaulted every newly
        created record to ``en``; that is wrong for CJK source text and caused
        local TTS to request an English voice for Chinese words.  This helper is
        intentionally conservative: Han-only text without context stays
        ``auto`` so the content-side detector can use the surrounding sentence.
        """
        word = str(text or '')
        sample = f'{word} {context or ""}'
        if re.search(r'[\u3040-\u30ff]', sample):
            return 'ja'
        if re.search(r'[\uac00-\ud7af]', sample):
            return 'ko'
        if re.search(r'[\u0400-\u04ff]', sample):
            return 'ru'
        if re.search(r'[\u4e00-\u9fff]', word):
            # Han-only tokens can be Chinese or Japanese.  Do not guess without
            # kana/context; the language compatibility bridge resolves it from
            # the actual sentence/page before TTS.
            if re.search(r'[\u3040-\u30ff]', str(context or '')):
                return 'ja'
            return 'auto'
        if re.search(r'[A-Za-z]', word):
            return 'en'
        return 'auto'

    @staticmethod
    def _source_language_name(word: str, sentence: str = '') -> str:
        sample = f'{word or ""} {sentence or ""}'
        if re.search(r'[\u3040-\u30ff]', sample):
            return 'Japanese'
        if re.search(r'[\uac00-\ud7af]', sample):
            return 'Korean'
        if re.search(r'[\u4e00-\u9fff]', sample):
            return 'Chinese'
        if re.search(r'[\u0400-\u04ff]', sample):
            return 'Russian or another Cyrillic-script language'
        return 'the source language used in the sentence'

    @staticmethod
    def _target_for_provider(target: str, provider: str) -> str:
        value = str(target or 'zh-CN').strip()
        lower = value.lower()
        if provider == 'microsoft':
            if lower in {'zh-cn', 'zh-hans', 'zh'}:
                return 'zh-Hans'
            if lower in {'zh-tw', 'zh-hant'}:
                return 'zh-Hant'
        return value or 'zh-CN'

    def _retarget_plain_ai_request(self, request_data: dict[str, Any], kind: str, text: str) -> dict[str, Any]:
        """Rewrite only a plain translation request to the configured target language.

        The original LingKuma prompt text is Chinese-centric.  Calibre keeps all
        non-translation AI prompts untouched, but when a request has already
        been positively identified as a plain word/sentence translation we can
        safely replace just that prompt before it reaches the AI backend.
        """
        target = str(self.translation_config().get('targetLanguage') or 'zh-CN').strip() or 'zh-CN'
        language = self._target_language_name(target)
        out = deep_copy(request_data)
        sentence = str(request_data.get('sentence') or '').strip()
        if kind == 'sentence':
            user = f'Translate the following sentence into {language} ({target}). Return only the translation, with no explanation.\n\n{text}'
        else:
            context = f'\nContext sentence: {sentence}' if sentence else ''
            if target.lower() in {'zh-cn', 'zh-hans', 'zh'}:
                user = (
                    f'Translate the word or short expression "{text}" into {language} ({target}) according to context. '
                    f'Return only a concise translation, with no explanation.{context}'
                )
            else:
                user = (
                    f'Translate the word or short expression "{text}" into natural {language} ({target}) as it is used in context. '
                    'Preserve the contextual grammatical meaning, but do not mechanically copy the source-language morphology or invent an unnatural calque. '
                    f'Return only one concise, dictionary-quality target-language equivalent, with no explanation.{context}'
                )
        out['messages'] = [
            {'role': 'system', 'content': 'You are a precise translation engine. Return only the requested translation.'},
            {'role': 'user', 'content': user},
        ]
        out['_skipTranslationRouting'] = True
        return out

    def _context_explanation_request(self, request_data: dict[str, Any]) -> tuple[str, str] | None:
        """Identify LingKuma's default second/contextual word explanation prompt.

        This is intentionally narrow.  The upstream prompt asks for a concise
        grammar/morphology explanation in Chinese, so non-Chinese target
        languages need a language-layer rewrite.  User-supplied aiPrompt2 is
        left untouched.
        """
        ai_config = self.storage.get('aiConfig') or {}
        if isinstance(ai_config, dict) and str(ai_config.get('aiPrompt2') or '').strip():
            return None
        word = str(request_data.get('word') or '').strip()
        sentence = str(request_data.get('sentence') or '').strip()
        if not word or not sentence:
            return None
        messages = request_data.get('messages') or []
        prompt = '\n'.join(str(item.get('content') or '') for item in messages if isinstance(item, dict))
        markers = ('语法解析专家', '具体语法作用', '形变规则', '返回20字左右精要解析', '待解析词')
        if sum(marker in prompt for marker in markers) >= 3:
            return (word, sentence)
        return None

    def _retarget_context_explanation_request(self, request_data: dict[str, Any], word: str, sentence: str) -> dict[str, Any]:
        """Retarget only the default contextual explanation to targetLanguage.

        No upstream UI or analysis logic is modified; this changes only the
        language of the backend response generated for the second AI capsule.
        """
        target = str(self.translation_config().get('targetLanguage') or 'zh-CN').strip() or 'zh-CN'
        if target.lower() in {'zh-cn', 'zh-hans', 'zh'}:
            return request_data
        language = self._target_language_name(target)
        out = deep_copy(request_data)
        user = (
            f'Analyze the word or expression "{word}" in the following sentence. '
            'Briefly explain its grammatical role and, when relevant, its inflection, conjugation, or morphological form. '
            f'Respond ONLY in concise natural {language} ({target}), in about one short sentence. '
            'Do not translate the whole sentence and do not add headings.\n\n'
            f'Sentence: {sentence}\nWord: {word}'
        )
        out['messages'] = [
            {'role': 'system', 'content': f'You are a concise language-learning grammar assistant. Answer in {language} ({target}).'},
            {'role': 'user', 'content': user},
        ]
        out['_skipTranslationRouting'] = True
        return out

    def _tag_analysis_request(self, request_data: dict[str, Any]) -> tuple[str, str] | None:
        """Identify LingKuma's built-in automatic tag-analysis request.

        Custom aiTagAnalysisPrompt values are respected exactly.  Only the
        upstream default prompt is adapted so grammatical metadata describes
        the SOURCE word in the SOURCE language rather than the translation
        target language.
        """
        ai_config = self.storage.get('aiConfig') or {}
        if isinstance(ai_config, dict) and str(ai_config.get('aiTagAnalysisPrompt') or '').strip():
            return None
        word = str(request_data.get('word') or '').strip()
        sentence = str(request_data.get('sentence') or '').strip()
        if not word or not sentence:
            return None
        messages = request_data.get('messages') or []
        prompt = '\n'.join(str(item.get('content') or '') for item in messages if isinstance(item, dict))
        markers = ('词性(pos)', '性别(gender)', '复数形式(plural)', '变位(conjugation)', '仅返回JSON')
        if sum(marker in prompt for marker in markers) >= 4:
            return (word, sentence)
        return None

    def _retarget_tag_analysis_request(self, request_data: dict[str, Any], word: str, sentence: str) -> dict[str, Any]:
        """Keep LingKuma tag metadata aligned with the SOURCE language.

        Core machine keys stay ``pos/gender/plural/conjugation`` because the
        untouched upstream UI expects them.  Extra human-readable tag labels
        and values are requested in the same language as the source sentence.
        Display-only localization is handled by the isolated Calibre language
        bridge, so changing the translation target cannot mix languages in the
        tag row.
        """
        source_name = self._source_language_name(word, sentence)
        out = deep_copy(request_data)
        user = (
            f'Analyze the SOURCE word/expression {word!r} as used in the SOURCE sentence below. '
            f'The source appears to be {source_name}. Do not analyze the translated equivalent. '
            'Return ONLY one JSON object, without markdown. Use these exact technical keys when applicable: '
            '"pos", "gender", "plural", "conjugation". '
            'Use compact LingKuma POS codes such as n, v, adj, adv, pron, prep, det, conj, interj, num, aux, part. '
            'For a category that does not grammatically apply, return null. In particular, Chinese verbs do not conjugate, '
            'so "conjugation" must be null for Chinese source words. For Japanese verbs, conjugation should be the dictionary form; '
            'for English/German/etc. verbs, use the ordinary lemma/base form. '
            'Any EXTRA human-readable keys and their values must be written naturally in the SAME language as the SOURCE sentence '
            'and word, not in the translation target language. Do not transliterate a Chinese word into pinyin as a conjugation.\n\n'
            f'Source sentence: {sentence}\nSource word: {word}'
        )
        out['messages'] = [
            {
                'role': 'system',
                'content': (
                    'You are a precise multilingual grammar tagger. Keep technical keys in the required LingKuma format. '
                    'Any extra human-readable tag labels and values must use the SAME language as the SOURCE text. '
                    'Output strict JSON only.'
                ),
            },
            {'role': 'user', 'content': user},
        ]
        out['_skipTranslationRouting'] = True
        return out

    def _translation_cache_key(self, provider: str, source: str, target: str, text: str) -> str:
        raw = json.dumps([provider, source, target, text], ensure_ascii=False, separators=(',', ':'))
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def _cached_translation(self, provider: str, source: str, target: str, text: str) -> str | None:
        key = self._translation_cache_key(provider, source, target, text)
        with self._translation_cache_lock:
            item = self._translation_cache.get(key)
            if item and time.monotonic() - item[0] < 86400:
                return item[1]
            if item:
                self._translation_cache.pop(key, None)
        return None

    def _remember_translation(self, provider: str, source: str, target: str, text: str, translated: str) -> None:
        key = self._translation_cache_key(provider, source, target, text)
        with self._translation_cache_lock:
            if len(self._translation_cache) > 2048:
                oldest = sorted(self._translation_cache.items(), key=lambda item: item[1][0])[:512]
                for old_key, _ in oldest:
                    self._translation_cache.pop(old_key, None)
            self._translation_cache[key] = (time.monotonic(), translated)

    def _google_web_translate_one(self, text: str, source: str, target: str, timeout: float) -> str:
        query = urllib.parse.urlencode({
            'client': 'gtx', 'sl': source or 'auto', 'tl': target or 'zh-CN',
            'dt': 't', 'q': text,
        })
        url = 'https://translate.googleapis.com/translate_a/single?' + query
        request = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 ' + USER_AGENT,
            'Accept': 'application/json,text/plain,*/*',
        })
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        chunks = payload[0] if isinstance(payload, list) and payload else []
        result = ''.join(str(chunk[0] or '') for chunk in chunks if isinstance(chunk, list) and chunk)
        result = html.unescape(result).strip()
        if not result:
            raise RuntimeError('Google Web Translate 没有返回译文')
        return result

    def _translate_google_web(self, texts: list[str], source: str, target: str, timeout: float) -> list[str]:
        if not texts:
            return []
        # One request is normally enough. Stable ASCII markers let us split the
        # translated block without relying on newline preservation alone.
        block = '\n'.join(f'[[LK{i:03d}]] {text}' for i, text in enumerate(texts))
        translated = self._google_web_translate_one(block, source, target, timeout)
        matches = list(re.finditer(r'\[\[LK(\d{3})\]\]\s*(.*?)(?=\n\s*\[\[LK\d{3}\]\]|\Z)', translated, re.S))
        parsed = [''] * len(texts)
        for match in matches:
            index = int(match.group(1))
            if 0 <= index < len(parsed):
                parsed[index] = match.group(2).strip()
        if all(parsed):
            return parsed
        # Some Google responses alter line boundaries. Fall back to a small
        # parallel pool rather than failing the whole sentence.
        workers = min(6, max(1, len(texts)))
        out = [''] * len(texts)
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='LingKumaTranslate') as pool:
            futures = {pool.submit(self._google_web_translate_one, text, source, target, timeout): i for i, text in enumerate(texts)}
            for future in as_completed(futures):
                out[futures[future]] = future.result()
        return out

    def _translate_microsoft(self, texts: list[str], source: str, target: str, timeout: float, config: dict[str, Any]) -> list[str]:
        key = str(config.get('microsoftKey') or '').strip()
        region = str(config.get('microsoftRegion') or '').strip()
        if not key:
            raise RuntimeError('尚未配置 Microsoft Translator Key')
        endpoint = str(config.get('microsoftEndpoint') or 'https://api.cognitive.microsofttranslator.com').rstrip('/')
        params = {'api-version': '3.0', 'to': self._target_for_provider(target, 'microsoft')}
        if source and source != 'auto':
            params['from'] = source
        url = endpoint + '/translate?' + urllib.parse.urlencode(params)
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Ocp-Apim-Subscription-Key': key,
            'User-Agent': USER_AGENT,
        }
        if region:
            headers['Ocp-Apim-Subscription-Region'] = region
        request = urllib.request.Request(
            url,
            data=json.dumps([{'Text': text} for text in texts], ensure_ascii=False).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        result = []
        for item in payload:
            translations = item.get('translations') or [] if isinstance(item, dict) else []
            result.append(str(translations[0].get('text') or '').strip() if translations else '')
        if len(result) != len(texts) or not all(result):
            raise RuntimeError('Microsoft Translator 返回数量不匹配')
        return result

    def _translate_google_cloud(self, texts: list[str], source: str, target: str, timeout: float, config: dict[str, Any]) -> list[str]:
        key = str(config.get('googleCloudApiKey') or '').strip()
        if not key:
            raise RuntimeError('尚未配置 Google Cloud Translation API Key')
        url = 'https://translation.googleapis.com/language/translate/v2?key=' + urllib.parse.quote(key)
        body: dict[str, Any] = {'q': texts, 'target': target or 'zh-CN', 'format': 'text'}
        if source and source != 'auto':
            body['source'] = source
        request = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json; charset=UTF-8', 'User-Agent': USER_AGENT},
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        items = ((payload.get('data') or {}).get('translations') or []) if isinstance(payload, dict) else []
        result = [html.unescape(str(item.get('translatedText') or '')).strip() for item in items]
        if len(result) != len(texts) or not all(result):
            raise RuntimeError('Google Cloud Translation 返回数量不匹配')
        return result

    def translate_texts(self, texts: Any, source: str = 'auto', target: str | None = None) -> list[str]:
        cleaned = [str(text or '').strip() for text in (texts or [])]
        if not cleaned:
            return []
        config = self.translation_config()
        provider = str(config.get('provider') or 'google-web').strip().lower()
        if provider == 'lingkuma-ai':
            raise RuntimeError('当前翻译引擎为 LingKuma AI')
        target_value = str(target or config.get('targetLanguage') or 'zh-CN').strip()
        try:
            timeout = max(3.0, min(60.0, float(config.get('timeoutSeconds') or 15)))
        except (TypeError, ValueError):
            timeout = 15.0
        results = [''] * len(cleaned)
        missing_texts: list[str] = []
        missing_indexes: list[int] = []
        for index, text in enumerate(cleaned):
            cached = self._cached_translation(provider, source, target_value, text)
            if cached is not None:
                results[index] = cached
            else:
                missing_texts.append(text)
                missing_indexes.append(index)
        if missing_texts:
            started = time.monotonic()
            if provider == 'google-web':
                translated = self._translate_google_web(missing_texts, source, target_value, timeout)
            elif provider == 'microsoft':
                translated = self._translate_microsoft(missing_texts, source, target_value, timeout, config)
            elif provider == 'google-cloud':
                translated = self._translate_google_cloud(missing_texts, source, target_value, timeout, config)
            else:
                raise RuntimeError(f'未知翻译引擎：{provider}')
            for index, original, result in zip(missing_indexes, missing_texts, translated):
                value = str(result or '').strip()
                if not value:
                    raise RuntimeError(f'翻译引擎没有返回“{original}”的译文')
                results[index] = value
                self._remember_translation(provider, source, target_value, original, value)
            elapsed = round((time.monotonic() - started) * 1000, 1)
            print(f'[LingKuma calibre {VERSION_STR}] {provider} translated {len(missing_texts)} texts in {elapsed} ms')
        return results

    @staticmethod
    def _plain_translation_request(request_data: dict[str, Any]) -> tuple[str, str] | None:
        messages = request_data.get('messages') or []
        prompt = '\n'.join(str(item.get('content') or '') for item in messages if isinstance(item, dict))
        word = str(request_data.get('word') or '').strip()
        sentence = str(request_data.get('sentence') or '').strip()
        normalized = re.sub(r'\s+', ' ', prompt)
        if sentence and ('请将句子' in prompt or ('翻译为中文' in prompt and '只返回翻译结果' in prompt)):
            return ('sentence', sentence)
        if word and ('你是翻译专家' in prompt or '只输出翻译结果' in prompt) and ('禁止输出分析' in prompt or '独立单词' in prompt):
            return ('word', word)
        # Custom prompts may be much shorter; only intercept when they still
        # explicitly request translation without explanation.
        if word and '翻译' in normalized and ('不要解释' in normalized or '只返回' in normalized or '只输出' in normalized):
            return ('word', word)
        return None

    @staticmethod
    def _openai_text_response(text: str) -> dict[str, Any]:
        return {
            'id': 'lingkuma-translation', 'object': 'chat.completion',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}],
        }

    def batch_translate_words(self, words: Any, sentence: Any = '') -> dict[str, Any]:
        """Return fast sentence-card translations without trusting stale word meanings.

        Older Calibre adapter builds could persist malformed or context-leaked AI
        translations (for example a function word receiving text from another
        prompt).  Reusing ``words[*].translations[0]`` made those historical
        values reappear forever in the sentence explosion panel.  When a
        dedicated translation provider is configured, refresh high-risk visible
        words through that provider and use the fresh value for page-level details
        returned to JavaScript.  Existing vocabulary translations remain intact
        on disk; only genuinely missing words are populated as before.
        """
        limit = max(1, min(60, int(self.storage.get('calibreBatchMaxWords') or 30)))
        requested: list[str] = []
        for value in words or []:
            word = normalize_word(value)
            if word and word not in requested:
                requested.append(word)
            if len(requested) >= limit:
                break
        sentence_text = str(sentence or '').strip()[:4000]
        translations: dict[str, str] = {}
        details_map: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        with self.lock:
            for word in requested:
                rec = self.words.get(word)
                existing = rec.get('translations', []) if rec else []
                if not existing:
                    missing.append(word)

        started = time.monotonic()
        parsed: dict[str, dict[str, str]] = {}
        config = self.translation_config()
        provider = str(config.get('provider') or 'google-web').strip().lower()
        translator_error: Exception | None = None

        # Refresh only values at high risk of historical contamination: missing
        # meanings, common function words (which were frequently mis-bound to a
        # neighbouring word), or values containing old AI prompt fragments.
        # Clean content-word translations remain local and instant.
        refresh_words: list[str] = []
        with self.lock:
            for word in requested:
                rec = self.words.get(word)
                existing = rec.get('translations', []) if rec else []
                target_value = str(config.get('targetLanguage') or 'zh-CN').strip() or 'zh-CN'
                target_is_default_chinese = target_value.lower() in {'zh-cn', 'zh-hans', 'zh'}
                if (not existing or not target_is_default_chinese or word in _CALIBRE_SENTENCE_REFRESH_WORDS or
                        _looks_like_legacy_sentence_translation(word, existing)):
                    refresh_words.append(word)
        if refresh_words and provider != 'lingkuma-ai':
            try:
                translated = self.translate_texts(refresh_words, source='auto')
                parsed = {
                    word: {'translation': translation, 'pos': ''}
                    for word, translation in zip(refresh_words, translated)
                    if str(translation or '').strip()
                }
            except Exception as error:
                translator_error = error
                print(f'[LingKuma calibre {VERSION_STR}] translation provider refresh failed, using stored meanings/fallback: {error}')
                if not bool(config.get('fallbackToAI', True)):
                    raise

        # Preserve the previous AI fallback only for words that actually have no
        # stored meaning.  A provider outage must not replace valid user data or
        # trigger expensive AI calls for the entire sentence.
        target_value = str(config.get('targetLanguage') or 'zh-CN').strip() or 'zh-CN'
        target_is_default_chinese = target_value.lower() in {'zh-cn', 'zh-hans', 'zh'}
        if provider == 'lingkuma-ai' and not target_is_default_chinese:
            ai_candidates = requested
        elif translator_error is not None and not target_is_default_chinese and bool(config.get('fallbackToAI', True)):
            ai_candidates = refresh_words
        else:
            ai_candidates = missing
        fallback_words = [word for word in ai_candidates if word not in parsed]
        if fallback_words:
            target_name = self._target_language_name(target_value)
            prompt = (
                f'Translate each listed English word into concise {target_name} ({target_value}) according to the sentence context. '
                'Also give a compact English part-of-speech label such as n, v, adj, adv, prep, pron, det, conj. '
                'Return ONLY a JSON object whose keys exactly match the listed lowercase words and whose values are '
                'objects with keys "translation" and "pos". Do not omit function words.\n\n'
                f'Sentence: {sentence_text}\nWords: {json.dumps(fallback_words, ensure_ascii=False)}'
            )
            request = {
                'messages': [
                    {'role': 'system', 'content': 'You are a precise bilingual vocabulary assistant. Output strict JSON only.'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.2,
                'stream': False,
                '_skipTranslationRouting': True,
            }
            response = self.make_ai_request(request)
            fallback_parsed = self._parse_batch_translation(self._extract_ai_content(response), fallback_words)
            parsed.update(fallback_parsed)
            if not fallback_parsed and translator_error:
                raise RuntimeError(f'翻译接口和 AI 回退均未返回译文：{translator_error}')

        now = utc_now()
        with self.lock:
            changed = False
            for word in requested:
                rec = self.words.get(word)
                existing = rec.get('translations', []) if rec else []
                item = parsed.get(word) or {}
                fresh_translation = str(item.get('translation') or '').strip()

                # Keep persistent vocabulary behavior unchanged: only populate a
                # record when it had no translation.  Historical/manual entries
                # are never deleted or overwritten by this repair.
                if fresh_translation and not existing:
                    rec = rec or fresh_record(word, word)
                    rec['status'] = '1' if rec.get('status') in {None, '', '0', 0} else normalize_status(rec.get('status'))
                    rec['language'] = rec.get('language') if rec.get('language') not in {None, '', 'auto'} else self._source_language_hint(word, sentence_text)
                    rec.setdefault('translations', []).append(fresh_translation)
                    pos = str(item.get('pos') or '').strip()
                    if pos:
                        tag = f'pos:["{pos}"]'
                        if tag not in rec.setdefault('tags', []):
                            rec['tags'].append(tag)
                    rec['updatedAt'] = now
                    self.words[word] = normalize_record(word, rec)
                    existing = self.words[word].get('translations', [])
                    changed = True

                stored = self.words.get(word)
                display = deep_copy(stored) if stored else fresh_record(word, word)
                if fresh_translation:
                    # Page-only authoritative translation.  This is the critical
                    # repair: the sentence panel no longer renders poisoned
                    # historical translations such as "中文翻译" prompt fragments.
                    display['translations'] = [fresh_translation]
                    display['language'] = display.get('language') if display.get('language') not in {None, '', 'auto'} else self._source_language_hint(word, sentence_text)
                    translations[word] = fresh_translation
                elif existing:
                    translations[word] = str(existing[0])
                details_map[word] = display

            if changed:
                self._save_locked()

        elapsed_ms = round((time.monotonic() - started) * 1000, 1)
        print(f'[LingKuma calibre {VERSION_STR}] batch prepared {len(translations)}/{len(requested)} word meanings via {provider} in {elapsed_ms} ms')
        return {'success': True, 'translations': translations, 'detailsMap': details_map, 'elapsedMs': elapsed_ms, 'provider': provider}

    def make_ai_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        # Plain word/sentence translations do not need a generative model. Route
        # them through the selected translation engine and reserve AI for the
        # second, explanatory capsule, POS/tags and free-form analysis.
        if not request_data.get('_skipTranslationRouting'):
            plain = self._plain_translation_request(request_data)
            provider = str(self.translation_config().get('provider') or 'google-web').strip().lower()
            if plain:
                kind, text = plain
                if provider != 'lingkuma-ai':
                    try:
                        started = time.monotonic()
                        translated = self.translate_texts([text], source='auto')[0]
                        elapsed = round((time.monotonic() - started) * 1000, 1)
                        print(f'[LingKuma calibre {VERSION_STR}] fast {kind} translation via {provider} in {elapsed} ms')
                        return self._openai_text_response(translated)
                    except Exception as error:
                        print(f'[LingKuma calibre {VERSION_STR}] fast translation failed: {error}')
                        if not bool(self.translation_config().get('fallbackToAI', True)):
                            raise
                # LingKuma AI, or the AI fallback after a dedicated translator
                # failed, must honor the same targetLanguage instead of the
                # Chinese wording embedded in the original upstream prompt.
                request_data = self._retarget_plain_ai_request(request_data, kind, text)
            else:
                contextual = self._context_explanation_request(request_data)
                if contextual:
                    word, sentence = contextual
                    request_data = self._retarget_context_explanation_request(request_data, word, sentence)
                else:
                    tag_analysis = self._tag_analysis_request(request_data)
                    if tag_analysis:
                        word, sentence = tag_analysis
                        request_data = self._retarget_tag_analysis_request(request_data, word, sentence)

        cached = self._cached_ai(request_data)
        if cached is not None:
            return cached
        started = time.monotonic()
        concurrency = max(1, min(8, int(self.storage.get('calibreAIConcurrency') or 3)))
        if getattr(self, '_ai_semaphore_limit', None) != concurrency:
            with self._ai_cache_lock:
                if getattr(self, '_ai_semaphore_limit', None) != concurrency:
                    self._ai_semaphore = threading.BoundedSemaphore(concurrency)
                    self._ai_semaphore_limit = concurrency
        with self._ai_semaphore:
            cached = self._cached_ai(request_data)
            if cached is not None:
                return cached
            custom = self.effective_ai_config()
            if custom.get('source') == 'custom':
                response = self._post_ai(custom, request_data)
            else:
                configs = self.ai_configs()
                random.shuffle(configs)
                last_error: Exception | None = None
                response = None
                for config in configs:
                    try:
                        response = self._post_ai({**config, 'temperature': 1}, request_data)
                        break
                    except Exception as err:  # noqa: PERF203 - key rotation intentionally sequential
                        last_error = err
                if response is None:
                    raise RuntimeError(f'LingKuma 内置免费 AI 当前不可用：{last_error or "所有公共密钥均请求失败"}')
            self._remember_ai(request_data, response)
            elapsed = round((time.monotonic() - started) * 1000, 1)
            print(f'[LingKuma calibre {VERSION_STR}] AI request completed in {elapsed} ms')
            return response


    def _highlight_page_key(self, message: dict[str, Any]) -> str:
        url = str(message.get('_calibreSenderUrl') or '').strip()
        if not url:
            return ''
        try:
            parsed = urllib.parse.urlparse(url)
            return str(parsed.hostname or parsed.netloc or url).lower()
        except Exception:
            return ''

    def _highlight_control_state(self, message: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            scope = 'page' if self.storage.get('wordHighlightFloatingButtonScope') == 'page' else 'global'
            global_enabled = self.storage.get('enablePlugin') is not False
            overrides = self.storage.get('wordHighlightPageTabOverrides')
            overrides = overrides if isinstance(overrides, dict) else {}
            page_key = self._highlight_page_key(message)
            tab_key = str(message.get('_calibreTabId') or '')
            if page_key and page_key in overrides:
                page_enabled = overrides.get(page_key) is True
            else:
                page_enabled = bool(tab_key and overrides.get(tab_key) is True)
            enabled = page_enabled if scope == 'page' else global_enabled
            return {'scope': scope, 'enabled': enabled, 'globalEnabled': global_enabled}

    def _set_page_highlight(self, message: dict[str, Any], enabled: bool) -> tuple[dict[str, Any], dict[str, Any]]:
        with self.lock:
            raw = self.storage.get('wordHighlightPageTabOverrides')
            overrides = deep_copy(raw if isinstance(raw, dict) else {})
        page_key = self._highlight_page_key(message)
        tab_key = str(message.get('_calibreTabId') or '')
        if tab_key:
            overrides.pop(tab_key, None)
        if enabled and page_key:
            overrides[page_key] = True
        elif page_key:
            overrides.pop(page_key, None)
        changes = self.storage_set({'wordHighlightPageTabOverrides': overrides})
        return self._highlight_control_state(message), changes

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        action = message.get('action')
        if action in {'broadcastToggleHighlight', 'setGlobalWordHighlight'}:
            enabled = message.get('enabled') is not False
            changes = self.storage_set({'enablePlugin': enabled})
            state = self._highlight_control_state(message)
            return {
                'success': True, **state, '_storageChanges': changes,
                '_broadcast': {'action': 'toggleHighlight', 'enabled': enabled},
            }
        if action == 'toggleWordHighlightFromFloatingButton':
            enabled = message.get('enabled') is True
            state = self._highlight_control_state(message)
            if state['scope'] == 'page':
                state, changes = self._set_page_highlight(message, enabled)
            else:
                changes = self.storage_set({'enablePlugin': enabled})
                state = self._highlight_control_state(message)
            return {
                'success': True, **state, '_storageChanges': changes,
                '_broadcast': {'action': 'toggleHighlight', 'enabled': enabled},
            }
        if action == 'getWordHighlightControlState':
            return self._highlight_control_state(message)
        if action == 'ensureWordHighlightRuntime':
            state = self._highlight_control_state(message)
            return {
                'success': True, **state,
                '_broadcast': {'action': 'toggleHighlight', 'enabled': state['enabled']},
            }
        if action == 'getWordDetails':
            return {'details': self.get_word(message.get('word'))}
        if action == 'getAllWordDetails':
            return {'details': self.get_all_words()}
        if action == 'getFilteredWordDetails':
            filters = message.get('filters') or {}
            out = {}
            for word, rec in self.get_all_words().items():
                statuses = [str(x) for x in filters.get('statuses', [])]
                if statuses and str(rec.get('status')) not in statuses:
                    continue
                if 'isCustom' in filters and rec.get('isCustom') != filters.get('isCustom'):
                    continue
                out[word] = rec
            return {'details': out}
        if action == 'getWordCount':
            return {'count': len(self.words)}
        if action == 'batchGetWordStatus':
            return {'statusMap': self.status_map(message.get('words') or [])}
        if action == 'batchGetWordDetails':
            words = [normalize_word(x) for x in (message.get('words') or [])]
            return {'detailsMap': {word: self.get_word(word) for word in words if word}}
        if action == 'batchTranslateWords':
            return self.batch_translate_words(message.get('words') or [], message.get('sentence') or '')
        if action == 'translateText':
            text = str(message.get('text') or '').strip()
            if not text:
                return {'success': True, 'translation': ''}
            translated = self.translate_texts([text], str(message.get('source') or 'auto'), str(message.get('target') or '') or None)[0]
            return {'success': True, 'translation': translated, 'provider': self.translation_config().get('provider')}
        if action == 'getAllWordStatusMap':
            return {'statusMap': self.status_map()}
        if action == 'addTranslation':
            self.add_translation(message.get('word'), message.get('translation')); return {'success': True}
        if action == 'removeTranslation':
            self.remove_translation(message.get('word'), message.get('translation')); return {'success': True}
        if action == 'addTag':
            self.add_tag(message.get('word'), message.get('tag')); return {'success': True}
        if action == 'removeTag':
            self.remove_tag(message.get('word'), message.get('tag')); return {'success': True}
        if action == 'addSentence':
            self.add_sentence(message.get('word'), message.get('sentence'), message.get('translation'), message.get('url')); return {'success': True}
        if action == 'removeSentence':
            self.remove_sentence(message.get('word'), message.get('sentence')); return {'success': True}
        if action == 'updateWordStatus':
            self.update_status(message.get('word'), message.get('status'), message.get('language'), message.get('isCustom')); return {'success': True}
        if action in {'ChangeWordLanguage', 'updateWordLanguage'}:
            self.update_language(message.get('word'), message.get('details') or message.get('language')); return {'success': True}
        if action in {'deleteWord', 'deleteWordExact'}:
            self.delete_word(message.get('word')); return {'success': True}
        if action == 'getKnownWordsByStatus':
            statuses = {str(x) for x in message.get('statuses', [])}
            return [rec.get('term') or word for word, rec in self.words.items() if rec.get('status') in statuses]
        if action == 'getCustomWords':
            return {'words': [rec for rec in self.words.values() if rec.get('isCustom')]}
        if action == 'backupDatabase':
            return {'success': True, 'data': self.get_all_words()}
        if action == 'clearDatabase':
            self.clear_words(); return {'success': True}
        if action == 'restoreDatabase':
            return {'success': True, 'restored': self.restore_words(message.get('data') or {}, merge=False)}
        if action == 'mergeDatabase':
            return {'success': True, 'merged': self.restore_words(message.get('data') or {}, merge=True), 'skipped': 0}
        if action == 'getAIConfig':
            return {'config': self.ai_config_for_content()}
        if action == 'makeAIRequest':
            # Upstream a3_aiFragen.js expects the raw OpenAI-compatible response
            # (response.choices[0].message.content), not a wrapper object.
            return self.make_ai_request({**(message.get('requestData') or {}), 'stream': False})
        if action in {'refreshAfdianSubscription'}:
            return {'success': True, 'active': False}
        if action in {
            'playAudio', 'playCustom', 'playLocal', 'playMinimaxi', 'playTTS', 'playEdgeTTS', 'playGptTTS',
            'playSupertoneTTS', 'stopAudio', 'stopSpecificAudio', 'streamUpdate', 'customWordUpdated',
            'clearBackgroundSettingsCache', 'toggleLiquidGlass', 'updateGlassEffect', 'updateHighlightTheme',
            'updateTooltipThemeMode', 'redetectPageLanguage', 'reinitializeJapaneseTokenizer',
            'showWordLimitNotification', 'audioPlaybackStarted', 'audioPlaybackCompleted', 'audioPlaybackError',
            'openSidebar', 'showSidebar', 'openCustomCapsuleSidebar', 'openCustomCapsuleTab',
            'openCustomCapsuleWindow', 'setFont', 'setFontSize', 'setTheme', 'languageChanged',
            'toggleBionic', 'toggleClipSubtitles', 'toggleLingqBlocker', 'togglePosHighlight', 'toggleReadingRuler',
            'toggleThanoxReading', 'toggleWaifu', 'toggleYoutubeCaptionFix', 'toggleYoutubeVideoOverlay',
            'updatePosHighlightConfig', 'updatePosHighlightLanguage', 'updateRulerSettings', 'updateSidebar',
            'updateThanoxSettings', 'updateWaifuUrl', 'updateYoutubeBionicReading', 'updateYoutubeCommaSentencing',
            'updateYoutubeFontFamily', 'updateYoutubeFontSize', 'updateYoutubeSubtitleOffset',
        }:
            return {'success': True, '_localAction': action}
        return {'success': True, 'unhandled': str(action or '')}
