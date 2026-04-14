/**
 * Auto-link dei termini glossario nel DOM wiki (dopo innerHTML, prima dei widget React).
 * Le definizioni supportano HTML base formattato.
 */

const SKIP_ANCESTOR_TAGS = new Set(['A', 'CODE', 'PRE', 'SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'KBD', 'SAMP']);

function isWordChar(ch) {
  if (!ch) return false;
  return /[\p{L}\p{N}]/u.test(ch);
}

function isBoundaryAt(text, start, end) {
  const before = start > 0 ? text[start - 1] : '';
  const after = end < text.length ? text[end] : '';
  return !isWordChar(before) && !isWordChar(after);
}

function shouldProcessTextNode(textNode, root) {
  let el = textNode.parentElement;
  while (el && el !== root) {
    if (SKIP_ANCESTOR_TAGS.has(el.tagName)) return false;
    if (el.classList?.contains('wiki-widget-slot')) return false;
    if (el.classList?.contains('wiki-glossary-section')) return false;
    el = el.parentElement;
  }
  return !!textNode.parentElement && root.contains(textNode.parentElement);
}

function normalizeEntries(entries) {
  if (!entries || !Array.isArray(entries)) return [];
  return entries
    .map((e) => ({
      sync_id: String(e.sync_id ?? '').trim(),
      nome: String(e.nome ?? '').trim(),
      dichiarazione: String(e.dichiarazione ?? '').trim(),
      descrizione: String(e.descrizione ?? ''),
    }))
    .filter((e) => e.sync_id && e.dichiarazione);
}

function sortTermsForMatching(entries) {
  return [...entries].sort((a, b) => b.dichiarazione.length - a.dichiarazione.length);
}

function appendSanitizedHtml(targetEl, html) {
  const tpl = document.createElement('template');
  tpl.innerHTML = String(html || '');

  // Rimuove elementi attivi/pericolosi, mantenendo la normale formattazione.
  tpl.content.querySelectorAll('script, style, iframe, object, embed').forEach((el) => el.remove());

  // Rimuove event handlers inline e URL javascript:
  tpl.content.querySelectorAll('*').forEach((el) => {
    [...el.attributes].forEach((attr) => {
      const name = attr.name.toLowerCase();
      const value = String(attr.value || '').trim().toLowerCase();
      if (name.startsWith('on')) {
        el.removeAttribute(attr.name);
        return;
      }
      if ((name === 'href' || name === 'src') && value.startsWith('javascript:')) {
        el.removeAttribute(attr.name);
      }
    });
  });

  targetEl.appendChild(tpl.content);
}

function replaceTextNodeWithGlossaryLinks(textNode, termsSorted) {
  const text = textNode.textContent;
  if (!text) return new Set();

  const matchedIds = new Set();
  let pos = 0;
  let buf = '';
  const frag = document.createDocumentFragment();
  let anyMatch = false;

  const flushBuf = () => {
    if (buf) {
      frag.appendChild(document.createTextNode(buf));
      buf = '';
    }
  };

  while (pos < text.length) {
    let found = null;
    for (const entry of termsSorted) {
      const t = entry.dichiarazione;
      const len = t.length;
      if (!len || pos + len > text.length) continue;
      if (text.slice(pos, pos + len).toLowerCase() !== t.toLowerCase()) continue;
      if (!isBoundaryAt(text, pos, pos + len)) continue;
      found = { entry, len };
      break;
    }
    if (found) {
      anyMatch = true;
      flushBuf();
      const a = document.createElement('a');
      a.href = `#wiki-glossario-${found.entry.sync_id}`;
      a.className = 'wiki-glossary-term';
      a.textContent = text.slice(pos, pos + found.len);
      frag.appendChild(a);
      matchedIds.add(found.entry.sync_id);
      pos += found.len;
    } else {
      buf += text[pos];
      pos += 1;
    }
  }
  flushBuf();

  if (!anyMatch) return new Set();
  textNode.parentNode.replaceChild(frag, textNode);
  return matchedIds;
}

function collectTextNodes(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const out = [];
  let n = walker.nextNode();
  while (n) {
    out.push(n);
    n = walker.nextNode();
  }
  return out;
}

function buildGlossaryPanel(matchedById) {
  const details = document.createElement('details');
  details.className = 'wiki-glossary-section wiki-glossary-panel';
  details.id = 'wiki-glossario-panel';

  const summary = document.createElement('summary');
  summary.textContent = 'Glossario (termini in questa pagina)';
  details.appendChild(summary);

  const body = document.createElement('div');
  body.className = 'wiki-glossary-panel-body';

  const ordered = [...matchedById.values()].sort((a, b) =>
    (a.nome || a.dichiarazione).localeCompare(b.nome || b.dichiarazione, 'it', { sensitivity: 'base' }),
  );

  for (const entry of ordered) {
    const row = document.createElement('div');
    row.className = 'wiki-glossary-def';
    row.id = `wiki-glossario-${entry.sync_id}`;

    const title = document.createElement('strong');
    title.textContent = entry.nome || entry.dichiarazione;
    row.appendChild(title);

    const sep = document.createTextNode(' · ');
    row.appendChild(sep);

    const desc = document.createElement('span');
    desc.className = 'wiki-glossary-desc';
    appendSanitizedHtml(desc, entry.descrizione || '');
    row.appendChild(desc);

    body.appendChild(row);
  }

  details.appendChild(body);
  return details;
}

/**
 * @param {HTMLElement} container - .wiki-content
 * @param {Array<{sync_id: string, nome: string, dichiarazione: string, descrizione: string}>} rawEntries
 */
export function applyWikiGlossaryToContainer(container, rawEntries) {
  const entries = normalizeEntries(rawEntries);
  if (!entries.length || !container) return;

  const byId = new Map(entries.map((e) => [e.sync_id, e]));
  const termsSorted = sortTermsForMatching(entries);

  const matchedIds = new Set();
  const maxPasses = 48;
  for (let pass = 0; pass < maxPasses; pass += 1) {
    let anyThisPass = false;
    const textNodes = collectTextNodes(container);
    for (const tn of textNodes) {
      if (!container.contains(tn)) continue;
      if (!shouldProcessTextNode(tn, container)) continue;
      const ids = replaceTextNodeWithGlossaryLinks(tn, termsSorted);
      if (ids.size) {
        anyThisPass = true;
        ids.forEach((id) => matchedIds.add(id));
      }
    }
    if (!anyThisPass) break;
  }

  if (!matchedIds.size) return;

  const matchedById = new Map();
  for (const id of matchedIds) {
    const e = byId.get(id);
    if (e) matchedById.set(id, e);
  }
  if (!matchedById.size) return;

  container.appendChild(buildGlossaryPanel(matchedById));
}
