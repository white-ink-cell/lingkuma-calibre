# -*- coding: utf-8 -*-
"""LingKuma for calibre — Interface Action plugin wrapper."""

from calibre.customize import InterfaceActionBase

from calibre_plugins.lingkuma_calibre.version import VERSION


class LingKumaCalibrePlugin(InterfaceActionBase):
    name = 'LingKuma for calibre'
    description = 'Read EPUB books with LingKuma language-learning tools inside calibre.'
    supported_platforms = ['windows']
    author = 'LingKuma contributors; Calibre port maintained by white-ink-cell'
    version = VERSION
    minimum_calibre_version = (9, 16, 0)
    actual_plugin = 'calibre_plugins.lingkuma_calibre.ui:LingKumaAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.lingkuma_calibre.config import ConfigWidget
        def refresh_open_readers():
            actual = getattr(self, 'actual_plugin_', None)
            if actual is not None:
                actual.apply_settings()
        return ConfigWidget(on_saved=refresh_open_readers)

    def save_settings(self, config_widget):
        config_widget.save_settings()
