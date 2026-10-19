import React from 'react';
import { HASHTAG_INLINE_REGEX, normalizeHashtagFilter } from '../utils/hashtags';

const MENTION_REGEX = /@([A-Za-z0-9_]+)/g;

function mappaTag(tags) {
  const byId = new Map();
  const byToken = new Map();
  for (const tag of tags || []) {
    const id = String(tag.personaggio_id);
    const label = tag.personaggio__nome || `#${id}`;
    const entry = { id: Number(tag.personaggio_id), label };
    byId.set(id, entry);
    byToken.set(id, entry);
    const underscored = label.replace(/\s+/g, '_');
    if (underscored) byToken.set(underscored, entry);
  }
  return { byId, byToken };
}

function risolviMention(token, byId, byToken) {
  return (/^\d+$/.test(token) ? byId.get(token) : null) || byToken.get(token) || null;
}

function renderHashtags(value, keyPrefix, onHashtag) {
  const chunks = [];
  let last = 0;
  let match;
  const regex = new RegExp(HASHTAG_INLINE_REGEX.source, HASHTAG_INLINE_REGEX.flags);
  while ((match = regex.exec(value)) !== null) {
    const full = match[0];
    const lead = match[1] || '';
    const tag = match[2];
    const start = match.index;
    if (start > last) {
      chunks.push(<React.Fragment key={`${keyPrefix}-t-${last}`}>{value.slice(last, start)}</React.Fragment>);
    }
    if (lead) chunks.push(<React.Fragment key={`${keyPrefix}-l-${start}`}>{lead}</React.Fragment>);
    const normalizzato = normalizeHashtagFilter(tag);
    chunks.push(
      <button
        key={`${keyPrefix}-h-${start}-${normalizzato}`}
        type="button"
        onClick={() => onHashtag?.(normalizzato)}
        className="underline decoration-dotted text-fuchsia-300 hover:text-fuchsia-100"
      >
        #{tag}
      </button>
    );
    last = start + full.length;
  }
  if (last < value.length) {
    chunks.push(<React.Fragment key={`${keyPrefix}-r-${last}`}>{value.slice(last)}</React.Fragment>);
  }
  return chunks;
}

/**
 * Testo InstaFame con @personaggio e #hashtag cliccabili.
 */
export default function InstafameRichText({ text, tags = [], onHashtag, onMention, className = '' }) {
  if (!text) return null;
  const { byId, byToken } = mappaTag(tags);
  const parts = [];
  let last = 0;
  let match;
  const regex = new RegExp(MENTION_REGEX.source, MENTION_REGEX.flags);
  while ((match = regex.exec(text)) !== null) {
    const start = match.index;
    const end = regex.lastIndex;
    if (start > last) parts.push({ type: 'text', value: text.slice(last, start) });
    const mention = risolviMention(match[1], byId, byToken);
    if (mention) parts.push({ type: 'mention', ...mention, raw: match[0] });
    else parts.push({ type: 'text', value: match[0] });
    last = end;
  }
  if (last < text.length) parts.push({ type: 'text', value: text.slice(last) });

  return (
    <span className={`whitespace-pre-wrap ${className}`}>
      {parts.map((part, index) =>
        part.type === 'mention' ? (
          <button
            key={`m-${index}-${part.id}`}
            type="button"
            onClick={() => onMention?.(part.id)}
            className="underline decoration-dotted text-amber-300 hover:text-amber-100"
          >
            @{part.label}
          </button>
        ) : (
          <React.Fragment key={`t-${index}`}>{renderHashtags(part.value, `t-${index}`, onHashtag)}</React.Fragment>
        )
      )}
    </span>
  );
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Inserisce ancore #hashtag- e #mention- nel testo fuori dai tag HTML,
 * così il sanitizer dell'articolo le conserva. Le classi usano il prefisso
 * `kor-`: la policy HTML tiene solo classi che iniziano con wiki, rich, kor o ql.
 */
export function decoraTokenInstafameHtml(html, tags = []) {
  if (!html) return '';
  const { byId, byToken } = mappaTag(tags);
  return String(html).replace(/(^|>)([^<]*)/g, (_full, lead, text) => {
    let out = text.replace(new RegExp(MENTION_REGEX.source, 'g'), (raw, token) => {
      const mention = risolviMention(token, byId, byToken);
      if (!mention) return raw;
      return `<a href="#mention-${mention.id}" class="kor-instafame-mention">@${escapeHtml(mention.label)}</a>`;
    });
    out = out.replace(new RegExp(HASHTAG_INLINE_REGEX.source, 'g'), (full, delimiter, tag) => {
      const normalizzato = normalizeHashtagFilter(tag);
      if (normalizzato.length < 2) return full;
      return `${delimiter}<a href="#hashtag-${normalizzato}" class="kor-instafame-hashtag">#${escapeHtml(tag)}</a>`;
    });
    return lead + out;
  });
}

export function gestisciClickTokenInstafame(event, { onHashtag, onMention } = {}) {
  const link = event.target?.closest?.('a');
  if (!link) return false;
  const href = link.getAttribute('href') || '';
  if (href.startsWith('#hashtag-')) {
    event.preventDefault();
    onHashtag?.(href.slice('#hashtag-'.length));
    return true;
  }
  if (href.startsWith('#mention-')) {
    event.preventDefault();
    const id = Number(href.slice('#mention-'.length));
    if (Number.isFinite(id)) onMention?.(id);
    return true;
  }
  return false;
}
