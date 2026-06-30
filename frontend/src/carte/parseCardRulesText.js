/**
 * Tokenizza testo regole con keyword esatte o parametrizzate ([X], [Y], …).
 */

const DEFAULT_MAX_LINE = 90;
const PLACEHOLDER_RE = /\[([A-Z]+)\]/g;

function compareFold(a, b) {
  return a.localeCompare(b, undefined, { sensitivity: 'accent' }) === 0;
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function escapeLiteralFlexibleWs(literal) {
  return escapeRegex(literal).replace(/\\ /g, '\\s+');
}

function compileKeywordTemplate(template) {
  const names = [];
  let pattern = '';
  let last = 0;
  const re = /\[([A-Z]+)\]/g;
  let m;
  while ((m = re.exec(template)) !== null) {
    const literal = template.slice(last, m.index);
    if (literal) pattern += escapeLiteralFlexibleWs(literal);
    names.push(m[1]);
    pattern += '(-?\\d+|\\S+)';
    last = m.index + m[0].length;
  }
  if (last < template.length) {
    pattern += escapeRegex(template.slice(last));
  }
  return {
    regex: new RegExp(`^${pattern}`, 'i'),
    names,
  };
}

export function keywordHaParametri(text) {
  return PLACEHOLDER_RE.test(text || '');
}

export function substituisciParametriKeyword(testo, params) {
  if (!testo || !params) return testo || '';
  return testo.replace(/\[([A-Z]+)\]/g, (_, name) => (
    params[name] !== undefined ? String(params[name]) : `[${name}]`
  ));
}

export function risolviTestiKeyword(kw, params) {
  return {
    ...kw,
    testo_regola: substituisciParametriKeyword(kw.testo_regola, params),
    reminder_breve: substituisciParametriKeyword(kw.reminder_breve, params),
    params,
  };
}

function tryExactMatch(text, i, term, kw) {
  const slice = text.slice(i, i + term.length);
  if (!compareFold(slice, term)) return null;
  return {
    kw,
    matched: slice,
    index: i,
    len: term.length,
    params: null,
  };
}

function tryTemplateMatch(text, i, template, kw) {
  const { regex, names } = compileKeywordTemplate(template);
  const slice = text.slice(i);
  const m = slice.match(regex);
  if (!m) return null;
  const params = {};
  names.forEach((name, idx) => {
    params[name] = m[idx + 1];
  });
  return {
    kw,
    matched: m[0],
    index: i,
    len: m[0].length,
    params,
  };
}

function buildMatchers(keywords) {
  const matchers = [];
  (keywords || []).forEach((kw) => {
    if (kw.attiva === false) return;
    const templates = [];
    for (const raw of [kw.nome, kw.codice]) {
      const term = (raw || '').trim();
      if (!term) continue;
      if (templates.some((t) => compareFold(t, term))) continue;
      templates.push(term);
      if (keywordHaParametri(term)) {
        matchers.push({
          kind: 'template',
          template: term,
          kw,
          sortLen: term.replace(/\[([A-Z]+)\]/g, '').length + 8,
          priorita: kw.priorita || 0,
        });
      } else {
        matchers.push({
          kind: 'exact',
          term,
          kw,
          sortLen: term.length,
          priorita: kw.priorita || 0,
        });
      }
    }
  });
  matchers.sort((a, b) => b.sortLen - a.sortLen || b.priorita - a.priorita);
  return matchers;
}

function lineBounds(text, index) {
  const start = text.lastIndexOf('\n', index - 1) + 1;
  const endIdx = text.indexOf('\n', index);
  const end = endIdx === -1 ? text.length : endIdx;
  return { start, end, length: end - start };
}

export function canShowInlineReminder(text, matchIndex, matchLen, reminder, maxLineLength = DEFAULT_MAX_LINE) {
  if (!reminder) return false;
  const suffix = ` (*${reminder}*)`;
  const { start, length } = lineBounds(text, matchIndex);
  const posInLine = matchIndex - start;
  return posInLine + matchLen + suffix.length <= maxLineLength && length <= maxLineLength;
}

/**
 * @returns {Array<{kind: 'text', value: string} | {kind: 'keyword', kw: object, matched: string, index: number, len: number, params: object|null}>}
 */
export function tokenizeCardRulesText(text, keywords) {
  if (!text) return [{ kind: 'text', value: '' }];
  const matchers = buildMatchers(keywords);
  if (!matchers.length) return [{ kind: 'text', value: text }];

  const segments = [];
  let i = 0;
  let textBuf = '';

  const flushText = () => {
    if (textBuf) {
      segments.push({ kind: 'text', value: textBuf });
      textBuf = '';
    }
  };

  while (i < text.length) {
    let hit = null;
    for (const entry of matchers) {
      const result = entry.kind === 'template'
        ? tryTemplateMatch(text, i, entry.template, entry.kw)
        : tryExactMatch(text, i, entry.term, entry.kw);
      if (result) {
        hit = result;
        break;
      }
    }
    if (hit) {
      flushText();
      segments.push({
        kind: 'keyword',
        kw: hit.params ? risolviTestiKeyword(hit.kw, hit.params) : hit.kw,
        matched: hit.matched,
        index: hit.index,
        len: hit.len,
        params: hit.params,
      });
      i += hit.len;
    } else {
      textBuf += text[i];
      i += 1;
    }
  }
  flushText();
  return segments;
}
