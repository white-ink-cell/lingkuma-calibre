# -*- coding: utf-8 -*-
"""LingKuma for calibre — Interface Action plugin wrapper."""

from calibre.customize import InterfaceActionBase

from calibre_plugins.lingkuma_calibre.version import VERSION


class LingKumaCalibrePlugin(InterfaceActionBase):
    name = 'LingKuma for calibre'
    description = 'Read EPUB books with LingKuma language-learning tools inside calibre.'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'white-ink-cell'
    version = VERSION
    minimum_calibre_version = (7, 0, 0)
    actual_plugin = 'calibre_plugins.lingkuma_calibre.ui:LingKumaAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.lingkuma_calibre.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
        actual = getattr(self, 'actual_plugin_', None)
        if actual is not None:
            actual.apply_settings()
