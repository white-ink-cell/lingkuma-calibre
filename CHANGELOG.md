# Changelog

## 1.1.2

- Updated the Calibre EPUB port to the pinned LingKuma 1.1.1 resource set while keeping original LingKuma authorship, interface, themes and product logic.
- Added Calibre settings and language controls, the English local-dictionary → translation/API → optional AI lookup path, editable meanings, vocabulary import/export, AI profiles, and reading aids. Original non-English translation paths remain in place.
- Added Local, Edge and GPT TTS settings previews. The maintained `edge-tts` 7.3.1 client is bundled for the Windows Calibre 9.16 host; the user heard US and UK speech and confirmed Stop. Live paid GPT speech was not verified. macOS/Linux are outside this release's supported platforms.
- Preserved EPUB sentence selection, short Japanese/Korean phrases and Word Explosion behavior. Calibre PDF is deferred and is not automatically converted.
- Validation: 169 Calibre-host tests with 15 expected skips and 46 Node tests with one expected skip passed on the reviewed source. The exact 199-entry release candidate installed in Calibre 9.16 and showed live German EPUB Quick Context results in Chinese and Japanese in a visible Windows reader; normal close exited 0. An offscreen-only WebEngine teardown test exited with a Windows access violation. Live AI Detail was not tested at the product owner's direction.

## 1.1.1

- Fixed a diagnostic-only page self-test race during rapid chapter navigation/reload.
- The delayed self-test is now bound to the URL that finished loading and skips stale timers.
- Made the diagnostic `documentElement.dataset` read null-safe while QWebEngine replaces documents.
- No changes to LingKuma upstream, AI/translation routing, a4/a7 compatibility, theme handling, vocabulary, or reader behavior.

## 1.1.0

- Refactored the Calibre port around a thin adapter boundary instead of continuing UI-specific hotfixes.
- Restored all 141 vendored `resources/upstream/**` files to byte-identical LingKuma 1.1.0 source.
- Restored LingKuma's original light/dark implementation in `highlight_floating_button.js`, `a2_hightlight.js`, `a4_tooltip_new.js`, and `a7_words_boom.js`.
- Removed Calibre-specific theme classes from upstream a7 and Calibre/Zotero CSS from upstream a4.
- Kept positioned/PDF sentence reconstruction as a gated compatibility module that falls back to upstream behavior on normal HTML.
- Kept the Qt WebEngine glass rendering workaround as an external compatibility stylesheet while leaving glass state/theme ownership to upstream a4.
- Added a minimal theme event bridge that uses upstream's own `updateHighlightTheme` message contract.
- Stopped page bootstrap/migrations from forcibly changing LingKuma master-switch, page-scope, page-overrides, or tooltip-minimized settings.
- Preserved fast word-meaning batching behind the original `getWordDetails` contract instead of mutating `highlightManager` internals.
- Made highlight control message handling respect the upstream global/page scope model.

## 1.0.12

- Fixed Calibre page-theme synchronization: the Word Explosion panel now follows the floating day/night highlight toggle immediately while `tooltipThemeMode` is `auto`.
- Re-applies the Word Explosion theme every time the reusable panel is shown, preventing stale light/dark classes after a theme change.
- Fixed the 1.0.11 legacy-translation repair path so already-populated polluted function words (for example `of`, `to`, `is`) are included in the fast sentence-card refresh instead of only missing words.
- Keeps persistent vocabulary records non-destructive; refreshed translations remain page-display overrides unless the word had no stored translation.

## 1.0.11

- Fixed sentence-card word meanings that could reuse malformed historical translations saved by older Calibre adapter builds.
- When a dedicated translation provider is configured, high-risk sentence words are refreshed through that provider for display while existing vocabulary translations are preserved on disk.
- Keeps the 1.0.10 state-recovery, master-switch, and version-consistency hardening.

## 1.0.10

- Preserve an explicit disabled master switch across migrations, chapter loads, and restarts.
- Preserve malformed state files before recovery and never overwrite them when backup fails.
- Use atomic, flushed state replacement for stronger persistence integrity.
- Centralize runtime version metadata so diagnostics and user agents report the installed release consistently.
- No intentional changes to vocabulary, translation, AI routing, TTS, reader appearance, or supported formats.

## 1.0.9

- Fixed the out-of-scope `layoutMode` reference in the reader runtime that fired after every page-appearance update and triggered LingKuma's global cleanup handler.
- Preserved the original LingKuma meaning of `enablePlugin`: “单词高亮” is the master switch, so disabling it intentionally stops highlighting, lookup popups and sentence explosion.
- Stopped the Calibre adapter from hard-coding the master switch back to enabled during chapter startup; it now respects the saved upstream setting.
- Clarified the Calibre settings label as “单词高亮（总开关）” without changing upstream behavior.

## 1.0.8

- Fixed the in-reader page settings dialog so **应用/保存** changes the open chapter immediately instead of relying on a page reload.
- Added an explicit Qt-to-JavaScript appearance bridge with diagnostic results for layout, theme, background, font, size and width.
- Made custom background, text, link, font, font-size, line-height, width and margins override nested EPUB styles that previously hid the changes.
- Kept these strong overrides isolated to **自定义书页**; **跟随 Calibre** and **保留 EPUB 原书排版** remain unchanged.
- Preserved the fast Google/Microsoft/Google Cloud translation routing introduced in 1.0.7.

## 1.0.6

- Added Calibre/original/custom layout modes and initial mirroring of Calibre viewer preferences.
- Batched sentence vocabulary AI requests and added AI caching/concurrency limits.
- Fixed highlighter startup ordering.

## 1.0.5

- Restored global highlighting in EPUB chapters and preserved publisher layout by default.
- Added safe post-load highlighter bootstrap and reduced duplicate runtime injection.

## 1.0.2

- Fixed Calibre toolbar construction compatibility.
- Added positioned-text sentence reconstruction and footnote handling.

## 1.0.0

- Initial Calibre adapter based on LingKuma 1.1.0.
