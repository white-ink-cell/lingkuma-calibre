# Upstream Project and Porting Notes

[English](UPSTREAM.md) | [简体中文](UPSTREAM_zh.md) | [日本語](UPSTREAM_ja.md) | [한국어](UPSTREAM_ko.md)

This project is an unofficial Calibre port of **LingKuma 1.1.0**.

- Original project: `lingkuma/LingKuma`
- Upstream version: LingKuma 1.1.0
- Calibre port maintained / published by: `white-ink-cell`

The original LingKuma authorship, copyright, licenses, and bundled upstream resources remain unchanged.

## Porting Changes

The Calibre port mainly adds:

1. A Calibre / Qt WebEngine compatibility layer around LingKuma.
2. Sentence-boundary and text-reconstruction rules for Calibre reading content. Version 1.0 also allows meaningful short Japanese and Korean sentences or phrases under five characters to trigger Word Explosion when they contain more than one lexical unit.
3. A Calibre-compatible frosted-glass fallback while preserving LingKuma's theme and popup logic.
4. Source-language and target-language handling for multilingual translation, AI output, and related language metadata.

Calibre-specific behavior is kept in the adapter / host / compatibility layers wherever possible, while the bundled LingKuma upstream resources retain their original attribution and licenses.
