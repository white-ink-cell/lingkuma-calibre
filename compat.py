# -*- coding: utf-8 -*-
"""Small compatibility helpers kept separate from the LingKuma core."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def app_executable(name: str) -> str | None:
    """Return a calibre sibling executable or a PATH executable."""
    import shutil

    suffix = '.exe' if sys.platform.startswith('win') else ''
    candidate = Path(sys.executable).resolve().parent / f'{name}{suffix}'
    if candidate.exists():
        return str(candidate)
    found = shutil.which(name) or shutil.which(f'{name}{suffix}')
    return found


def safe_join(root: str | os.PathLike[str], relative: str) -> Path:
    root_path = Path(root).resolve()
    result = (root_path / relative).resolve()
    if result != root_path and root_path not in result.parents:
        raise ValueError('Path escapes the allowed root')
    return result


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first(mapping_a: dict[str, Any], mapping_b: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in mapping_a and mapping_a.get(key) is not None:
        return mapping_a.get(key)
    if key in mapping_b and mapping_b.get(key) is not None:
        return mapping_b.get(key)
    return default


def _color_from_scheme(scheme: dict[str, Any], names: tuple[str, ...], fallback: str) -> str:
    candidates = [scheme]
    for nested in ('light_palette', 'dark_palette', 'palette', 'colors'):
        value = scheme.get(nested)
        if isinstance(value, dict):
            candidates.append(value)
    for candidate in candidates:
        for name in names:
            value = candidate.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return fallback


def calibre_viewer_preferences() -> dict:
    """Return current calibre viewer appearance preferences.

    Calibre has moved some viewer keys between ``session_data`` and the top
    level over releases. Reading both shapes keeps the adapter useful across
    calibre 7–9 without depending on a private dialog class.
    """
    result = {
        'baseFontSize': None, 'minimumFontSize': None,
        'serifFamily': '', 'sansFamily': '', 'monoFamily': '',
        'standardFont': 'serif',
        'marginTop': 40, 'marginRight': 60, 'marginBottom': 40, 'marginLeft': 60,
        'maxTextWidth': 0, 'maxTextHeight': 0, 'readMode': 'flow',
        'userStylesheet': '', 'overrideBookColors': 'never',
        'currentColorScheme': '',
        'backgroundColor': '#ffffff', 'foregroundColor': '#222222', 'linkColor': '#315f9f',
    }
    try:
        from calibre.gui2.viewer.config import vprefs

        session = _dict(vprefs.get('session_data', {}))
        fonts = _dict(_first(session, vprefs, 'standalone_font_settings', {}))

        def integer(name: str, default: int | None) -> int | None:
            value = _first(session, vprefs, name, default)
            try:
                return int(value) if value is not None else default
            except (TypeError, ValueError):
                return default

        current_scheme = str(_first(session, vprefs, 'current_color_scheme', '') or '')
        schemes = _dict(_first(session, vprefs, 'user_color_schemes', {}))
        scheme = _dict(schemes.get(current_scheme))
        background = _color_from_scheme(
            scheme,
            ('background_color', 'background', 'page_background', 'window', 'base'),
            '#222222' if current_scheme.lower() in {'dark', 'night'} else '#ffffff',
        )
        foreground = _color_from_scheme(
            scheme,
            ('foreground_color', 'foreground', 'text_color', 'text', 'window_text'),
            '#e6e0d7' if current_scheme.lower() in {'dark', 'night'} else '#222222',
        )
        link = _color_from_scheme(
            scheme,
            ('link_color', 'link', 'anchor_color'),
            '#8ab4f8' if current_scheme.lower() in {'dark', 'night'} else '#315f9f',
        )
        result.update({
            'baseFontSize': integer('base_font_size', None),
            'minimumFontSize': integer('minimum_font_size', None) if not fonts else (
                int(fonts.get('minimum_font_size')) if fonts.get('minimum_font_size') is not None else None
            ),
            'serifFamily': str(fonts.get('serif_family') or ''),
            'sansFamily': str(fonts.get('sans_family') or ''),
            'monoFamily': str(fonts.get('mono_family') or ''),
            'standardFont': str(fonts.get('standard_font') or 'serif'),
            'marginTop': max(0, integer('margin_top', 40) or 0),
            'marginRight': max(0, integer('margin_right', 60) or 0),
            'marginBottom': max(0, integer('margin_bottom', 40) or 0),
            'marginLeft': max(0, integer('margin_left', 60) or 0),
            'maxTextWidth': max(0, integer('max_text_width', 0) or 0),
            'maxTextHeight': max(0, integer('max_text_height', 0) or 0),
            'readMode': str(_first(session, vprefs, 'read_mode', 'flow') or 'flow'),
            'userStylesheet': str(_first(session, vprefs, 'user_stylesheet', '') or ''),
            'overrideBookColors': str(_first(session, vprefs, 'override_book_colors', 'never') or 'never'),
            'currentColorScheme': current_scheme,
            'backgroundColor': background,
            'foregroundColor': foreground,
            'linkColor': link,
        })
    except Exception as error:
        print(f'[LingKuma calibre] could not read calibre viewer preferences: {error}')
    return result
