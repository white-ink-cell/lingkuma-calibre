/* LingKuma calibre WebExtension adapter.
 * Runs in the book page before the original LingKuma scripts.
 */
(() => {
  'use strict';
  const boot = globalThis.__LINGKUMA_CALIBRE_BOOTSTRAP__ || {};
  const pluginVersion = String(boot.pluginVersion || '');
  const base = String(boot.baseURL || '').replace(/\/$/, '');
  const tabID = Number(boot.tabID || 1);
  let storageCache = Object.assign({}, boot.storage || {});
  // a1 can receive its asynchronous storage callback before a2 defines the
  // real highlighter. Queue that early request instead of throwing and aborting
  // the remaining upstream initialization.
  if (typeof globalThis.highlightAllWords !== 'function') {
    globalThis.highlightAllWords = function lingkumaPendingHighlight() {
      globalThis.__LK_PENDING_HIGHLIGHT__ = true;
    };
  }

  // Keep the bootstrap storage snapshot byte-for-byte faithful to the backend.
  // Platform emulation must not rewrite LingKuma policy/settings before upstream reads it.
  const runtimeListeners = new Set();
  const storageListeners = new Set();
  let currentSpeech = null;
  let currentAudio = null;

  function clone(value) {
    if (value === undefined) return undefined;
    try { return structuredClone(value); } catch (_) {
      try { return JSON.parse(JSON.stringify(value)); } catch (_) { return value; }
    }
  }
  async function api(path, payload, options = {}) {
    const attempts = Math.max(1, Number(options.attempts || 3));
    let lastError = null;
    for (let attempt = 1; attempt <= attempts; attempt++) {
      try {
        const response = await fetch(base + '/api/' + path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-LingKuma-Client': pluginVersion ? `calibre-${pluginVersion}` : 'calibre' },
          body: JSON.stringify(payload === undefined ? {} : payload),
          cache: 'no-store',
          credentials: 'same-origin',
          redirect: 'error'
        });
        const text = await response.text();
        let data = {};
        try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { error: text || response.statusText }; }
        if (!response.ok || data.error) throw new Error(data.error || ('HTTP ' + response.status));
        return data;
      } catch (error) {
        lastError = error;
        if (attempt < attempts) await new Promise(resolve => setTimeout(resolve, 90 * attempt));
      }
    }
    throw lastError || new Error('LingKuma calibre API failed');
  }
  function callbackOrPromise(promise, callback) {
    if (typeof callback === 'function') {
      // WebExtension callbacks run asynchronously after the current content
      // script has yielded.  A Promise microtask is too early here: a1 can call
      // highlightAllWords before a2_hightlight.js has defined it.  A zero-delay
      // task preserves the browser ordering used by the original extension.
      promise.then(value => {
        setTimeout(() => {
          runtime.lastError = null;
          try { callback(value); } finally { runtime.lastError = null; }
        }, 0);
      }).catch(error => {
        setTimeout(() => {
          runtime.lastError = { message: error && error.message ? error.message : String(error) };
          try { callback(undefined); } finally { setTimeout(() => { runtime.lastError = null; }, 0); }
        }, 0);
      });
      return undefined;
    }
    return promise;
  }
  function getFromCache(keys) {
    if (keys === undefined || keys === null) return clone(storageCache);
    if (typeof keys === 'string') return { [keys]: clone(storageCache[keys]) };
    if (Array.isArray(keys)) {
      const out = {};
      for (const key of keys) out[String(key)] = clone(storageCache[String(key)]);
      return out;
    }
    if (typeof keys === 'object') {
      const out = {};
      for (const [key, fallback] of Object.entries(keys)) {
        out[key] = Object.prototype.hasOwnProperty.call(storageCache, key) ? clone(storageCache[key]) : clone(fallback);
      }
      return out;
    }
    return {};
  }
  function dispatchStorage(changes) {
    if (!changes || typeof changes !== 'object') return;
    for (const listener of Array.from(storageListeners)) {
      try { listener(clone(changes), 'local'); } catch (error) { console.error('[LingKuma storage listener]', error); }
    }
  }
  let storageMutationChain = Promise.resolve();
  function normalizeBackendChanges(rawChanges) {
    const out = {};
    if (!rawChanges || typeof rawChanges !== 'object') return out;
    for (const [key, change] of Object.entries(rawChanges)) {
      if (!change || typeof change !== 'object') continue;
      const normalized = {};
      if (Object.prototype.hasOwnProperty.call(change, 'oldValue')) normalized.oldValue = clone(change.oldValue);
      if (Object.prototype.hasOwnProperty.call(change, 'newValue')) normalized.newValue = clone(change.newValue);
      out[key] = normalized;
    }
    return out;
  }
  function applyBackendStorageChanges(rawChanges) {
    const changes = normalizeBackendChanges(rawChanges);
    const keys = Object.keys(changes);
    if (!keys.length) return changes;
    for (const key of keys) {
      const change = changes[key];
      if (Object.prototype.hasOwnProperty.call(change, 'newValue')) storageCache[key] = clone(change.newValue);
      else delete storageCache[key];
    }
    // storage.onChanged is asynchronous relative to the initiating write and is
    // emitted only after the backend has durably accepted the change.
    setTimeout(() => dispatchStorage(changes), 0);
    return changes;
  }
  function enqueueStorageMutation(work) {
    const operation = storageMutationChain.then(work, work);
    storageMutationChain = operation.catch(() => {});
    return operation;
  }
  function dispatchRuntime(message, sender = {}) {
    for (const listener of Array.from(runtimeListeners)) {
      try { listener(clone(message), clone(sender), () => {}); } catch (error) { console.error('[LingKuma runtime listener]', error); }
    }
  }
  function languageForText(text, requested) {
    if (requested && requested !== 'auto') return requested;
    text = String(text || '');
    if (/[\u4e00-\u9fff]/.test(text)) return 'zh-CN';
    if (/[\u3040-\u30ff]/.test(text)) return 'ja-JP';
    if (/[\uac00-\ud7af]/.test(text)) return 'ko-KR';
    if (/[\u0400-\u04ff]/.test(text)) return 'ru-RU';
    return 'en-US';
  }
  function speakLocal(message) {
    const text = String(message.text || message.sentence || '');
    if (!text || !('speechSynthesis' in globalThis)) return Promise.resolve({ success: false, error: 'speechSynthesis unavailable' });
    try { speechSynthesis.cancel(); } catch (_) {}
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = languageForText(text, message.lang || message.language);
    const options = message.options || {};
    const ttsConfig = storageCache.ttsConfig || {};
    utterance.rate = Number(options.rate || message.rate || ttsConfig.localTTSRate || storageCache.localTTSRate || 1);
    utterance.pitch = Number(options.pitch || message.pitch || ttsConfig.localTTSPitch || storageCache.localTTSPitch || 1);
    utterance.volume = Number(options.volume || message.volume || 1);
    const preferred = String(ttsConfig.localTTSVoice || storageCache.localTTSVoice || message.voice || '');
    if (preferred) {
      const voice = speechSynthesis.getVoices().find(item => item.name === preferred || item.voiceURI === preferred);
      if (voice) utterance.voice = voice;
    }
    currentSpeech = utterance;
    speechSynthesis.speak(utterance);
    return Promise.resolve({ success: true });
  }
  function playRemoteAudio(message) {
    const url = String(message.url || '');
    if (!url) return speakLocal(message);
    try {
      if (currentAudio) { currentAudio.pause(); currentAudio.src = ''; }
      const audio = new Audio(url);
      audio.volume = Math.max(0, Math.min(1, Number(message.volume ?? 1)));
      let remaining = Math.max(1, Number(message.count || 1));
      audio.addEventListener('ended', () => {
        remaining -= 1;
        if (remaining > 0) { audio.currentTime = 0; audio.play().catch(() => {}); }
      });
      currentAudio = audio;
      audio.play().catch(error => console.warn('[LingKuma custom audio]', error));
      return Promise.resolve({ success: true });
    } catch (error) {
      console.warn('[LingKuma custom audio fallback]', error);
      return speakLocal(message);
    }
  }
  function playAudioMessage(message) {
    if (message.audioType === 'playCustom' && message.url) return playRemoteAudio(message);
    // Cloud/Edge providers require browser-extension background capabilities.
    // In calibre, fall back to the operating-system voice rather than failing.
    return speakLocal(message);
  }
  function stopLocalSpeech() {
    try { speechSynthesis.cancel(); } catch (_) {}
    try { if (currentAudio) { currentAudio.pause(); currentAudio.src = ''; } } catch (_) {}
    currentSpeech = null;
    currentAudio = null;
    return Promise.resolve({ success: true });
  }

  // Preserve upstream getWordDetails contract while coalescing bursts from the
  // sentence card into one backend batch. No upstream cache/DOM globals are touched.
  const wordDetailQueue = new Map();
  let wordDetailTimer = 0;
  function queueWordDetails(word) {
    const key = String(word || '').trim().toLowerCase();
    if (!key) return Promise.resolve({ details: {} });
    return new Promise((resolve, reject) => {
      if (!wordDetailQueue.has(key)) wordDetailQueue.set(key, []);
      wordDetailQueue.get(key).push({ resolve, reject });
      if (!wordDetailTimer) wordDetailTimer = setTimeout(flushWordDetailQueue, 18);
    });
  }
  async function flushWordDetailQueue() {
    wordDetailTimer = 0;
    const batch = Array.from(wordDetailQueue.entries());
    wordDetailQueue.clear();
    if (!batch.length) return;
    const max = Math.max(1, Math.min(60, Number(storageCache.calibreBatchMaxWords) || 30));
    for (let offset = 0; offset < batch.length; offset += max) {
      const chunk = batch.slice(offset, offset + max);
      const words = chunk.map(([word]) => word);
      try {
        const response = await api('message', { action: 'batchTranslateWords', words, sentence: '' });
        const detailsMap = response?.detailsMap || {};
        for (const [word, waiters] of chunk) {
          const value = { details: clone(detailsMap[word] || {}) };
          for (const waiter of waiters) waiter.resolve(value);
        }
      } catch (error) {
        // Provider failure must not break the upstream contract. Fall back to
        // ordinary local lookups before surfacing an error.
        for (const [word, waiters] of chunk) {
          try {
            const local = await api('message', { action: 'getWordDetails', word });
            for (const waiter of waiters) waiter.resolve(local || { details: {} });
          } catch (fallbackError) {
            for (const waiter of waiters) waiter.reject(fallbackError);
          }
        }
      }
    }
  }

  const storageLocal = {
    get(keys, callback) {
      // Reads are intentionally cache-backed like a content-script view of
      // extension storage. All writes update this cache from backend-confirmed changes.
      return callbackOrPromise(Promise.resolve(getFromCache(keys)), callback);
    },
    set(values, callback) {
      const payload = values && typeof values === 'object' ? clone(values) : {};
      const promise = enqueueStorageMutation(() => api('storage/set', payload).then(result => {
        applyBackendStorageChanges(result?.changes || {});
        return undefined;
      }));
      return callbackOrPromise(promise, callback);
    },
    remove(keys, callback) {
      const list = Array.isArray(keys) ? keys.map(String) : [String(keys)];
      const promise = enqueueStorageMutation(() => api('storage/remove', { keys: list }).then(result => {
        applyBackendStorageChanges(result?.changes || {});
        return undefined;
      }));
      return callbackOrPromise(promise, callback);
    },
    clear(callback) {
      const promise = enqueueStorageMutation(() => api('storage/clear', {}).then(result => {
        applyBackendStorageChanges(result?.changes || {});
        return undefined;
      }));
      return callbackOrPromise(promise, callback);
    }
  };

  const runtime = {
    id: 'lingkuma-calibre',
    lastError: null,
    getURL(path = '') { return base + '/res/upstream/' + String(path).replace(/^\/+/, ''); },
    getManifest() { return { name: 'LingKuma for calibre', version: pluginVersion, manifest_version: 3 }; },
    sendMessage(...args) {
      let message = args[0];
      let callback = args[1];
      if (typeof message === 'string' && args.length > 1 && typeof args[1] === 'object') {
        message = args[1]; callback = args[2];
      }
      message = message || {};
      const action = message.action;
      if (action === 'getWordDetails') {
        return callbackOrPromise(queueWordDetails(message.word), callback);
      }
      if (action === 'makeAIRequest' && message.requestData && message.requestData.stream) {
        const request = clone(message);
        request.requestData.stream = false;
        request._calibreSenderUrl = location.href;
        request._calibreTabId = tabID;
        const background = api('message', request).then(result => {
          const content = result && result._streamContent ? result._streamContent :
            result?.choices?.[0]?.message?.content || result?.data?.choices?.[0]?.message?.content || '';
          dispatchRuntime({ action: 'streamChunk', data: { content, isFirstChunk: true, isDone: true } }, { tab: { id: tabID, url: location.href } });
          dispatchRuntime({ action: 'streamComplete', data: { done: true } }, { tab: { id: tabID, url: location.href } });
        }).catch(error => {
          dispatchRuntime({ action: 'streamError', data: { error: error.message || String(error) } }, { tab: { id: tabID, url: location.href } });
        });
        void background;
        return callbackOrPromise(Promise.resolve({ success: true, stream: true }), callback);
      }
      if (action === 'playAudio' || action === 'playLocal' || action === 'playTTS' || action === 'playEdgeTTS') {
        return callbackOrPromise(playAudioMessage(message), callback);
      }
      if (['openSidebar', 'openCustomCapsuleSidebar', 'openCustomCapsuleTab', 'openCustomCapsuleWindow'].includes(action)) {
        const url = String(message.url || message.targetUrl || '');
        const p = url ? api('ui', { action: 'open-url', url }) : api('ui', { action: 'vocabulary' });
        return callbackOrPromise(p, callback);
      }
      if (action === 'stopAudio' || action === 'stopSpecificAudio') {
        return callbackOrPromise(stopLocalSpeech(), callback);
      }
      // The real extension background receives sender.tab.url/id out of band.
      // Preserve that contract as adapter metadata rather than making upstream
      // content scripts know anything about calibre.
      const backendMessage = Object.assign({}, clone(message), {
        _calibreSenderUrl: location.href,
        _calibreTabId: tabID
      });
      const promise = api('message', backendMessage).then(result => {
        if (result && result._storageChanges) applyBackendStorageChanges(result._storageChanges);
        if (result && result._broadcast) {
          setTimeout(() => dispatchRuntime(result._broadcast, { id: runtime.id, tab: { id: tabID, url: location.href } }), 0);
        }
        return result;
      });
      return callbackOrPromise(promise, callback);
    },
    openOptionsPage(callback) {
      const p = api('ui', { action: 'settings' });
      return callbackOrPromise(p, callback);
    },
    onMessage: {
      addListener(listener) { if (typeof listener === 'function') runtimeListeners.add(listener); },
      removeListener(listener) { runtimeListeners.delete(listener); },
      hasListener(listener) { return runtimeListeners.has(listener); }
    },
    onConnect: { addListener() {}, removeListener() {}, hasListener() { return false; } }
  };

  const storage = {
    local: storageLocal, sync: storageLocal, session: storageLocal,
    onChanged: {
      addListener(listener) { if (typeof listener === 'function') storageListeners.add(listener); },
      removeListener(listener) { storageListeners.delete(listener); },
      hasListener(listener) { return storageListeners.has(listener); }
    }
  };
  const tabs = {
    query(_query, callback) { return callbackOrPromise(Promise.resolve([{ id: tabID, active: true, url: location.href }]), callback); },
    get(_id, callback) { return callbackOrPromise(Promise.resolve({ id: tabID, active: true, url: location.href }), callback); },
    sendMessage(_id, message, callback) {
      dispatchRuntime(message, { tab: { id: tabID, url: location.href } });
      return callbackOrPromise(Promise.resolve({ success: true }), callback);
    },
    create(info, callback) {
      const url = String(info?.url || '');
      const p = url ? api('ui', { action: 'open-url', url }).then(() => ({ id: Date.now(), url })) : Promise.resolve({ id: Date.now(), url: '' });
      return callbackOrPromise(p, callback);
    }
  };
  const i18n = {
    getUILanguage() { return navigator.language || 'zh-CN'; },
    getMessage(name) { return String(name || ''); },
    detectLanguage(text, callback) {
      const sample = String(text || '');
      const language = /[\u4e00-\u9fff]/.test(sample) ? 'zh' : /[\u3040-\u30ff]/.test(sample) ? 'ja' : /[\uac00-\ud7af]/.test(sample) ? 'ko' : 'en';
      return callbackOrPromise(Promise.resolve({ isReliable: true, languages: [{ language, percentage: 100 }] }), callback);
    }
  };
  const chromeObject = {
    runtime, storage, tabs, i18n,
    extension: { getURL: runtime.getURL },
    tts: {
      speak(text, options = {}, callback) { return callbackOrPromise(speakLocal({ text, options }), callback); },
      stop: stopLocalSpeech,
      getVoices(callback) {
        const voices = ('speechSynthesis' in globalThis ? speechSynthesis.getVoices() : []).map(v => ({ voiceName: v.name, lang: v.lang, remote: !v.localService }));
        return callbackOrPromise(Promise.resolve(voices), callback);
      }
    },
    windows: { create(info, callback) { if (info?.url) window.open(String(info.url), '_blank', 'noopener'); return callbackOrPromise(Promise.resolve({ id: Date.now() }), callback); } },
    sidePanel: { open() { return api('ui', { action: 'vocabulary' }); }, setPanelBehavior() { return Promise.resolve(); } },
    downloads: {
      download(info, callback) {
        try {
          const a = document.createElement('a'); a.href = String(info?.url || ''); a.download = String(info?.filename || ''); a.style.display = 'none';
          document.documentElement.appendChild(a); a.click(); a.remove();
        } catch (_) {}
        return callbackOrPromise(Promise.resolve(Date.now()), callback);
      }
    },
    scripting: { executeScript() { return Promise.resolve([]); }, insertCSS() { return Promise.resolve(); } }
  };

  Object.defineProperty(globalThis, '__LINGKUMA_CALIBRE_READER__', { value: true, configurable: true });
  Object.defineProperty(globalThis, 'chrome', { value: chromeObject, configurable: true });
  Object.defineProperty(globalThis, 'browser', { value: chromeObject, configurable: true });
  Object.defineProperty(globalThis, '__LINGKUMA_CALIBRE__', { value: { version: pluginVersion, bridge: 'http1' }, configurable: true });

  const sendDiagnostic = (level, message, extra = {}) => {
    api('log', { level, message: String(message || ''), url: location.href, ...extra }, { attempts: 1 }).catch(() => {});
  };
  addEventListener('error', event => sendDiagnostic('error', event.message, { source: event.filename, line: event.lineno, column: event.colno }));
  addEventListener('unhandledrejection', event => sendDiagnostic('unhandledrejection', event.reason?.stack || event.reason?.message || String(event.reason || '')));
  sendDiagnostic('info', 'platform adapter ready', {
    enablePlugin: storageCache.enablePlugin !== false,
    highlightScope: storageCache.wordHighlightFloatingButtonScope,
    alphabetic: storageCache.highlightAlphabeticEnabled !== false,
    explosion: storageCache.wordExplosionEnabled !== false,
    readerLayoutMode: storageCache.readerLayoutMode || 'calibre',
    storagePolicy: 'pass-through'
  });
})();
