/* LingKuma Zotero: contextual Word Explosion gloss adapter. */
(() => {
  'use strict';
  if (!globalThis.__LINGKUMA_ZOTERO_READER__) return;
  if (globalThis.__LINGKUMA_ZOTERO_WORD_EXPLOSION__?.installed) return;

  const lookup = globalThis.__LINGKUMA_ZOTERO_LOOKUP_UI__;
  const originalExtract = globalThis.extractUnknownWords;
  const originalCreate = globalThis.createWordItem;
  const originalWordAI = globalThis.fetchAIWordTranslation;
  const originalHide = globalThis.hideWordExplosion;
  const originalShow = globalThis.showWordExplosion;
  const originalGetSentenceForWord = globalThis.getSentenceForWord;
  if (!lookup?.installed || typeof originalExtract !== 'function' || typeof originalCreate !== 'function') return;

  const MAX_CONCURRENT = 4;
  const pending = [];
  const requests = new Map();
  const fallbacks = new Map();
  const cardVersions = new WeakMap();
  let running = 0;
  let nextToken = 0;
  let generation = 0;
  let activeSentence = '';
  let pendingClicked = null;
  let activeClicked = null;
  let cleaned = false;

  function getSentenceWithOccurrence(detail) {
    const result = originalGetSentenceForWord.apply(this, arguments);
    pendingClicked = null;
    const sentence = String(result?.sentence || '').trim();
    const surface = String(detail?.word || '').trim();
    const start = result?.clickedSurfaceStart;
    if (sentence && surface && Number.isInteger(start) && start >= 0
        && sentence.slice(start, start + surface.length).toLocaleLowerCase() === surface.toLocaleLowerCase()) {
      const compound = lookup.explicitCompoundRanges?.(sentence)?.find(item =>
        start >= item.surfaceStart && start + surface.length <= item.surfaceStart + item.surface.length);
      pendingClicked = {
        sentence,
        surface: compound?.surface || surface,
        start: compound?.surfaceStart ?? start,
      };
    }
    return result;
  }

  const sendMessage = message => Promise.resolve(globalThis.chrome.runtime.sendMessage(message));
  const storageGet = keys => Promise.resolve(globalThis.chrome.storage.local.get(keys));

  function pump() {
    while (!cleaned && running < MAX_CONCURRENT && pending.length) {
      const job = pending.shift();
      running++;
      Promise.resolve().then(job.task).then(job.resolve, job.reject).finally(() => {
        running--;
        pump();
      });
    }
  }

  function enqueue(task) {
    return new Promise((resolve, reject) => {
      pending.push({ task, resolve, reject });
      pump();
    });
  }

  function surfaceStart(sentence, surface) {
    const source = String(sentence || '');
    const unit = String(surface || '');
    if (activeClicked?.sentence === source
        && activeClicked.surface.toLocaleLowerCase() === unit.toLocaleLowerCase()) {
      return activeClicked.start;
    }
    const sourceLower = source.toLocaleLowerCase();
    const unitLower = unit.toLocaleLowerCase();
    let start = sourceLower.indexOf(unitLower);
    while (start >= 0) {
      const before = start > 0 ? source[start - 1] : '';
      const after = source[start + unit.length] || '';
      if (!(/[\p{L}\p{N}]/u.test(before) || /[\p{L}\p{N}]/u.test(after))) return start;
      start = sourceLower.indexOf(unitLower, start + 1);
    }
    return -1;
  }

  function requestKey(surface, sentence) {
    const normalizedSurface = String(surface || '').trim();
    const normalizedSentence = String(sentence || '').trim();
    return JSON.stringify([normalizedSentence, normalizedSurface, surfaceStart(normalizedSentence, normalizedSurface)]);
  }

  function quickContext(surface, sentence) {
    const normalizedSurface = String(surface || '').trim();
    const normalizedSentence = String(sentence || '').trim();
    const start = surfaceStart(normalizedSentence, normalizedSurface);
    const key = requestKey(normalizedSurface, normalizedSentence);
    const existing = requests.get(key);
    if (existing) return existing;

    const owner = generation;
    const request = (async () => {
      let stored;
      try { stored = await storageGet('translationConfig'); }
      catch (_) { return { status: 'ERROR' }; }
      if (cleaned || owner !== generation || activeSentence !== normalizedSentence) return { status: 'STALE' };
      const sourceLanguage = String(lookup.inferSourceLanguage?.(
        normalizedSurface,
        normalizedSentence,
        '',
        globalThis.document?.documentElement || null,
      ) || '').trim();
      const targetLanguage = String(stored?.translationConfig?.targetLanguage || '').trim();
      if (!sourceLanguage || !targetLanguage) return { status: 'MISS' };
      return enqueue(async () => {
        if (cleaned || owner !== generation || activeSentence !== normalizedSentence) return { status: 'STALE' };
        const requestToken = `lk-explosion-${++nextToken}`;
        try {
          const result = await sendMessage({
            action: 'lookupQuickContext',
            requestToken,
            surface: normalizedSurface,
            sentence: normalizedSentence,
            ...(start < 0 ? {} : { surfaceStart: start }),
            sourceLanguage,
            targetLanguage,
          });
          if (cleaned || owner !== generation || activeSentence !== normalizedSentence) return { status: 'STALE' };
          if (result?.requestToken !== requestToken) return { status: 'ERROR' };
          return result;
        } catch (_) {
          return { status: 'ERROR' };
        }
      });
    })();
    requests.set(key, request);
    return request;
  }

  function mergedSegments(input, segments) {
    const compounds = lookup.explicitCompoundRanges?.(input) || [];
    if (!compounds.length) return segments;
    const result = [];
    for (const segment of segments) {
      const start = Number(segment.index);
      const end = start + String(segment.segment || '').length;
      const compound = compounds.find(item => {
        const compoundEnd = item.surfaceStart + item.surface.length;
        return start < compoundEnd && end > item.surfaceStart;
      });
      if (!compound) {
        result.push(segment);
      } else if (start === compound.surfaceStart) {
        result.push({
          segment: compound.surface,
          index: compound.surfaceStart,
          input: String(input),
          isWordLike: true,
        });
      }
    }
    return result;
  }

  function withCompoundSegmenter(callback) {
    const nativeIntl = globalThis.Intl;
    const NativeSegmenter = nativeIntl?.Segmenter;
    if (typeof NativeSegmenter !== 'function') return callback();
    const scopedIntl = Object.create(nativeIntl);
    class CompoundSegmenter {
      constructor(locales, options) {
        this.segmenter = new NativeSegmenter(locales, options);
        this.wordGranularity = options?.granularity === 'word';
      }
      segment(input) {
        const segments = Array.from(this.segmenter.segment(input));
        return this.wordGranularity ? mergedSegments(String(input), segments) : segments;
      }
      resolvedOptions() { return this.segmenter.resolvedOptions(); }
    }
    Object.defineProperty(scopedIntl, 'Segmenter', { value: CompoundSegmenter });
    globalThis.Intl = scopedIntl;
    try { return callback(); }
    finally { globalThis.Intl = nativeIntl; }
  }

  function extractWithCompounds(sentence) {
    const normalizedSentence = String(sentence || '').trim();
    if (pendingClicked?.sentence === normalizedSentence) activeClicked = pendingClicked;
    else if (normalizedSentence !== activeSentence) activeClicked = null;
    pendingClicked = null;
    if (normalizedSentence !== activeSentence) {
      generation++;
      activeSentence = normalizedSentence;
      requests.clear();
      fallbacks.clear();
    }
    return withCompoundSegmenter(() => originalExtract.apply(this, arguments));
  }

  function wordAIThroughQuickContext(word, sentence) {
    const normalizedSentence = String(sentence || '').trim();
    if (cleaned || !normalizedSentence || normalizedSentence !== activeSentence) {
      return typeof originalWordAI === 'function'
        ? lookup.fetchAIWithoutCandidateCapture.call(this, word, sentence) : null;
    }
    const key = requestKey(word, normalizedSentence);
    const existing = fallbacks.get(key);
    if (existing) return existing;
    const receiver = this;
    const args = arguments;
    const request = (async () => {
      const result = await quickContext(word, normalizedSentence);
      if (key !== requestKey(word, normalizedSentence)) return null;
      if (result?.status === 'HIT' && String(result.contextualMeaning || '').trim()) {
        return String(result.contextualMeaning).trim();
      }
      if (result?.status === 'STALE' || cleaned || normalizedSentence !== activeSentence) return null;
      if (typeof originalWordAI === 'function') {
        return lookup.fetchAIWithoutCandidateCapture.apply(receiver, args);
      }
      return null;
    })();
    fallbacks.set(key, request);
    return request;
  }

  async function terminalFallback(word, sentence, receiver) {
    const normalizedSentence = String(sentence || '').trim();
    const owner = generation;
    const key = requestKey(word, normalizedSentence);
    const existing = fallbacks.get(key);
    if (existing) return existing;
    let stored;
    try { stored = await storageGet({ autoRequestAITranslations: false }); }
    catch (_) { return null; }
    if (cleaned || owner !== generation || activeSentence !== normalizedSentence) return null;
    if (stored?.autoRequestAITranslations !== true) return null;
    const registered = fallbacks.get(key);
    if (registered) return registered;
    return wordAIThroughQuickContext.call(receiver, word, normalizedSentence);
  }

  function glossContainer(card) {
    let container = card?.querySelector?.('.word-explosion-word-translations');
    if (container) return container;
    container = card?.querySelector?.('.word-explosion-word-loading');
    if (container) {
      container.className = 'word-explosion-word-translations';
      return container;
    }
    container = globalThis.document.createElement('div');
    container.className = 'word-explosion-word-translations';
    card?.appendChild?.(container);
    return container;
  }

  function paintContext(card, wordInfo, sentence, receiver) {
    const owner = generation;
    const version = (cardVersions.get(card) || 0) + 1;
    cardVersions.set(card, version);
    const isCurrent = () => !cleaned && owner === generation && activeSentence === sentence
      && card?.isConnected !== false && cardVersions.get(card) === version;
    const historical = Array.isArray(wordInfo?.details?.translations)
      ? wordInfo.details.translations.filter(value => String(value || '').trim())
      : [];
    const container = glossContainer(card);
    const row = globalThis.document.createElement('div');
    row.className = 'word-explosion-word-translation';
    row.textContent = '加载中...';
    container.replaceChildren(row);
    const paintTerminalFallback = () => {
      terminalFallback(wordInfo?.word, sentence, receiver).then(value => {
        if (!isCurrent()) return;
        row.textContent = String(value || '').trim() || '暂无释义';
      }).catch(() => {
        if (isCurrent()) row.textContent = '暂无释义';
      });
    };
    quickContext(wordInfo?.word, sentence).then(result => {
      if (!isCurrent()) return;
      const contextual = result?.status === 'HIT' ? String(result.contextualMeaning || '').trim() : '';
      if (contextual || historical[0]) {
        row.textContent = contextual || historical[0];
        return;
      }
      paintTerminalFallback();
    }).catch(() => {
      if (isCurrent()) {
        if (historical[0]) row.textContent = historical[0];
        else paintTerminalFallback();
      }
    });
  }

  async function createWithContext(wordInfo) {
    const card = await originalCreate.apply(this, arguments);
    paintContext(card, wordInfo, activeSentence, this);
    return card;
  }

  function showWithOccurrence(sentence) {
    const normalizedSentence = String(sentence || '').trim();
    const clicked = pendingClicked;
    const isNewOccurrence = clicked?.sentence === normalizedSentence && activeSentence === normalizedSentence
      && (clicked.start !== activeClicked?.start || clicked.surface !== activeClicked?.surface);
    const visible = typeof wordExplosionEl !== 'undefined' && wordExplosionEl
      && wordExplosionEl.style.display !== 'none';
    const canUpdate = isNewOccurrence && visible && typeof isPluginEnabled !== 'undefined'
      && isPluginEnabled && typeof wordExplosionEnabled !== 'undefined' && wordExplosionEnabled
      && !(typeof wordExplosionLocked !== 'undefined' && wordExplosionLocked
        && typeof isMouseInsideExplosion !== 'undefined' && isMouseInsideExplosion);
    const result = originalShow?.apply(this, arguments);
    if (!canUpdate || pendingClicked !== clicked || cleaned) return result;
    const wordInfo = typeof currentExplosionWords !== 'undefined'
      ? currentExplosionWords?.find(item => String(item?.word || '').toLocaleLowerCase()
        === clicked.surface.toLocaleLowerCase()) : null;
    const card = Array.from(wordExplosionEl.querySelectorAll('.word-explosion-word-item')).find(item =>
      String(item.querySelector('.word-explosion-word-title')?.firstElementChild?.textContent || '')
        .toLocaleLowerCase() === clicked.surface.toLocaleLowerCase());
    if (!wordInfo || !card) return result;
    activeClicked = clicked;
    pendingClicked = null;
    paintContext(card, wordInfo, normalizedSentence, this);
    return result;
  }

  function hideWithInvalidation() {
    generation++;
    activeSentence = '';
    activeClicked = null;
    const clickAtHide = pendingClicked;
    if (clickAtHide) queueMicrotask(() => {
      if (pendingClicked === clickAtHide) pendingClicked = null;
    });
    requests.clear();
    fallbacks.clear();
    return originalHide?.apply(this, arguments);
  }

  function cleanup() {
    if (cleaned) return;
    cleaned = true;
    generation++;
    activeSentence = '';
    activeClicked = null;
    pendingClicked = null;
    requests.clear();
    fallbacks.clear();
    while (pending.length) pending.shift().resolve({ status: 'STALE' });
    if (globalThis.extractUnknownWords === extractWithCompounds) globalThis.extractUnknownWords = originalExtract;
    if (globalThis.createWordItem === createWithContext) globalThis.createWordItem = originalCreate;
    if (globalThis.fetchAIWordTranslation === wordAIThroughQuickContext) globalThis.fetchAIWordTranslation = originalWordAI;
    if (globalThis.hideWordExplosion === hideWithInvalidation) globalThis.hideWordExplosion = originalHide;
    if (globalThis.showWordExplosion === showWithOccurrence) globalThis.showWordExplosion = originalShow;
    if (globalThis.getSentenceForWord === getSentenceWithOccurrence) globalThis.getSentenceForWord = originalGetSentenceForWord;
  }

  globalThis.extractUnknownWords = extractWithCompounds;
  globalThis.createWordItem = createWithContext;
  if (typeof originalWordAI === 'function') globalThis.fetchAIWordTranslation = wordAIThroughQuickContext;
  if (typeof originalHide === 'function') globalThis.hideWordExplosion = hideWithInvalidation;
  if (typeof originalShow === 'function') globalThis.showWordExplosion = showWithOccurrence;
  if (typeof originalGetSentenceForWord === 'function') globalThis.getSentenceForWord = getSentenceWithOccurrence;
  globalThis.__LINGKUMA_ZOTERO_WORD_EXPLOSION__ = Object.freeze({
    installed: true,
    version: '1.0.0',
    maxConcurrent: MAX_CONCURRENT,
    cleanup,
  });
})();
