/* Capture only LingKuma's closed ShadowRoots so explicit Calibre compatibility
 * overlays can be injected without changing vendored upstream source bytes. */
(() => {
  'use strict';
  if (!globalThis.__LINGKUMA_CALIBRE_READER__) return;
  if (globalThis.__LK_CALIBRE_SHADOW_CAPTURE__) return;
  const rootsByHost = new WeakMap();
  const rootsById = new Map();
  const listeners = new Set();
  const originalAttachShadow = Element.prototype.attachShadow;
  const allowedTags = new Set(['lingkuma-tooltip-root', 'lingkuma-explosion-root']);
  Element.prototype.attachShadow = function(init) {
    const root = originalAttachShadow.call(this, init);
    const tag = String(this.localName || '').toLowerCase();
    if (allowedTags.has(tag)) {
      rootsByHost.set(this, root);
      if (this.id) rootsById.set(this.id, root);
      queueMicrotask(() => { if (this.id) rootsById.set(this.id, root); });
      queueMicrotask(() => {
        for (const listener of listeners) listener(this, root);
      });
    }
    return root;
  };
  globalThis.__LK_CALIBRE_SHADOW_CAPTURE__ = {
    get(hostOrId) {
      if (typeof hostOrId === 'string') {
        const host = document.getElementById(hostOrId);
        return (host && rootsByHost.get(host)) || rootsById.get(hostOrId) || null;
      }
      return hostOrId ? rootsByHost.get(hostOrId) || null : null;
    },
    onCapture(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }
  };
  // Reuse the exact Zotero language/lookup adapters through this host alias.
  globalThis.__LINGKUMA_ZOTERO_READER__ = true;
  globalThis.__LINGKUMA_ZOTERO_SHADOW_CAPTURE__ = globalThis.__LK_CALIBRE_SHADOW_CAPTURE__;
})();
