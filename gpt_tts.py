# -*- coding: utf-8 -*-
"""Calibre network transport for LingKuma's existing GPT speech parameters.

The request fields mirror upstream src/player/offscreen.js::playGptTTS.
The original content script still chooses the provider and supplies its values.
"""

from __future__ import annotations

import base64
import json
import math
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ENDPOINT = 'https://api.openai.com/v1/audio/speech'
MIME_TYPES = {'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'opus': 'audio/opus',
              'aac': 'audio/aac', 'flac': 'audio/flac'}
MAX_AUDIO_BYTES = 10 * 1024 * 1024


def prepare_gpt_tts_request(options):
    """Return one request using the same GPT fields/defaults as upstream."""
    key = str(options.get('apiKey') or '').strip()
    if not key:
        raise ValueError('GPT TTS API Key is empty')
    endpoint = str(options.get('apiEndpoint') or DEFAULT_ENDPOINT).strip()
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('GPT TTS API address is invalid')
    text = str(options.get('text') or '').strip()
    if not text:
        raise ValueError('GPT TTS text is empty')
    fmt = str(options.get('responseFormat') or 'mp3').lower()
    if fmt not in MIME_TYPES:
        raise ValueError('GPT TTS audio format is unsupported')
    voice = str(options.get('voice') or 'alloy').strip() or 'alloy'
    if voice.startswith('{'):
        try:
            voice = json.loads(voice)
        except json.JSONDecodeError:
            voice = 'alloy'  # Upstream's malformed-voice fallback.
    elif voice.startswith('voice_'):
        voice = {'id': voice}
    try:
        speed = float(options.get('speed') or 1)
    except (TypeError, ValueError):
        speed = 1.0
    if not math.isfinite(speed):
        speed = 1.0
    body = {'model': options.get('model') or 'gpt-4o-mini-tts', 'input': text,
            'voice': voice, 'response_format': fmt, 'speed': speed}
    instructions = str(options.get('instructions') or '').strip()
    if instructions:
        body['instructions'] = instructions
    return endpoint, {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, json.dumps(body, ensure_ascii=False).encode('utf-8'), MIME_TYPES[fmt]


def fetch_gpt_tts_audio(options):
    """Supply the extension offscreen network capability to the loopback reader."""
    endpoint, headers, body, mime = prepare_gpt_tts_request(options)
    request = urllib.request.Request(endpoint, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            audio = response.read(MAX_AUDIO_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'GPT TTS HTTP {error.code}') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError('GPT TTS network request failed') from None
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise RuntimeError('GPT TTS returned empty or oversized audio')
    return {'audioBase64': base64.b64encode(audio).decode('ascii'), 'mimeType': mime}
