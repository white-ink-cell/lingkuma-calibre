/* Read-only LingKuma boot coordinator. It starts upstream after the document is
 * ready but never rewrites LingKuma settings or UI state. */
(() => {
  'use strict';
  let started = false;
  function start() {
    if (started) return;
    started = true;
    try {
      if (typeof globalThis.startHighlightRuntimeFromStorage === 'function') {
        globalThis.startHighlightRuntimeFromStorage();
      } else if (typeof globalThis.highlightAllWords === 'function') {
        globalThis.highlightAllWords();
        globalThis.__LK_PENDING_HIGHLIGHT__ = false;
      } else {
        console.error('[LingKuma calibre] upstream highlighter entry point is missing');
      }
    } catch (error) {
      console.error('[LingKuma calibre] failed to start upstream runtime', error);
    }
  }

  const schedule = () => setTimeout(start, 80);
  if (document.readyState === 'complete') schedule();
  else addEventListener('load', schedule, { once: true });

  console.info('[LingKuma calibre] thin adapter boot ready');
})();
