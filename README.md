# LingKuma for Calibre

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [한국어](README_ko.md)

- [LingKuma for Zotero](https://github.com/white-ink-cell/lingkuma-zotero)

An unofficial desktop port of **LingKuma 1.1.0** for Calibre, bringing LingKuma's highlighting, word lookup, translation / AI, sentence analysis, vocabulary, TTS, and theme features into the Calibre reading environment.

> **Calibre port published / maintained by [`white-ink-cell`](https://github.com/white-ink-cell)**  
> This repository is not an official Calibre version of LingKuma. The original LingKuma authorship, copyright, and licenses remain unchanged. `white-ink-cell` refers only to the maintainer and publisher of this Calibre port.

## Screenshots

<p align="center">
  <img src="docs/calibre-ja-zh-light.png" width="48%" alt="Japanese to Chinese in light mode">
  <img src="docs/calibre-en-ko-dark.png" width="48%" alt="English to Korean in dark mode">
</p>
<p align="center">
  <img src="docs/calibre-zh-en-light.png" width="48%" alt="Chinese to English in light mode">
  <img src="docs/calibre-zh-it-dark.png" width="48%" alt="Chinese to Italian in dark mode">
</p>
<p align="center">
  <img src="docs/calibre-en-ja-light.png" width="65%" alt="English to Japanese in light mode">
</p>

## Main Changes

This port focuses on four compatibility changes.

### 1. Calibre Runtime Adaptation

A Calibre compatibility layer is added around LingKuma to provide the runtime capabilities that were originally supplied by the browser-extension environment.

LingKuma's original features and code structure are kept unchanged wherever possible.

### 2. Sentence Selection Improvements

Sentence-boundary and text-reconstruction rules improve complete-sentence capture in EPUB, PDF, parenthetical text, abbreviations, and special punctuation.

**New in 1.0:** meaningful short Japanese and Korean sentences or phrases with fewer than five characters can also open the Word Explosion panel when they contain more than one lexical unit. Single-word hits remain suppressed.

### 3. Frosted-Glass Compatibility

Some original glass effects depend on browser-specific Web components and rendering behavior that are not fully available in Calibre's Qt WebEngine.

This port keeps the original UI and theme logic while providing a Calibre-compatible frosted-glass fallback.

### 4. Multilingual Translation Support

Some original AI prompts and language-handling paths used Chinese as the fixed target language.

This port adds source-language detection and target-language handling so translation, AI explanations, TTS metadata, and related language output can follow the user's selected languages.

## Installation

1. Open **Calibre → Preferences → Plugins**.
2. If an older version of LingKuma for Calibre is installed, remove it and fully exit Calibre.
3. Reopen Calibre and choose **Load plugin from file**.
4. Install `lingkuma-calibre-1.0.zip` from GitHub Releases.
5. Restart Calibre.

> Do not install GitHub's automatically generated source-code ZIP as the Calibre plugin package.

## Translation Settings

Open:

`LingKuma → Full Settings → AI / API Configuration`

Available providers include:

- Google Web Translate (experimental, no API key required)
- Microsoft Translator
- Google Cloud Translation
- LingKuma AI

## Supported Formats and Environment

Directly supported:

- EPUB
- HTMLZ
- TXT
- HTML / XHTML

Other formats can be converted to EPUB with Calibre. PDF quality depends on the text layer and original layout.

Runtime:

- Calibre 7.0+
- Windows / macOS / Linux
- Mainly tested with Calibre 9.x

## Data and Privacy

Settings, vocabulary, example sentences, and reading progress are stored locally in Calibre's configuration directory.

When translation or AI services are used, only the words, sentences, or context required for the request are sent to the selected provider. The plugin does not intentionally upload complete ebook files, Calibre credentials, or library metadata.

API keys are stored in the local plugin state file. WebDAV synchronization occurs only when explicitly requested.

## Upstream Project and Attribution

- Original project: **LingKuma**
- Upstream version: **LingKuma 1.1.0**
- Calibre port maintained / published by: **white-ink-cell**

The original LingKuma authorship, copyright, licenses, core UI, and bundled upstream resources remain attributed to the original project.

See [`UPSTREAM.md`](UPSTREAM.md) for details.

## License

The original LingKuma authorship, copyright, and license remain unchanged.

The Calibre adapter / compatibility layer is covered by `LICENSE-ADAPTER.txt`. The original LingKuma license is preserved in `LICENSE-LINGKUMA.txt`. Bundled third-party resources retain their own notices and licenses in `THIRD-PARTY-NOTICES.txt` and `licenses/`.
