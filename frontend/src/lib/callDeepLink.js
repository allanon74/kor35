/**
 * Deep-link / payload push per chiamate vocali (shell Capacitor + PWA).
 *
 * URL tipica: /?tab=messaggi&call=<uuid>&voce=VOCE_INVITO
 * Payload FCM/data: { category, call_id, action, url, ... }
 */

const VOCE_ACTIONS = new Set([
  'VOCE_INVITO',
  'VOCE_PERSA',
  'VOCE_ACCETTATA',
  'VOCE_RIFIUTATA',
  'VOCE_CHIUSA',
  'VOCE_PRESA',
]);

function pick(obj, keys) {
  if (!obj || typeof obj !== 'object') return undefined;
  for (const key of keys) {
    const value = obj[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return value;
    }
  }
  return undefined;
}

/**
 * @param {string|URL|Location|{search?: string, href?: string}|null|undefined} source
 * @returns {{callId: string|null, action: string|null, url: string|null, category: string|null}}
 */
export function parseCallDeepLink(source) {
  let search = '';
  let href = '';
  try {
    if (!source) {
      /* empty */
    } else if (typeof source === 'string') {
      href = source;
      if (source.includes('?')) {
        search = source.slice(source.indexOf('?'));
      } else if (source.startsWith('call=') || source.startsWith('voce=')) {
        search = `?${source}`;
      }
    } else if (typeof URL !== 'undefined' && source instanceof URL) {
      href = source.href;
      search = source.search;
    } else if (typeof source.search === 'string') {
      search = source.search;
      href = source.href || '';
    }
  } catch {
    /* ignore */
  }

  let params;
  try {
    params = new URLSearchParams(search || '');
  } catch {
    params = new URLSearchParams();
  }

  const callId = (params.get('call') || params.get('call_id') || '').trim() || null;
  let action = (params.get('voce') || params.get('action') || '').trim() || null;
  if (action && !action.startsWith('VOCE_') && VOCE_ACTIONS.has(`VOCE_${action.toUpperCase()}`)) {
    action = `VOCE_${action.toUpperCase()}`;
  } else if (action && action.startsWith('voce_')) {
    action = action.toUpperCase();
  }
  if (action && !VOCE_ACTIONS.has(action)) {
    // Accetta comunque VOCE_* sconosciute; scarta junk
    if (!String(action).startsWith('VOCE_')) action = null;
  }

  return {
    callId,
    action,
    url: href || null,
    category: (params.get('category') || '').trim() || null,
  };
}

/**
 * Normalizza payload Capacitor push / data FCM / SW notification data.
 * @param {object|null|undefined} raw
 */
export function parseCallPushPayload(raw) {
  if (!raw || typeof raw !== 'object') {
    return { callId: null, action: null, url: null, category: null, head: null, body: null };
  }

  const data =
    raw.data && typeof raw.data === 'object'
      ? { ...raw, ...raw.data }
      : raw.notification && typeof raw.notification === 'object'
        ? { ...raw, ...raw.notification, ...(raw.notification.data || {}) }
        : raw;

  const nested = data.data && typeof data.data === 'object' ? data.data : {};
  const merged = { ...nested, ...data };

  const url = String(pick(merged, ['url', 'link']) || '').trim() || null;
  const fromUrl = url ? parseCallDeepLink(url) : { callId: null, action: null };

  const callId =
    String(pick(merged, ['call_id', 'callId', 'call']) || fromUrl.callId || '').trim() || null;
  let action =
    String(pick(merged, ['action', 'voce']) || fromUrl.action || '').trim() || null;
  if (action && !action.startsWith('VOCE_') && /^[A-Z_]+$/.test(action)) {
    action = action.startsWith('VOCE') ? action : `VOCE_${action}`;
  }
  if (action && action.startsWith('voce_')) action = action.toUpperCase();

  const category = String(pick(merged, ['category']) || fromUrl.category || '').trim() || null;
  const head = String(pick(merged, ['head', 'title']) || '').trim() || null;
  const body = String(pick(merged, ['body', 'message']) || '').trim() || null;

  return { callId, action, url, category, head, body };
}

export function isIncomingCallPayload(parsed) {
  if (!parsed) return false;
  if (parsed.category === 'chiamate') return true;
  if (parsed.action === 'VOCE_INVITO' || parsed.action === 'VOCE_PERSA') return true;
  return Boolean(parsed.callId && parsed.action && String(parsed.action).startsWith('VOCE_'));
}

/**
 * Emette eventi DOM per aprire messaggi e risvegliare l'overlay chiamata.
 * @param {{callId?: string|null, action?: string|null, url?: string|null}} info
 */
export function dispatchCallWake(info = {}) {
  if (typeof window === 'undefined') return;
  const detail = {
    call_id: info.callId || null,
    action: info.action || null,
    url: info.url || null,
  };
  window.dispatchEvent(new CustomEvent('kor35:open-messaggi'));
  window.dispatchEvent(new CustomEvent('kor35:voce-wake', { detail }));
  if (detail.action && detail.action.startsWith('VOCE_')) {
    window.dispatchEvent(
      new CustomEvent('kor35:voce', {
        detail: {
          action: detail.action,
          call_id: detail.call_id,
        },
      })
    );
  }
}
