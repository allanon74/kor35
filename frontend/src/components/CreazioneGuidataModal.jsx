import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { X, Loader2, ChevronLeft, Sparkles, CheckCircle2 } from 'lucide-react';
import {
  getCreazioneGuidataAvvio,
  getCreazioneGuidataPasso,
  applyCreazioneGuidata,
  getCreazioneGuidataProposte,
  getCreazioneGuidataRiepilogo,
  salvaCreazioneGuidataProposte,
  getWikiGlossario,
} from '../api';
import WikiRenderer from './WikiRenderer';
import CreazioneGuidataRiepilogo from './CreazioneGuidataRiepilogo';
import {
  applyModelloAuraToTrail,
  applySceltaToTrail,
  flattenEffettiFromTrail,
  getPresentazione,
  trailSliceToIndex,
} from '../utils/creazioneGuidataWizard';

export default function CreazioneGuidataModal({
  isOpen,
  onClose,
  personaggioId,
  onLogout,
  onApplied,
  canUseWizardTest = false,
}) {
  const [passo, setPasso] = useState(null);
  const [flussoTitolo, setFlussoTitolo] = useState('');
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState(null);
  const [trail, setTrail] = useState([]);
  const [effetti, setEffetti] = useState([]);
  const [wikiGlossary, setWikiGlossary] = useState([]);
  const [riepilogoApply, setRiepilogoApply] = useState(null);
  const [schedaPg, setSchedaPg] = useState(null);
  const [schedaPgLoading, setSchedaPgLoading] = useState(false);
  const [radioSelectedId, setRadioSelectedId] = useState(null);
  const [initialPassoSlug, setInitialPassoSlug] = useState(null);
  const [percorsoPronto, setPercorsoPronto] = useState(false);
  const [modalitaTest, setModalitaTest] = useState(false);
  const [flussoIsTest, setFlussoIsTest] = useState(false);
  const persistTimerRef = useRef(null);
  const skipPersistRef = useRef(false);

  const loadPasso = useCallback(
    async (slug, effettiSnapshot, trailSnapshot) => {
      if (!slug) return;
      setLoading(true);
      setError(null);
      try {
        const data = await getCreazioneGuidataPasso(
          slug,
          personaggioId,
          effettiSnapshot ?? effetti,
          onLogout,
          modalitaTest,
        );
        setPasso(data);
        const pres = getPresentazione(data);
        if (pres === 'radio' || pres === 'radio_abilita') {
          const match = (trailSnapshot ?? trail).find(
            (t) => t.passoSlug === slug && t.sceltaId && t.sceltaId !== 'modello_aura',
          );
          setRadioSelectedId(match?.sceltaId ?? null);
        } else {
          setRadioSelectedId(null);
        }
      } catch (err) {
        setError(err?.message || 'Impossibile caricare il passo.');
        setPasso(null);
      } finally {
        setLoading(false);
      }
    },
    [personaggioId, onLogout, effetti, trail, modalitaTest],
  );

  const refreshScheda = useCallback(
    async (effettiSnapshot) => {
      if (!personaggioId) return;
      setSchedaPgLoading(true);
      try {
        const data = await getCreazioneGuidataRiepilogo(
          personaggioId,
          effettiSnapshot ?? effetti,
          onLogout,
        );
        setSchedaPg(data);
      } catch {
        /* non bloccare il wizard */
      } finally {
        setSchedaPgLoading(false);
      }
    },
    [personaggioId, effetti, onLogout],
  );

  const persistProposte = useCallback(
    (nextTrail, nextEff) => {
      if (skipPersistRef.current || !personaggioId || riepilogoApply) return;
      if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
      persistTimerRef.current = setTimeout(() => {
        salvaCreazioneGuidataProposte(personaggioId, nextEff, nextTrail, onLogout).catch(() => {});
      }, 600);
    },
    [personaggioId, onLogout, riepilogoApply],
  );

  useEffect(
    () => () => {
      if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    },
    [],
  );

  const syncTrail = useCallback(
    (nextTrail) => {
      const nextEff = flattenEffettiFromTrail(nextTrail);
      setTrail(nextTrail);
      setEffetti(nextEff);
      setPercorsoPronto(false);
      refreshScheda(nextEff);
      persistProposte(nextTrail, nextEff);
    },
    [refreshScheda, persistProposte],
  );

  useEffect(() => {
    if (!isOpen || !personaggioId) return undefined;
    let cancelled = false;
    const init = async () => {
      setTrail([]);
      setEffetti([]);
      setRiepilogoApply(null);
      setPercorsoPronto(false);
      refreshScheda([]);
      setLoading(true);
      setError(null);
      try {
        const [avvio, gloss, proposte] = await Promise.all([
          getCreazioneGuidataAvvio(personaggioId, [], onLogout, modalitaTest),
          getWikiGlossario().catch(() => []),
          getCreazioneGuidataProposte(personaggioId, onLogout).catch(() => ({
            trail: [],
            effetti: [],
          })),
        ]);
        if (cancelled) return;
        setWikiGlossary(Array.isArray(gloss) ? gloss : []);
        setFlussoTitolo(avvio?.flusso?.titolo || 'Creazione guidata');
        setFlussoIsTest(!!avvio?.flusso?.modalita_test);
        const initial = avvio?.passo;
        const savedTrail = Array.isArray(proposte?.trail) ? proposte.trail : [];

        if (initial?.slug) {
          setInitialPassoSlug(initial.slug);
        }

        if (savedTrail.length > 0) {
          skipPersistRef.current = true;
          const nextEff = flattenEffettiFromTrail(savedTrail);
          setTrail(savedTrail);
          setEffetti(nextEff);
          refreshScheda(nextEff);
          const last = savedTrail[savedTrail.length - 1];
          const slug = last?.passoSlug || initial?.slug;
          if (slug) {
            await loadPasso(slug, nextEff, savedTrail);
          }
          skipPersistRef.current = false;
        } else if (initial?.slug) {
          setPasso(initial);
          const pres = getPresentazione(initial);
          if (pres === 'radio' || pres === 'radio_abilita') setRadioSelectedId(null);
        } else {
          setError('Percorso non configurato (manca il passo iniziale).');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || 'Nessun percorso di creazione guidata attivo.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    init();
    return () => {
      cancelled = true;
    };
    // refreshScheda volutamente escluso: cambierebbe a ogni scelta e resetterebbe il trail
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, personaggioId, onLogout, modalitaTest]);


  const doApply = async (effettiToApply) => {
    setApplying(true);
    setError(null);
    try {
      const result = await applyCreazioneGuidata(personaggioId, effettiToApply, onLogout);
      setRiepilogoApply(result);
      await refreshScheda([]);
      if (onApplied) onApplied(result);
    } catch (err) {
      setError(err?.message || "Errore durante l'applicazione delle scelte.");
    } finally {
      setApplying(false);
    }
  };

  const commitScelta = async (scelta) => {
    const { trail: nextTrail, effetti: nextEffetti, navigareSlug, fine } = applySceltaToTrail(
      trail,
      passo,
      scelta,
    );
    syncTrail(nextTrail);

    if (fine) {
      syncTrail(nextTrail);
      setPercorsoPronto(true);
      return;
    }

    if (navigareSlug) {
      await loadPasso(navigareSlug, nextEffetti, nextTrail);
    } else if (scelta?.tipo_azione !== 'fine') {
      await loadPasso(passo?.slug, nextEffetti, nextTrail);
    }
  };

  const jumpToTrailIndex = async (index) => {
    const { trail: sliced, effetti: eff } = trailSliceToIndex(trail, index);
    syncTrail(sliced);
    const targetSlug = sliced[index]?.passoSlug;
    if (targetSlug) {
      await loadPasso(targetSlug, eff, sliced);
    }
  };

  const handleModelloAuraSelect = async (modello) => {
    if (!modello?.disponibile || !passo) return;
    const { trail: nextTrail, effetti: nextEff } = applyModelloAuraToTrail(
      trail,
      passo,
      modello.sync_id,
      modello.nome,
    );
    syncTrail(nextTrail);
    await loadPasso(passo.slug, nextEff, nextTrail);
  };

  const scelte = useMemo(() => {
    const list = Array.isArray(passo?.scelte) ? [...passo.scelte] : [];
    return list.sort((a, b) => (a.ordine || 0) - (b.ordine || 0));
  }, [passo?.scelte]);

  const presentazione = getPresentazione(passo);
  const widgetFondo = passo?.widget_fondo;

  const selectedModelloSyncId = useMemo(() => {
    const entry = trail.find(
      (t) => t.passoSlug === passo?.slug && t.sceltaId === 'modello_aura',
    );
    const eff = entry?.effetti?.find((e) => e.tipo === 'seleziona_modello_aura');
    return eff?.modello_aura_sync_id || null;
  }, [trail, passo?.slug]);

  if (!isOpen) return null;

  const renderSceltaButton = (s, className = '') => (
    <button
      key={s.id}
      type="button"
      disabled={applying}
      onClick={() => commitScelta(s)}
      className={`text-left px-4 py-3 rounded-lg border transition-colors disabled:opacity-50 ${className}`}
    >
      <span className="font-semibold text-white block">{s.etichetta}</span>
      {s.descrizione ? (
        <span className="text-sm text-gray-400 block mt-1">{s.descrizione}</span>
      ) : null}
    </button>
  );

  const renderScelte = () => {
    if (scelte.length === 0) {
      return <p className="text-sm text-gray-500">Nessuna scelta configurata per questo passo.</p>;
    }

    if (presentazione === 'si_no' && scelte.length >= 2) {
      const [a, b, ...rest] = scelte;
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {renderSceltaButton(
              a,
              'border-gray-600 bg-gray-800 hover:bg-emerald-900/30 hover:border-emerald-500',
            )}
            {renderSceltaButton(
              b,
              'border-gray-600 bg-gray-800 hover:bg-rose-900/30 hover:border-rose-500',
            )}
          </div>
          {rest.map((s) =>
            renderSceltaButton(
              s,
              'w-full border-gray-600 bg-gray-800 hover:bg-indigo-900/40 hover:border-indigo-500',
            ),
          )}
        </div>
      );
    }

    if (presentazione === 'radio' || presentazione === 'radio_abilita') {
      return (
        <div className="space-y-2" role="radiogroup">
          {scelte.map((s) => {
            const checked = radioSelectedId === s.id;
            return (
              <label
                key={s.id}
                className={`flex gap-3 items-start px-4 py-3 rounded-lg border cursor-pointer transition-colors ${
                  checked
                    ? 'border-indigo-500 bg-indigo-950/50'
                    : 'border-gray-600 bg-gray-800 hover:border-gray-500'
                }`}
              >
                <input
                  type="radio"
                  name={`wizard-radio-${passo?.slug}`}
                  className="mt-1"
                  checked={checked}
                  disabled={applying}
                  onChange={() => {
                    setRadioSelectedId(s.id);
                    commitScelta(s);
                  }}
                />
                <span>
                  <span className="font-semibold text-white block">{s.etichetta}</span>
                  {s.descrizione ? (
                    <span className="text-sm text-gray-400 block mt-1">{s.descrizione}</span>
                  ) : null}
                </span>
              </label>
            );
          })}
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {scelte.map((s) =>
          renderSceltaButton(
            s,
            'w-full border-gray-600 bg-gray-800 hover:bg-indigo-900/40 hover:border-indigo-500',
          ),
        )}
      </div>
    );
  };

  const renderWidgetModelloAura = () => {
    if (!widgetFondo || widgetFondo.tipo !== 'modello_aura') return null;
    const gruppi = widgetFondo.gruppi || [];
    return (
      <div className="mt-6 pt-4 border-t border-gray-700 space-y-4">
        <p className="text-xs uppercase tracking-wider text-violet-400 font-bold">
          Modello di aura
        </p>
        {gruppi.map((g) => (
          <div key={g.aura_sigla} className={g.aura_attiva ? '' : 'opacity-70'}>
            <p className="text-sm font-semibold text-gray-300 mb-2">
              {g.aura_nome}
              {g.caratteristica_nome ? (
                <span className="text-gray-500 font-normal ml-2">
                  (talenti {g.caratteristica_nome}: {g.talenti})
                </span>
              ) : null}
            </p>
            <div className="space-y-1">
              {(g.modelli || []).map((m) => {
                const selected = selectedModelloSyncId === m.sync_id;
                const disabled = !m.disponibile;
                return (
                  <button
                    key={m.sync_id}
                    type="button"
                    disabled={disabled || applying}
                    onClick={() => handleModelloAuraSelect(m)}
                    className={`w-full text-left px-3 py-2 rounded-lg border text-sm ${
                      disabled
                        ? 'border-gray-800 bg-gray-900/50 text-gray-500 cursor-not-allowed'
                        : selected
                          ? 'border-violet-500 bg-violet-950/40 text-white'
                          : 'border-gray-600 bg-gray-800 hover:border-violet-500 text-gray-200'
                    }`}
                  >
                    <span className="font-medium">{m.nome}</span>
                    {disabled && m.motivo_blocco ? (
                      <span className="block text-xs text-gray-500 mt-0.5 italic">
                        {m.motivo_blocco}
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-0 md:p-4">
      <div className="absolute inset-0 bg-black/85 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full h-full md:h-auto md:max-h-[92vh] md:max-w-3xl flex flex-col text-gray-100">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wider text-indigo-400">
              {flussoTitolo}
              {flussoIsTest ? (
                <span className="ml-2 text-amber-400 normal-case">(modalità test)</span>
              ) : null}
            </p>
            <h2 className="text-lg font-bold flex items-center gap-2 truncate">
              <Sparkles size={18} className="text-indigo-400 shrink-0" />
              {riepilogoApply ? 'Riepilogo percorso' : passo?.titolo || 'Creazione guidata'}
            </h2>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {canUseWizardTest && !riepilogoApply && (
              <label className="flex items-center gap-1.5 text-[10px] text-amber-300/90 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={modalitaTest}
                  onChange={(e) => setModalitaTest(e.target.checked)}
                  className="rounded border-amber-600 bg-gray-800 text-amber-500"
                />
                Flusso test
              </label>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-800 text-gray-400"
              aria-label="Chiudi"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {!riepilogoApply && (
          <CreazioneGuidataRiepilogo riepilogo={schedaPg} loading={schedaPgLoading} />
        )}

        {!riepilogoApply && trail.length > 0 && (
          <div className="px-4 py-2 border-b border-gray-800 bg-gray-950/80 shrink-0 overflow-x-auto">
            <p className="text-[10px] uppercase text-gray-500 mb-1">Percorso scelto</p>
            <ol className="flex flex-wrap gap-1 items-center text-xs">
              {trail.map((t, idx) => (
                <li key={`${t.passoSlug}-${t.sceltaId}-${idx}`} className="flex items-center gap-1">
                  {idx > 0 ? <span className="text-gray-600">›</span> : null}
                  <button
                    type="button"
                    className="px-2 py-1 rounded bg-indigo-900/50 text-indigo-200 hover:bg-indigo-800 border border-indigo-700/50 max-w-[140px] truncate"
                    title={t.sceltaEtichetta}
                    onClick={() => jumpToTrailIndex(idx)}
                  >
                    {t.sceltaEtichetta || t.passoTitolo}
                  </button>
                </li>
              ))}
            </ol>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {loading && (
            <div className="flex flex-col items-center py-16 gap-3">
              <Loader2 className="animate-spin text-indigo-400" size={40} />
              <p className="text-gray-400 text-sm">Caricamento...</p>
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-lg border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}

          {riepilogoApply && !loading && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex items-start gap-2 text-emerald-300">
                <CheckCircle2 size={22} className="shrink-0 mt-0.5" />
                <p className="text-sm">
                  Percorso applicato sul personaggio. Puoi chiudere e completare il salvataggio.
                </p>
              </div>
              {(riepilogoApply.acquistate || []).length > 0 && (
                <div>
                  <p className="text-xs uppercase text-gray-500 mb-1">Abilità acquistate</p>
                  <ul className="text-sm list-disc pl-5 text-gray-200">
                    {riepilogoApply.acquistate.map((a) => (
                      <li key={a.abilita_id}>{a.abilita_nome}</li>
                    ))}
                  </ul>
                </div>
              )}
              {(riepilogoApply.pendenti || []).length > 0 && (
                <div>
                  <p className="text-xs uppercase text-amber-500 mb-1">Da acquistare</p>
                  <ul className="text-sm list-disc pl-5 text-amber-100">
                    {riepilogoApply.pendenti.map((a) => (
                      <li key={a.abilita_id}>{a.abilita_nome}</li>
                    ))}
                  </ul>
                </div>
              )}
              {(riepilogoApply.modelli_aura || []).length > 0 && (
                <div>
                  <p className="text-xs uppercase text-violet-400 mb-1">Modelli di aura</p>
                  <ul className="text-sm list-disc pl-5 text-gray-200">
                    {riepilogoApply.modelli_aura.map((m) => (
                      <li key={m.sync_id}>{m.nome}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {!riepilogoApply && percorsoPronto && effetti.length > 0 && (
            <p className="mb-3 text-sm text-emerald-300/90 bg-emerald-950/40 border border-emerald-800/60 rounded-lg px-3 py-2">
              Percorso completato. Le scelte sono in bozza: premi{' '}
              <strong>Salva le proposte</strong> per applicarle alla scheda (abilità, era, ecc.).
            </p>
          )}
          {!riepilogoApply && passo && !loading && (
            <div className="space-y-6 animate-fadeIn">
              {passo.immagine_url && (
                <img
                  src={passo.immagine_url}
                  alt=""
                  className="w-full max-h-48 object-cover rounded-lg border border-gray-700"
                />
              )}
              <div className="prose prose-invert prose-sm max-w-none">
                <WikiRenderer content={passo.contenuto || ''} glossaryEntries={wikiGlossary} />
              </div>
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wider text-gray-500">Scegli un&apos;opzione</p>
                {renderScelte()}
              </div>
              {renderWidgetModelloAura()}
            </div>
          )}
        </div>

        <div className="px-4 py-3 border-t border-gray-700 flex flex-wrap justify-between gap-2 shrink-0">
          <div className="flex gap-2">
            {trail.length > 0 && !riepilogoApply && (
              <button
                type="button"
                onClick={async () => {
                  if (trail.length <= 1) {
                    const empty = { trail: [], effetti: [] };
                    syncTrail(empty.trail);
                    if (initialPassoSlug) await loadPasso(initialPassoSlug, [], []);
                  } else {
                    await jumpToTrailIndex(trail.length - 2);
                  }
                }}
                disabled={loading || applying}
                className="inline-flex items-center gap-1 px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm disabled:opacity-50"
              >
                <ChevronLeft size={16} />
                Indietro
              </button>
            )}
          </div>
          <div className="flex gap-2">
            {!riepilogoApply && effetti.length > 0 && (
              <button
                type="button"
                disabled={applying || loading}
                onClick={() => doApply(effetti)}
                className="px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-sm font-bold disabled:opacity-50"
              >
                {applying ? 'Salvataggio...' : 'Salva le proposte'}
              </button>
            )}
            <button type="button" onClick={onClose} className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">
              {riepilogoApply ? 'Chiudi' : 'Esci dal percorso'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
