# LingKuma for Calibre

[English](README.md) | [简体中文](README/README_zh.md) | [日本語](README/README_ja.md) | [한국어](README/README_ko.md)

**See it? Click it. Learn it!!!**

LingKuma — *let knowledge spread beyond the barriers of language* — is a translation and language-learning tool designed around reading.

You shouldn't have to wait until you have "learned" a language before you can start reading books and other content in that language.

When you encounter a word you don't know, **click it**.  
When a sentence is difficult to understand, **click it**.

LingKuma helps you read content in languages you are still learning while naturally expanding your vocabulary, becoming more familiar with grammar and expressions, and improving your understanding of the language.

> **Enjoy reading first — and learn a new language along the way.**

## What can LingKuma do?

- Click a word to see its meaning
- Translate and analyze complete sentences
- Listen to word pronunciation with TTS
- Learn vocabulary while reading
- Get AI-assisted grammar and contextual explanations
- Translate between multiple languages
- Use light and dark themes
- Keep the original LingKuma-style interface inside Calibre

## Screenshots

<div align="center">

<p><i>LingKuma in action across different languages and themes.</i></p>

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/calibre-ja-zh-light.png" alt="Japanese to Chinese in light mode" width="95%">
      <br>
      <sub><b>Japanese → Chinese</b></sub><br>
      <sub>Light mode</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/calibre-en-ko-dark.png" alt="English to Korean in dark mode" width="95%">
      <br>
      <sub><b>English → Korean</b></sub><br>
      <sub>Dark mode</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/calibre-zh-en-light.png" alt="Chinese to English in light mode" width="95%">
      <br>
      <sub><b>Chinese → English</b></sub><br>
      <sub>Light mode</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/calibre-zh-it-dark.png" alt="Chinese to Italian in dark mode" width="95%">
      <br>
      <sub><b>Chinese → Italian</b></sub><br>
      <sub>Dark mode</sub>
    </td>
  </tr>
</table>

<br>

<img src="docs/calibre-en-ja-light.png" alt="English to Japanese in light mode" width="70%">
<br>
<sub><b>English → Japanese</b></sub><br>
<sub>Light mode</sub>

</div>

## Calibre Port

This is an unofficial Calibre port of the open-source LingKuma project.

The Calibre port adds:

- Calibre / Qt WebEngine compatibility
- Improved sentence selection for EPUB and PDF
- Short-sentence recognition for Japanese and Korean
- Calibre-compatible frosted-glass effects
- Multilingual translation and AI output support
- Integration with the Calibre reading environment

## Installation

1. Download `lingkuma-calibre-1.0.zip` from **GitHub Releases**.
2. Open **Calibre → Preferences → Plugins**.
3. Choose **Load plugin from file**.
4. Select the downloaded `lingkuma-calibre-1.0.zip`.
5. Restart Calibre.

> Do not install GitHub's automatically generated `Source code (zip)` file. Use the `lingkuma-calibre-1.0.zip` plugin package attached to the release.

## Other Port

- [LingKuma for Zotero](https://github.com/white-ink-cell/lingkuma-zotero)
- [LingKuma](https://github.com/lingkuma/LingKuma)

## Supported Environment

- Calibre 9.x
- EPUB and PDF reading
- Windows / macOS / Linux

## Settings

The settings interface is integrated into Calibre. It includes language and AI settings, vocabulary management, TTS options, appearance controls, and optional WebDAV backup / restore.

## Privacy

LingKuma for Calibre stores its local state in the Calibre plugin data directory. Translation, AI, remote TTS, and WebDAV features may send the text or data required for the selected service. The plugin does not intentionally upload an entire ebook or PDF file for ordinary word or sentence translation.

## Upstream Project and Attribution

- Original project: **LingKuma**
- Upstream version: **LingKuma 1.1.0**
- Calibre port maintained and published by: **white-ink-cell**

This repository provides an unofficial Calibre port of LingKuma.

The port adapts LingKuma to Calibre's reading environment while preserving the original project's core features, interface, assets, and overall design as closely as possible. Calibre-specific changes mainly focus on runtime compatibility, sentence selection, frosted-glass effects, and multilingual translation support.

See `UPSTREAM.md` for more details.

## License

The original LingKuma authorship, copyright, and licenses remain unchanged.

The Calibre adapter and compatibility layer are covered by `LICENSE-ADAPTER.txt`. The original LingKuma license is preserved in `LICENSE-LINGKUMA.txt`, and bundled third-party licenses and notices are documented in `THIRD-PARTY-NOTICES.txt`.
