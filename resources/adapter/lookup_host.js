/* Calibre host primitives for Zotero's unchanged LingKumaLookupService. */
(() => {
  'use strict';
  const boot = globalThis.__LINGKUMA_CALIBRE_BOOTSTRAP__ || {};
  const base = String(boot.baseURL || '').replace(/\/$/, '');
  const storage = { ...(boot.storage || {}) };
  let pendingSave = Promise.resolve();
  const api = async (path, payload, signal) => {
    const response = await fetch(`${base}/api/lookup/${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload), credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal
    });
    const result = await response.json();
    if (!response.ok || result.error) throw new Error(result.error || `Lookup host HTTP ${response.status}`);
    return result.value;
  };
  const invoke = (op, fields = {}) => api('op', { op, ...fields });
  const pathJoin = (...parts) => parts.map(part => String(part).replace(/^\/+|\/+$/g, '')).join('/');
  const state = {
    storageGet(defaults = {}) {
      const value = {};
      for (const [key, fallback] of Object.entries(defaults)) value[key] = storage[key] ?? fallback;
      return value;
    },
    storageSet(values) {
      Object.assign(storage, values);
      pendingSave = pendingSave.then(() => globalThis.chrome.storage.local.set(values));
    },
    addTranslation(surface, meaning, targetLanguage) {
      globalThis.chrome.runtime.sendMessage({ action: 'addTranslation', word: surface,
        translation: meaning, targetLanguage }).catch(error => console.warn('[LingKuma lookup save]', error));
    },
    makeAIRequest(requestData) {
      return globalThis.chrome.runtime.sendMessage({ action: 'makeAIRequest', requestData });
    },
    save() { return pendingSave; }
  };
  globalThis.chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local') return;
    for (const [key, item] of Object.entries(changes || {})) storage[key] = item.newValue;
  });
  const dependencies = {
    dataRoot: 'data', join: pathJoin,
    file: {
      exists: path => invoke('exists', { path }),
      stat: path => invoke('stat', { path }),
      makeDirectory: path => invoke('mkdir', { path }),
      copy: (source, target) => invoke('copy', { source, target }),
      move: (source, target) => invoke('move', { source, target }),
      remove: path => invoke('remove', { path }),
    },
    dbFactory: path => ({
      queryAsync: (sql, params = []) => invoke('query', { path, sql, params }),
      valueQueryAsync: (sql, params = []) => invoke('value', { path, sql, params }),
      closeDatabase: async () => {}
    }),
    sha256File: path => invoke('sha256', { path }),
    copyBundledToFile: (source, target, signal) => {
      if (signal?.aborted) throw new Error('Dictionary copy cancelled');
      return invoke('copyBundled', { source, target });
    },
    async translateQuickContext({ surface, sentence, surfaceStart, sourceLanguage, targetLanguage, signal }) {
      if (signal?.aborted) throw new Error('Quick Context translation was cancelled');
      const config = state.storageGet({ translationConfig: {} }).translationConfig || {};
      const rawTimeout = Number(config.timeoutSeconds);
      const timeout = Number.isFinite(rawTimeout) ? Math.max(3, Math.min(60, rawTimeout)) : 15;
      const url = lkLookupMicrosoftEdgeURL(sourceLanguage, targetLanguage);
      const marked = lkLookupMarkedSentence(sentence, surface, surfaceStart);
      const payload = await api('translate', { url: url.href, body: JSON.stringify([marked]), timeout }, signal);
      const result = lkLookupMicrosoftEdgeResult(payload, targetLanguage);
      if (!result) throw new Error('Microsoft Edge Translator returned an invalid marked-sentence result');
      return result;
    },
    now: () => new Date().toISOString(),
    logError: error => console.warn('[LingKuma lookup]', error),
  };
  const lookup = new globalThis.LingKumaLookupService({ state, dependencies });
  const originalEnsureDefault = lookup.ensureDefaultDictionary.bind(lookup);
  lookup.ensureDefaultDictionary = async (sourceLanguage, targetLanguage, options) => {
    const dictionaryID = lookup._catalogEntry(sourceLanguage, targetLanguage)?.dictionaryID;
    if (!dictionaryID) return originalEnsureDefault(sourceLanguage, targetLanguage, options);
    const lease = await invoke('acquireDefault', { dictionaryID });
    try { return await originalEnsureDefault(sourceLanguage, targetLanguage, options); }
    finally { await invoke('releaseDefault', { lease }); }
  };
  const ready = lookup.init();
  globalThis.__LINGKUMA_CALIBRE_LOOKUP__ = lookup;
  let checkedPair = '';
  const precheckDictionary = async () => {
    const source = String(document.documentElement?.lang || boot.bookLanguage || '').trim();
    const target = String(storage.translationConfig?.targetLanguage || '').trim();
    if (!source || !target || !/^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$/i.test(source)) return;
    const pair = `${source.toLowerCase()}\u0000${target.toLowerCase()}`;
    if (pair === checkedPair) return;
    checkedPair = pair;
    try {
      await ready;
      await lookup.ensureApplicableDefaultDictionary(source, target);
    } catch (error) {
      checkedPair = '';
      dependencies.logError(error);
    }
  };
  if (boot.bookKey) {
    Promise.resolve().then(precheckDictionary);
    globalThis.chrome.storage.onChanged.addListener((changes, area) => {
      if (area === 'local' && changes?.translationConfig) Promise.resolve().then(precheckDictionary);
    });
  }
  globalThis.__LINGKUMA_CALIBRE_IMPORT_DICTIONARY__ = async sourcePath => {
    await ready;
    const result = await lookup.importCustomDictionary(sourcePath);
    await state.save();
    return result;
  };
  globalThis.__LINGKUMA_CALIBRE_DICTIONARY_STATUS__ = async pair => {
    await ready;
    return lookup.getDictionaryStatus(pair || {});
  };
  globalThis.__LINGKUMA_CALIBRE_LOOKUP_REQUEST__ = async message => {
    await ready;
    if (message.action === 'lookupDictionary') return lookup.lookupDictionary(message);
    if (message.action === 'lookupPronunciation') return lookup.lookupPronunciation(message);
    if (message.action === 'lookupAIPronunciation') return lookup.lookupAIPronunciation(message);
    if (message.action === 'lookupQuickContext') return lookup.lookupQuickContext(message);
    throw new Error('Unknown lookup action');
  };
})();
