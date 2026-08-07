/* Calibre host navigation/progress. No LingKuma UI or persistent settings. */
(() => {
  'use strict';
  const boot = globalThis.__LINGKUMA_CALIBRE_BOOTSTRAP__ || {};
  const base = String(boot.baseURL || '').replace(/\/$/, '');

  const postProgress = () => {
    const max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
    const ratio = Math.max(0, Math.min(1, scrollY / max));
    fetch(base + '/api/progress', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chapter: Number(boot.chapterIndex || 0), scrollRatio: ratio }),
      keepalive: true
    }).catch(() => {});
  };
  let timer = 0;
  addEventListener('scroll', () => {
    clearTimeout(timer);
    timer = setTimeout(postProgress, 500);
  }, { passive: true });
  addEventListener('pagehide', postProgress);

  const restoreProgress = () => {
    const ratio = Number(boot.progress?.scrollRatio || 0);
    if (ratio <= 0 || Number(boot.progress?.chapter || 0) !== Number(boot.chapterIndex || 0)) return;
    setTimeout(() => {
      const max = Math.max(0, document.documentElement.scrollHeight - innerHeight);
      scrollTo(0, max * Math.max(0, Math.min(1, ratio)));
    }, 120);
  };
  if (document.readyState === 'complete') restoreProgress();
  else addEventListener('load', restoreProgress, { once: true });

  document.addEventListener('click', event => {
    const anchor = event.target?.closest?.('a[href]');
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    try {
      const target = new URL(anchor.href, location.href);
      const sameBook = target.origin === location.origin && target.pathname.includes('/book/');
      const isHtml = /\.(?:x?html?|xhtm)$/i.test(target.pathname);
      if (sameBook && isHtml && target.searchParams.get('lkmain') !== '1') {
        event.preventDefault();
        target.searchParams.set('lkmain', '1');
        location.assign(target.href);
      }
    } catch (_) {}
  }, true);
})();
