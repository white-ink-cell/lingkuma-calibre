# -*- coding: utf-8 -*-
"""Thin Calibre host for the pinned, unmodified edge-tts Python client."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import math
import re
import shutil
import sys
import threading
import zipfile
from pathlib import Path

from calibre.utils.config import config_dir
from calibre_plugins.lingkuma_calibre.version import VERSION_STR

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_TEXT_LENGTH = 2000
_LOCK = threading.Lock()
_SYNTH_SLOTS = threading.BoundedSemaphore(2)
_REQUEST_LOCK = threading.Lock()
_ACTIVE_REQUESTS = {}
_EARLY_CANCELS = set()
_WHEEL_HASHES = {
    'aiohappyeyeballs-2.7.1-py3-none-any.whl': '9243213661e29250eb41368e5daa826fc017156c3b8a11440826b2e3ed376472',
    'aiohttp-3.14.5-cp314-cp314-win_amd64.whl': '6f967dde489ca6a8c02d093ab245d2cbf50ccb5c36adf0188b17b0ca39d24b67',
    'aiosignal-1.4.0-py3-none-any.whl': '053243f8b92b990551949e63930a839ff0cf0b0ebbe0597b0f3fb19e1a0fe82e',
    'async_timeout-5.0.1-py3-none-any.whl': '39e3809566ff85354557ec2398b55e096c8364bacac9405a7a1fa429e77fe76c',
    'attrs-26.1.0-py3-none-any.whl': 'c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309',
    'certifi-2026.10.18-py3-none-any.whl': '73191c47aaa79da394e8fee2dbc2ec827432cab56311122c9e47abf79e390f62',
    'edge_tts-7.3.1-py3-none-any.whl': '2a3c79d6235a7a736d681233823ce5492e829b43eb47beae49aa181237a8f9a4',
    'frozenlist-1.8.0-cp314-cp314-win_amd64.whl': '3e0761f4d1a44f1d1a47996511752cf3dcec5bbdd9cc2b4fe595caf97754b7a0',
    'idna-3.20-py3-none-any.whl': 'ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c',
    'multidict-7.1.0-cp314-cp314-win_amd64.whl': '6c9fd50f636a8fa9cb6324cd3eac962fec2bc5bb432452a3b583583a1059acfc',
    'propcache-0.5.4-cp314-cp314-win_amd64.whl': '0a095db8e15a6020db149ecbed6461939fe74f6acaa3ae8b702a1fe8c38cd983',
    'tabulate-0.10.0-py3-none-any.whl': 'f0b0622e567335c8fabaaa659f1b33bcb6ddfe2e496071b743aa113f8774f2d3',
    'typing_extensions-4.16.0-py3-none-any.whl': '481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8',
    'yarl-1.25.1-cp314-cp314-win_amd64.whl': 'acfa7e22aa6c6e7a5996a41d275bfa01efa7ea56ab890590280e9063e2cf5c1b',
}


def _client():
    """Extract wheels to this plugin's versioned runtime; never pip install."""
    with _LOCK:
        runtime = Path(config_dir) / 'plugins' / 'lingkuma-calibre' / f'runtime-{VERSION_STR}'
        site = runtime / 'edge_tts_site'
        wheels = runtime / 'resources' / 'vendor' / 'edge_tts_wheels'
        if not wheels.is_dir():
            wheels = Path(__file__).resolve().parent / 'resources' / 'vendor' / 'edge_tts_wheels'
        if not (site / '.complete').exists():
            if not wheels.is_dir():
                raise RuntimeError('Edge TTS unavailable')
            staging = runtime / 'edge_tts_site.partial'
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir(parents=True)
            try:
                for name, expected in _WHEEL_HASHES.items():
                    wheel = wheels / name
                    if hashlib.sha256(wheel.read_bytes()).hexdigest() != expected:
                        raise RuntimeError('Edge TTS dependency check failed')
                    with zipfile.ZipFile(wheel) as archive:
                        for member in archive.infolist():
                            target = (staging / member.filename).resolve()
                            if not target.is_relative_to(staging.resolve()):
                                raise RuntimeError('Edge TTS dependency check failed')
                            archive.extract(member, staging)
                (staging / '.complete').write_text('edge-tts 7.3.1', encoding='ascii')
                if site.exists():
                    shutil.rmtree(site)
                staging.rename(site)
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                raise
        if str(site) not in sys.path:
            sys.path.insert(0, str(site))
        import edge_tts
        if edge_tts.__version__ != '7.3.1':
            raise RuntimeError('Edge TTS dependency check failed')
        return edge_tts


def _signed(value, suffix, *, pitch=False):
    raw = str(value if value is not None else 'default').strip()
    if raw.lower() == 'default':
        raw = '+0%'
    explicit = raw.endswith('%') or raw.endswith('Hz')
    if explicit:
        raw = raw[:-1] if raw.endswith('%') else raw[:-2]
    try:
        number = float(raw)
    except ValueError:
        raise ValueError('Edge TTS setting is invalid') from None
    if not math.isfinite(number):
        raise ValueError('Edge TTS setting is invalid')
    if not explicit:
        # Upstream sends legacy numeric multipliers; the existing JS bridge
        # treats 1 as default and +/-3 as a relative rate/volume/pitch scale.
        number = (number - 1) * 100 if abs(number) <= 3 else number
    number = round(number)
    if number < -100 or number > 100:
        raise ValueError('Edge TTS setting is invalid')
    # Keep the original LingKuma SSML percentage semantics for pitch.
    return f'{number:+d}{"%" if pitch else suffix}'


def _options(options):
    text = str(options.get('text') or '').strip()
    if not text or len(text) > MAX_TEXT_LENGTH:
        raise ValueError('Edge TTS text is invalid')
    voice = str(options.get('voice') or 'en-US-AriaNeural').strip()
    if not re.fullmatch(r'[A-Za-z]{2,3}-[A-Za-z]{2,4}-[A-Za-z0-9]+Neural', voice):
        raise ValueError('Edge TTS voice is invalid')
    return text, voice, _signed(options.get('rate'), '%'), _signed(options.get('volume'), '%'), _signed(options.get('pitch'), '', pitch=True)


async def _synthesize(edge_tts, values):
    text, voice, rate, volume, pitch = values
    audio = bytearray()
    client = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch='+0Hz',
                                  connect_timeout=10, receive_timeout=15)
    # edge-tts 7.3.1 validates pitch only as Hz on construction, but its SSML
    # formatter reads this field verbatim. LingKuma's original setting is %.
    # The value above is bounded to a signed integer before this assignment.
    client.tts_config.pitch = pitch
    async for chunk in client.stream():
        if chunk.get('type') == 'audio':
            data = chunk.get('data') or b''
            if len(audio) + len(data) > MAX_AUDIO_BYTES:
                raise RuntimeError('Edge TTS audio is too large')
            audio.extend(data)
    return bytes(audio)


class _Cancellation:
    def __init__(self):
        self.cancelled = False
        self.loop = None
        self.task = None

    def bind(self):
        with _REQUEST_LOCK:
            self.loop = asyncio.get_running_loop()
            self.task = asyncio.current_task()
            if self.cancelled:
                self.task.cancel()


def cancel_edge_tts_audio(request_id):
    """Cancel a single reader or native-preview synthesis without cross-book effects."""
    if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,96}', request_id):
        return False
    with _REQUEST_LOCK:
        current = _ACTIVE_REQUESTS.get(request_id)
        if current is None:
            # A stop request may overtake the synthesis POST on the loopback server.
            if len(_EARLY_CANCELS) >= 128:
                _EARLY_CANCELS.pop()
            _EARLY_CANCELS.add(request_id)
            return True
        current.cancelled = True
        loop, task = current.loop, current.task
    if loop is not None and task is not None:
        try:
            loop.call_soon_threadsafe(task.cancel)
        except RuntimeError:
            # The synthesis may have completed and closed its per-call loop.
            pass
    return True


def fetch_edge_tts_audio(options):
    """Return the same bounded audio envelope as the existing host TTS route."""
    values = _options(options)
    request_id = options.get('requestId')
    if request_id is not None and (not isinstance(request_id, str) or
                                   not re.fullmatch(r'[A-Za-z0-9_-]{8,96}', request_id)):
        raise ValueError('Edge TTS setting is invalid')
    control = _Cancellation()
    if request_id:
        with _REQUEST_LOCK:
            if request_id in _ACTIVE_REQUESTS:
                raise ValueError('Edge TTS setting is invalid')
            control.cancelled = request_id in _EARLY_CANCELS
            _EARLY_CANCELS.discard(request_id)
            _ACTIVE_REQUESTS[request_id] = control
    acquired = False
    try:
        if control.cancelled:
            raise RuntimeError('Edge TTS synthesis cancelled')
        acquired = _SYNTH_SLOTS.acquire(blocking=False)
        if not acquired:
            raise RuntimeError('Edge TTS synthesis failed')
        async def run():
            control.bind()
            return await asyncio.wait_for(_synthesize(_client(), values), timeout=25)
        try:
            audio = asyncio.run(run())
        except asyncio.CancelledError:
            raise RuntimeError('Edge TTS synthesis cancelled') from None
        except (TimeoutError, OSError):
            raise RuntimeError('Edge TTS connection failed') from None
        except RuntimeError as error:
            if str(error) == 'Edge TTS synthesis cancelled':
                raise
            raise RuntimeError('Edge TTS synthesis failed') from None
        except Exception:
            raise RuntimeError('Edge TTS synthesis failed') from None
    finally:
        if acquired:
            _SYNTH_SLOTS.release()
        if request_id:
            with _REQUEST_LOCK:
                if _ACTIVE_REQUESTS.get(request_id) is control:
                    del _ACTIVE_REQUESTS[request_id]
    if not audio or not (audio.startswith(b'ID3') or audio[0] == 0xff):
        raise RuntimeError('Edge TTS synthesis failed')
    return {'audioBase64': base64.b64encode(audio).decode('ascii'), 'mimeType': 'audio/mpeg'}
