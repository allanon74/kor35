import React, { useEffect, useMemo, useRef, useState } from 'react';
import { X, Send, Heart } from 'lucide-react';
import { resolveMediaUrl, socialMarkStoryViewed, socialReactStory, socialReplyStory } from '../api';

const DEFAULT_DURATION_MS = 6500;
const TEXT_PAGE_DURATION_MS = 4200;

const StoryViewerModal = ({ open, onClose, stories = [], initialIndex = 0, personaggioId, onLogout, onStoryUpdated, onOpenProfile }) => {
  const [idx, setIdx] = useState(initialIndex);
  const [progress, setProgress] = useState(0);
  const [replyText, setReplyText] = useState('');
  const [textPage, setTextPage] = useState(0);
  const rafRef = useRef(null);
  const startRef = useRef(0);

  useEffect(() => {
    if (!open) return;
    setIdx(initialIndex || 0);
    setProgress(0);
    setReplyText('');
    setTextPage(0);
  }, [open, initialIndex]);

  const story = stories[idx] || null;
  const mediaUrl = useMemo(() => resolveMediaUrl(story?.media), [story?.media]);
  const isVideo = useMemo(() => {
    const u = String(story?.media || '').toLowerCase();
    return u.endsWith('.mp4') || u.endsWith('.webm') || u.endsWith('.mov') || u.includes('video');
  }, [story?.media]);
  const isTextOnlyStory = !mediaUrl && !!String(story?.testo || '').trim();

  const textPages = useMemo(() => {
    const text = String(story?.testo || '').trim();
    if (!text) return [];
    const textSize = Math.max(12, Math.min(56, Number(story?.text_size || 22)));
    const linesPerPage = isTextOnlyStory ? 11 : 6;
    const charsPerLine = Math.max(
      14,
      Math.floor((isTextOnlyStory ? 34 : 26) * (22 / textSize))
    );
    const approxLimit = Math.max(90, linesPerPage * charsPerLine);
    if (text.length <= approxLimit) return [text];
    const words = text.split(/\s+/);
    const pages = [];
    let curr = '';
    for (const w of words) {
      const next = curr ? `${curr} ${w}` : w;
      if (next.length > approxLimit) {
        pages.push(curr);
        curr = w;
      } else {
        curr = next;
      }
    }
    if (curr) pages.push(curr);
    return pages.length > 0 ? pages : [text];
  }, [story?.testo, story?.text_size, isTextOnlyStory]);

  useEffect(() => {
    setTextPage(0);
  }, [story?.id]);

  const goNext = () => {
    if (idx < stories.length - 1) {
      setIdx((i) => i + 1);
      setProgress(0);
      setReplyText('');
      return;
    }
    onClose?.();
  };

  const goPrev = () => {
    if (idx > 0) {
      setIdx((i) => i - 1);
      setProgress(0);
      setReplyText('');
      return;
    }
    onClose?.();
  };

  // Mark viewed on story change
  useEffect(() => {
    if (!open || !story?.id) return;
    if (story.viewed_by_me) return;
    socialMarkStoryViewed(story.id, personaggioId, onLogout)
      .then(() => onStoryUpdated?.({ storyId: story.id, patch: { viewed_by_me: true } }))
      .catch((err) => {
        console.error('Errore mark viewed story', err);
        console.warn(
          '[Stories][Viewed] Verifica backend /api/social/stories/<id>/viewed/ (possibile errore in auto-conversione).',
          { storyId: story?.id, personaggioId }
        );
      });
  }, [open, story?.id]);

  // Progress timer
  useEffect(() => {
    if (!open || !story) return;
    const pageCount = Math.max(1, textPages.length);
    const duration = isTextOnlyStory
      ? Math.max(DEFAULT_DURATION_MS, pageCount * TEXT_PAGE_DURATION_MS)
      : DEFAULT_DURATION_MS;
    startRef.current = performance.now();
    const tick = (t) => {
      const elapsed = t - startRef.current;
      const p = Math.min(1, elapsed / duration);
      setProgress(p);
      if (isTextOnlyStory && pageCount > 1) {
        const nextPage = Math.min(pageCount - 1, Math.floor(elapsed / TEXT_PAGE_DURATION_MS));
        setTextPage((prev) => (prev === nextPage ? prev : nextPage));
      }
      if (p >= 1) {
        rafRef.current = null;
        goNext();
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [open, idx, story?.id, isTextOnlyStory, textPages.length]);

  if (!open) return null;

  const renderStoryText = (text, tags = []) => {
    if (!text) return null;
    const mapById = new Map((tags || []).map((t) => [String(t.personaggio_id), t.personaggio__nome || `#${t.personaggio_id}`]));

    const parts = [];
    const mentionRegex = /@([A-Za-z0-9_]+)/g;
    let last = 0;
    let m;
    while ((m = mentionRegex.exec(text)) !== null) {
      const start = m.index;
      const end = mentionRegex.lastIndex;
      const token = m[1];
      if (start > last) parts.push({ type: 'text', value: text.slice(last, start) });
      if (/^\d+$/.test(token) && mapById.has(token)) {
        parts.push({ type: 'mention', id: Number(token), label: mapById.get(token), raw: m[0] });
      } else {
        parts.push({ type: 'text', value: m[0] });
      }
      last = end;
    }
    if (last < text.length) parts.push({ type: 'text', value: text.slice(last) });

    const hashtagRegex = /(^|[\s.,;:!?()[\]{}])#([A-Za-z0-9_]{2,40})/g;
    const renderWithHashtags = (value, keyPrefix) => {
      const chunks = [];
      let hl = 0;
      let h;
      while ((h = hashtagRegex.exec(value)) !== null) {
        const full = h[0];
        const lead = h[1] || '';
        const tag = h[2];
        const start = h.index;
        const hashIndex = start + lead.length;
        if (start > hl) chunks.push(<React.Fragment key={`${keyPrefix}-t-${hl}`}>{value.slice(hl, start)}</React.Fragment>);
        if (lead) chunks.push(<React.Fragment key={`${keyPrefix}-l-${start}`}>{lead}</React.Fragment>);
        chunks.push(
          <span key={`${keyPrefix}-h-${hashIndex}-${tag}`} className="text-fuchsia-200 font-semibold">
            #{tag}
          </span>
        );
        hl = start + full.length;
      }
      if (hl < value.length) chunks.push(<React.Fragment key={`${keyPrefix}-r-${hl}`}>{value.slice(hl)}</React.Fragment>);
      return chunks;
    };

    return (
      <span className="whitespace-pre-wrap">
        {parts.map((p, i) =>
          p.type === 'mention' ? (
            <button
              key={`sm-${i}-${p.id}`}
              type="button"
              onClick={() => onOpenProfile?.(p.id)}
              className="underline decoration-dotted text-amber-200 hover:text-amber-50"
              title={`Apri profilo ${p.label}`}
            >
              @{p.label}
            </button>
          ) : (
            <React.Fragment key={`st-${i}`}>{renderWithHashtags(p.value, `st-${i}`)}</React.Fragment>
          )
        )}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-80 bg-black/80 backdrop-blur-sm flex items-center justify-center p-2">
      <div className="w-full max-w-md h-[92vh] rounded-2xl overflow-hidden border border-amber-300/25 bg-[#07040a] shadow-2xl flex flex-col">
        <div className="p-3 border-b border-amber-300/15 bg-black/40">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="text-sm font-bold text-amber-100 truncate">{story?.autore_nome || 'Story'}</div>
              <div className="h-1 mt-2 rounded-full bg-white/10 overflow-hidden">
                <div className="h-full bg-linear-to-r from-fuchsia-400 via-amber-300 to-rose-400" style={{ width: `${Math.round(progress * 100)}%` }} />
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/10 text-white/80 hover:text-white"
              title="Chiudi"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 relative">
          <button
            type="button"
            onClick={goPrev}
            className="absolute inset-y-0 left-0 w-1/3 z-10"
            title="Precedente"
          />
          <button
            type="button"
            onClick={goNext}
            className="absolute inset-y-0 right-0 w-1/3 z-10"
            title="Successiva"
          />

          <div className="absolute inset-0 flex items-center justify-center bg-black">
            {mediaUrl ? (
              isVideo ? (
                <video
                  src={mediaUrl}
                  className="w-full h-full object-contain"
                  playsInline
                  autoPlay
                  muted
                />
              ) : (
                <img src={mediaUrl} alt="story" className="w-full h-full object-contain" />
              )
            ) : (
              <div className="w-full h-full bg-linear-to-br from-[#23112d] via-[#140a1d] to-[#07040a]" />
            )}
          </div>

          {story?.testo && (
            <div className={isTextOnlyStory ? 'absolute inset-0 p-6 flex items-center justify-center' : 'absolute bottom-16 left-0 right-0 p-4'}>
              <div
                className={
                  isTextOnlyStory
                    ? 'w-full h-full rounded-2xl bg-black/25 border border-white/10 p-6 text-white flex items-center justify-center text-center'
                    : 'rounded-xl bg-black/55 border border-white/10 p-3 text-white'
                }
              >
                <div
                  key={`page-${story?.id}-${textPage}`}
                  className="animate-[fadeIn_260ms_ease-out]"
                  style={{
                    fontSize: `${Math.max(12, Math.min(56, Number(story?.text_size || 22)))}px`,
                    lineHeight: isTextOnlyStory ? 1.35 : 1.25,
                    maxWidth: isTextOnlyStory ? '100%' : 'none',
                  }}
                >
                  {renderStoryText(textPages[textPage] || story.testo, story.tags || [])}
                </div>
              </div>
              {textPages.length > 1 && (
                <div className={isTextOnlyStory ? 'absolute bottom-6 left-0 right-0' : 'absolute -bottom-2 left-4 right-4'}>
                  <div className="mx-auto w-fit rounded-full bg-black/45 border border-white/15 px-3 py-1 text-xs text-white/85">
                    Pagina {textPage + 1}/{textPages.length}
                  </div>
                </div>
              )}
            </div>
          )}

          {isTextOnlyStory && textPages.length > 1 && (
            <div className="absolute top-16 left-0 right-0 flex items-center justify-center gap-1.5 px-6">
              {textPages.map((_, pageIdx) => (
                <span
                  key={`tp-dot-${pageIdx}`}
                  className={`h-1.5 rounded-full transition-all ${
                    pageIdx === textPage ? 'w-5 bg-white/95' : 'w-2 bg-white/35'
                  }`}
                />
              ))}
            </div>
          )}
        </div>

        {!isTextOnlyStory && (
          <div className="p-3 border-t border-amber-300/15 bg-black/40">
            <div className="flex items-center gap-2 mb-2">
              {['❤️', '🔥', '✨', '😂', '😮'].map((e) => (
                <button
                  key={`react-${e}`}
                  type="button"
                  onClick={async () => {
                    if (!story?.id) return;
                    try {
                      await socialReactStory(story.id, e, personaggioId, onLogout);
                      onStoryUpdated?.({ storyId: story.id, patch: { my_reaction: e, reacted_by_me: true } });
                    } catch {}
                  }}
                  className="px-2 py-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-white text-sm"
                  title={`Reagisci ${e}`}
                >
                  {e}
                </button>
              ))}
              <div className="flex-1" />
              <div className="text-xs text-white/60 inline-flex items-center gap-1">
                <Heart size={14} /> {Number(story?.reactions_count || 0)}
              </div>
            </div>

            <div className="flex items-end gap-2">
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                rows={1}
                placeholder="Rispondi (invia DM all'autore)..."
                className="flex-1 resize-none rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-white/40 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40"
              />
              <button
                type="button"
                onClick={async () => {
                  const t = (replyText || '').trim();
                  if (!t || !story?.id) return;
                  try {
                    await socialReplyStory(story.id, t, true, personaggioId, onLogout);
                    setReplyText('');
                  } catch {}
                }}
                className="px-3 py-2 rounded-xl bg-fuchsia-600 hover:bg-fuchsia-500 text-white font-semibold inline-flex items-center gap-2"
                title="Invia risposta"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StoryViewerModal;

