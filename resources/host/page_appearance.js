/* Calibre reader appearance only. This does not control LingKuma popup theme. */
(() => {
  'use strict';
  const boot = globalThis.__LINGKUMA_CALIBRE_BOOTSTRAP__ || {};
  let settings = boot.storage || {};
  let calibreViewer = boot.calibreViewer || {};
  const root = document.documentElement;
  root.dataset.lkCalibreReader = 'true';

  const number = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
  const cssFamily = value => {
    const text = String(value || '').trim();
    return text ? JSON.stringify(text) : 'LingKumaReaderBook';
  };

  function clearAppearanceState() {
    delete root.dataset.lkReaderTheme;
    delete root.dataset.lkCalibreOverrideColors;
    for (const name of [
      '--lk-calibre-margin-top', '--lk-calibre-margin-right', '--lk-calibre-margin-bottom',
      '--lk-calibre-margin-left', '--lk-calibre-max-width', '--lk-calibre-base-font-size',
      '--lk-calibre-font-family', '--lk-calibre-background', '--lk-calibre-foreground',
      '--lk-calibre-link', '--lk-reader-font-size', '--lk-reader-line-height', '--lk-reader-width',
      '--lk-reader-font-family-custom', '--lk-reader-margin-top', '--lk-reader-margin-right',
      '--lk-reader-margin-bottom', '--lk-reader-margin-left', '--lk-reader-background',
      '--lk-reader-foreground', '--lk-reader-link'
    ]) root.style.removeProperty(name);
  }

  function applyReaderAppearance(nextSettings = {}, nextCalibreViewer = {}) {
    settings = nextSettings && typeof nextSettings === 'object' ? nextSettings : {};
    calibreViewer = nextCalibreViewer && typeof nextCalibreViewer === 'object' ? nextCalibreViewer : {};
    clearAppearanceState();

    let layoutMode = String(settings.readerLayoutMode || '').trim();
    if (!['calibre', 'original', 'custom'].includes(layoutMode)) {
      layoutMode = settings.readerPreserveBookStyles === false ? 'custom' : 'calibre';
    }
    root.dataset.lkReaderLayout = layoutMode;

    if (layoutMode === 'calibre') {
      root.dataset.lkReaderTheme = 'original';
      root.style.setProperty('--lk-calibre-margin-top', number(calibreViewer.marginTop, 40) + 'px');
      root.style.setProperty('--lk-calibre-margin-right', number(calibreViewer.marginRight, 60) + 'px');
      root.style.setProperty('--lk-calibre-margin-bottom', number(calibreViewer.marginBottom, 40) + 'px');
      root.style.setProperty('--lk-calibre-margin-left', number(calibreViewer.marginLeft, 60) + 'px');
      const nativeWidth = number(calibreViewer.maxTextWidth, 0);
      root.style.setProperty('--lk-calibre-max-width', nativeWidth > 0 ? nativeWidth + 'px' : 'none');
      if (number(calibreViewer.baseFontSize, 0) > 0) root.style.setProperty('--lk-calibre-base-font-size', number(calibreViewer.baseFontSize) + 'px');
      const standard = String(calibreViewer.standardFont || 'serif');
      const family = standard === 'sans-serif' ? calibreViewer.sansFamily : standard === 'monospace' ? calibreViewer.monoFamily : calibreViewer.serifFamily;
      if (family) root.style.setProperty('--lk-calibre-font-family', JSON.stringify(String(family)));
      root.style.setProperty('--lk-calibre-background', String(calibreViewer.backgroundColor || '#ffffff'));
      root.style.setProperty('--lk-calibre-foreground', String(calibreViewer.foregroundColor || '#222222'));
      root.style.setProperty('--lk-calibre-link', String(calibreViewer.linkColor || '#315f9f'));
      root.dataset.lkCalibreOverrideColors = String(calibreViewer.overrideBookColors || 'never') === 'never' ? 'false' : 'true';
    } else if (layoutMode === 'custom') {
      const theme = String(settings.readerTheme || 'paper');
      const presets = {
        paper: ['#f8f0dc', '#4a372b', '#6c4d2e'],
        light: ['#ffffff', '#222222', '#315f9f'],
        dark: ['#222222', '#e6e0d7', '#8ab4f8']
      };
      const colors = theme === 'custom'
        ? [settings.readerBackgroundColor || '#f8f0dc', settings.readerTextColor || '#4a372b', settings.readerLinkColor || '#6c4d2e']
        : (presets[theme] || [settings.readerBackgroundColor || '#f8f0dc', settings.readerTextColor || '#4a372b', settings.readerLinkColor || '#6c4d2e']);
      root.dataset.lkReaderTheme = theme;
      root.style.setProperty('--lk-reader-font-size', number(settings.readerFontSize, 20) + 'px');
      root.style.setProperty('--lk-reader-line-height', String(number(settings.readerLineHeight, 1.65)));
      root.style.setProperty('--lk-reader-width', number(settings.readerContentWidth, 860) + 'px');
      root.style.setProperty('--lk-reader-font-family-custom', cssFamily(settings.readerCustomFontFamily));
      root.style.setProperty('--lk-reader-margin-top', number(settings.readerMarginTop, 40) + 'px');
      root.style.setProperty('--lk-reader-margin-right', number(settings.readerMarginRight, 60) + 'px');
      root.style.setProperty('--lk-reader-margin-bottom', number(settings.readerMarginBottom, 40) + 'px');
      root.style.setProperty('--lk-reader-margin-left', number(settings.readerMarginLeft, 60) + 'px');
      root.style.setProperty('--lk-reader-background', String(colors[0]));
      root.style.setProperty('--lk-reader-foreground', String(colors[1]));
      root.style.setProperty('--lk-reader-link', String(colors[2]));
    } else {
      root.dataset.lkReaderTheme = 'original';
    }

    void root.offsetHeight;
    const body = document.body;
    const result = {
      ok: true,
      layout: root.dataset.lkReaderLayout || '',
      theme: root.dataset.lkReaderTheme || '',
      background: body ? getComputedStyle(body).backgroundColor : '',
      color: body ? getComputedStyle(body).color : '',
      fontSize: body ? getComputedStyle(body).fontSize : '',
      fontFamily: body ? getComputedStyle(body).fontFamily : '',
      width: body ? Math.round(body.getBoundingClientRect().width) : 0
    };
    console.info('[LingKuma calibre] page appearance updated', result);
    return result;
  }

  globalThis.__LK_APPLY_READER_APPEARANCE__ = applyReaderAppearance;
  applyReaderAppearance(settings, calibreViewer);
})();
