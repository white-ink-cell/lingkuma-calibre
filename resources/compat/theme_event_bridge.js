/* Bridge LingKuma's original per-page theme override back into LingKuma's
 * original tooltip-theme message contract. No popup classes/styles are changed here. */
(() => {
  'use strict';
  if (!globalThis.__LINGKUMA_CALIBRE_READER__) return;

  const normalize = value => {
    if (typeof value === 'boolean') return value;
    if (value && typeof value.isDark === 'boolean') return value.isDark;
    return null;
  };
  const pageKey = () => {
    try { return String(location.hostname || location.host || '').toLowerCase(); }
    catch (_) { return ''; }
  };

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName !== 'local' || !changes.highlightPageThemeOverrides) return;
    const overrides = changes.highlightPageThemeOverrides.newValue || {};
    if (normalize(overrides[pageKey()]) === null) return;

    // Upstream a2 consumes the storage change and updates highlightManager.
    // On the next task, ask upstream a4/a7 to re-evaluate their own theme.
    // updateTooltipThemeMode is already handled by both original modules.
    setTimeout(() => {
      chrome.storage.local.get({ tooltipThemeMode: 'auto' }, result => {
        const mode = ['auto', 'light', 'dark'].includes(result?.tooltipThemeMode)
          ? result.tooltipThemeMode : 'auto';
        // A page day/night toggle should affect popup surfaces only when the
        // user's original tooltip preference is "auto".
        if (mode !== 'auto') return;
        chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
          const tab = Array.isArray(tabs) ? tabs[0] : null;
          if (!tab) return;
          chrome.tabs.sendMessage(tab.id, { action: 'updateTooltipThemeMode', mode: 'auto' }, () => {});
        });
      });
    }, 0);
  });
})();
