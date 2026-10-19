# LingKuma for Calibre

[English](README.md) | [简体中文](README/README_zh.md) | [日本語](README/README_ja.md) | [한국어](README/README_ko.md)

**See it. Click it. Learn it.**<br>
**If you don't understand it, click it.**

[Original LingKuma](https://github.com/lingkuma/LingKuma) · [LingKuma Wiki](https://docs.lingkuma.org) · [LingKuma website](https://lingkuma.org/) · [Zotero port](https://github.com/white-ink-cell/lingkuma-zotero)

LingKuma — *let knowledge spread beyond the barriers of language* — is a translation and language-learning tool designed around reading.

You shouldn't have to wait until you have "learned" a language before you can start reading papers, books, and documents in that language.

When you encounter a word you don't know, **click it**.  
When a sentence is difficult to understand, **click it**.

LingKuma helps you read content in languages you are still learning while naturally expanding your vocabulary, becoming more familiar with grammar and expressions, and improving your understanding of the language.

> **Enjoy reading first — and learn a new language along the way.**

## What can LingKuma do?

- Click a word to see its meaning
- Translate and analyze complete sentences
- Use **Dictionary + Quick Context + AI Detail** for faster, more accurate word lookup
- Listen to word pronunciation using recorded dictionary audio, with separate US and UK pronunciation options and TTS fallback when recordings are unavailable
- Learn vocabulary while reading and keep personal meanings / notes
- Use AI-assisted grammar, context, and sentence explanations
- Use Word Explosion to inspect multiple words in the current sentence
- Open external dictionaries, search engines, or encyclopedias such as Wikipedia with custom buttons
- Use Bionic Reading, Reading Ruler, and POS Highlight
- Back up / restore learning data with optional WebDAV
- Use light and dark themes

For broader LingKuma usage guides and platform documentation, see the [LingKuma Wiki](https://docs.lingkuma.org).

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

The original LingKuma already provides word highlighting, sentence translation and analysis, vocabulary learning, speech playback, Edge TTS, and other reading features. The Calibre port preserves these core capabilities and adapts them to Calibre's independent reading environment.

The Calibre port mainly adds or adjusts:

- Integration with Calibre's ebook reading environment, running LingKuma in a separate Qt WebEngine reader window
- EPUB reading compatibility, chapter navigation, reading progress, and page appearance controls
- Improved sentence selection and line-break repair during EPUB reading
- Better sentence recognition and reconstruction, including meaningful short Japanese and Korean phrases
- Explicit English hyphenated-compound recognition
- Faster English word lookup with Dictionary + Quick Context
- Calibre-compatible frosted-glass effects
- An integrated LingKuma settings interface inside Calibre, covering language, vocabulary, TTS, reading assistance, and data management
- Fixes for Edge TTS playback, previews, and stopping behavior in the Calibre runtime

## What's new in v1.1.2?

### Calibre reading environment compatibility

This release is based on **LingKuma 1.1.1** and further improves its independent reading experience inside Calibre.

LingKuma's reading, translation, learning, and tooltip interfaces continue to follow the original project's design and functionality. The Calibre adapter handles ebook parsing, the Qt WebEngine reader window, chapter navigation, reading progress, and compatibility with browser-extension runtime interfaces.

This release also completes more of the language settings, vocabulary management, TTS configuration and previews, reading assistance, and data management functionality.

### Faster lookup: Dictionary + Quick Context + AI

Previous versions depended much more heavily on AI for ordinary word meanings. That could make simple lookup slower and could occasionally produce over-broad explanations — for example, an adjective and the noun next to it might both be explained as the same whole phrase.

The new lookup flow separates the job into three layers:

1. **Dictionary** — fast lexical facts such as basic meanings, part of speech, morphology, IPA, and pronunciation metadata.
2. **Quick Context** — fast, non-generative contextual translation using the **full current sentence**, extracting the selected word's meaning in context rather than interpreting it in isolation.
3. **AI Detail** — deeper grammar, usage, sentence analysis, and follow-up explanation.

This reduces ordinary lookup latency and improves the reliability of basic lexical information without removing LingKuma's AI capabilities.

When meanings are available, users can also review, edit, or delete saved meanings through vocabulary management without forcing meanings from different sources into a single entry.

### Faster Word Explosion

Word Explosion no longer needs to wait for a separate AI request for every visible word in the normal path.

Its per-word glosses now prioritize Quick Context while preserving existing saved meanings.

Full-sentence translation and deeper AI analysis remain available separately.

### Better sentence selection

This release preserves LingKuma's existing sentence-processing capabilities and further improves them for Calibre's EPUB reading environment:

- improved sentence selection across line breaks and multiple text nodes in EPUB;
- fewer half-sentence and accidental cross-sentence selections;
- conservative handling of abbreviations, initials, decimals, quotes, brackets, colons, and semicolons;
- repair of obvious layout-induced line-break hyphenation in EPUB;
- improved recognition of meaningful short Japanese and Korean phrases.

The Calibre port does not automatically convert or handle PDF files. For PDF reading, the original LingKuma browser extension can be used instead.

### Hyphenated words and compounds

Previously, words like these could be incorrectly split:

- `well-known`
- `out-of-sample`
- `peer-on-peer`

Explicit English hyphenated compounds can now be treated as one lookup and learning unit instead of being split into unrelated tokens.

Layout-only line breaks remain a separate case. For example, an obvious `inter-` + line break + `national` can be conservatively repaired as `international`.

### Pronunciation: recorded dictionary audio + IPA + US / UK

English pronunciation follows a **dictionary-first pronunciation path** using reliable pronunciation data:

- reliable surface-form IPA is shown when available;
- US and UK pronunciation are displayed separately and can be played independently;
- recorded dictionary audio is preferred when available;
- when the exact surface form has no recording, TTS is used.

For the main word pronunciation button:

- only US recording available → play US;
- only UK recording available → play UK;
- both available → **US is the default**;
- neither available → fall back to TTS.

This is particularly useful for inflected forms such as `books`, `worked`, `studies`, and `working`.

### Edge TTS fixes for Calibre

**Edge TTS is an existing feature of the original LingKuma project, not a new speech provider introduced by this port.**

This release mainly fixes its compatibility with the Calibre runtime, improving speech synthesis, previews, parameter handling, and playback cancellation. It uses a bundled `edge-tts` client and its required dependencies.

During actual installation testing with Windows Calibre 9.16, the user confirmed that:

- Edge TTS US English speech plays correctly;
- Edge TTS UK English speech plays correctly;
- the Stop button works correctly.

Calibre's settings also provide configuration and preview controls for system-local speech, Edge TTS, and GPT TTS. Each speech provider continues to use its own configuration and service requirements.

### Reading and learning features retained

The port continues to preserve or expose the applicable LingKuma reading workflow, including:

- vocabulary status and saved meanings;
- example records and learning data;
- AI sentence analysis and deeper word explanation;
- Bionic Reading;
- Reading Ruler;
- POS Highlight;
- custom external search / dictionary / encyclopedia buttons;
- local vocabulary management;
- WebDAV backup / restore;
- EPUB reading and text repair;
- Calibre-compatible theme and popup behavior;
- chapter navigation, reading progress, and page appearance controls.

## Current language scope

LingKuma itself remains multilingual, but the **new bundled local dictionary acceleration is currently focused on English source text**.

In this release:

- the bundled local lexical dictionary is **English → Simplified Chinese**;
- Quick Context can follow the configured target language where the translation service supports it;
- other source languages can continue using applicable translation and AI features;
- equivalent local dictionary packs for other source languages are not bundled yet.

As a result, the largest speed and lexical-meaning reliability improvement in this release is for **English-source reading**. Other source languages do not lose their existing translation and AI capabilities simply because a corresponding local dictionary is unavailable.

## Installation

1. Download `lingkuma-calibre-1.1.2.zip` from **[GitHub Releases](https://github.com/white-ink-cell/lingkuma-calibre/releases)**.
2. Open **Calibre → Preferences → Plugins**.
3. Choose **Load plugin from file**.
4. Select the downloaded `lingkuma-calibre-1.1.2.zip` file.
5. Confirm the installation as prompted by Calibre, then restart Calibre.

> Do not install GitHub's automatically generated `Source code (zip)` file as the Calibre plugin. Use the `lingkuma-calibre-1.1.2.zip` plugin package attached to the release.

## Other Versions

- [LingKuma for Zotero](https://github.com/white-ink-cell/lingkuma-zotero)
- [LingKuma](https://github.com/lingkuma/LingKuma)

## Supported Environment

- **Windows x64**
- Minimum required version: **Calibre 9.16**
- Tested with Windows Calibre 9.16 / Python 3.14
- EPUB reading support
- This port does not automatically convert or handle PDF files
- **macOS and Linux are outside this release's supported platforms**

The bundled Edge TTS native dependencies target Windows AMD64 / Python 3.14.

## Settings

The settings interface is integrated into Calibre.

After installation, open **LingKuma → Full Settings** inside Calibre.

It includes language and translation settings, AI provider / prompt settings, vocabulary management, dictionary options, local / Edge / GPT TTS, popup and reading-assistance controls, and optional WebDAV backup / restore.

The interface language and translation target language can be configured independently. Changing the interface language does not automatically change the translation target.

## Privacy

LingKuma for Calibre stores its local state in the Calibre plugin data directory.

Translation, AI, remote TTS, and WebDAV features may send the text or data required for the selected service to external providers.

Ordinary word or sentence lookup does not intentionally upload an entire ebook.

## Upstream Project and Attribution

- Original project: **[LingKuma](https://github.com/lingkuma/LingKuma)**
- LingKuma Wiki: **[docs.lingkuma.org](https://docs.lingkuma.org)**
- Upstream version: **LingKuma 1.1.1**
- Calibre port maintained and published by: **white-ink-cell**

This repository provides an unofficial Calibre port of LingKuma.

The port adapts LingKuma to Calibre's reading environment while preserving the original project's core features, interface, assets, and overall design as closely as possible. Calibre-specific changes focus on runtime compatibility, sentence selection, Dictionary / Quick Context integration, pronunciation adaptation, compound-word handling, frosted-glass compatibility, and multilingual translation support.

See [UPSTREAM.md](UPSTREAM.md) for more details.

## Dictionary Data

The bundled English dictionary is derived from **English Wiktionary** contributor data extracted through **Wiktextract** and distributed by **Kaikki.org**.

Dictionary text data is distributed under **CC BY-SA 4.0**. Remote Wikimedia Commons pronunciation files keep the individual licenses shown on their source pages.

See `licenses/ENGLISH-WIKTIONARY-DATA-NOTICE.txt` and `THIRD-PARTY-NOTICES.txt` for details.

## License

The original LingKuma authorship, copyright, and licenses remain unchanged.

The Calibre adapter and compatibility layer are covered by `licenses/LICENSE-ADAPTER.txt`. The original LingKuma license is preserved in `LICENSE-LINGKUMA.txt`, and bundled third-party licenses and notices are documented in `THIRD-PARTY-NOTICES.txt`.
