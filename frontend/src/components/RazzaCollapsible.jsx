import React, { useMemo, useState, useCallback, useEffect } from 'react';
import { X, Loader2, ChevronDown } from 'lucide-react';
import PunteggioDisplay from './PunteggioDisplay';
import { useOptimisticAcquireAbilita } from '../hooks/useGameData';

const PREFIX_ARCH = 'archetipo - ';
const PREFIX_FORMA = 'forma - ';

/** Nome mostrato senza prefissi "Archetipo - " / "Forma - " */
export function stripRazzaPrefix(nome) {
  if (!nome) return '';
  const s = nome.trim();
  const low = s.toLowerCase();
  if (low.startsWith(PREFIX_ARCH)) return s.slice(PREFIX_ARCH.length).trim();
  if (low.startsWith(PREFIX_FORMA)) return s.slice(PREFIX_FORMA.length).trim();
  return s;
}

function isTrattoAuraInnita(ab) {
  return (
    ab?.is_tratto_aura &&
    ab?.aura_riferimento &&
    String(ab.aura_riferimento.sigla || '').toUpperCase() === 'AIN'
  );
}

/** Punteggi caratteristica escludendo i contributi punteggio_acquisito delle abilità indicate */
function caratteristicheEscludendoAbilita(punteggiBase, punteggiList, abilitaPossedute, excludeIds) {
  const caNames = new Set((punteggiList || []).filter((p) => p.tipo === 'CA').map((p) => p.nome));
  const scores = {};
  for (const [k, v] of Object.entries(punteggiBase || {})) {
    if (caNames.has(k)) scores[k] = Number(v) || 0;
  }
  const excl = new Set(excludeIds || []);
  for (const ab of abilitaPossedute || []) {
    if (!ab?.id || !excl.has(ab.id)) continue;
    for (const link of ab.punteggi_assegnati || []) {
      const nom = link?.punteggio?.nome;
      if (nom && Object.prototype.hasOwnProperty.call(scores, nom)) {
        scores[nom] -= Number(link.valore) || 0;
      }
    }
  }
  return scores;
}

function idsTrattiInnatiSlot(abilitaPossedute, slot) {
  return (abilitaPossedute || [])
    .filter((ab) => {
      if (!isTrattoAuraInnita(ab)) return false;
      const liv = ab.livello_riferimento;
      if (slot === 'archetipo') return liv === 0 || liv === 1;
      if (slot === 'forma') return liv === 2;
      return false;
    })
    .map((ab) => ab.id);
}

/**
 * Un solo record per nome visualizzato (evita doppi "Umano" da duplicati in DB o livelli diversi).
 */
function dedupeArchetipiPerNomeVisualizzato(list, selectedId) {
  const byKey = new Map();
  const score = (t) => {
    let s = 0;
    if (selectedId && t.id === selectedId) s += 100;
    if (t.livello_riferimento === 0) s += 10;
    return s;
  };
  for (const t of list) {
    const key = stripRazzaPrefix(t.nome).toLowerCase().trim() || String(t.id);
    const cur = byKey.get(key);
    if (!cur || score(t) > score(cur)) byKey.set(key, t);
  }
  return Array.from(byKey.values());
}

export function useRazzaDisplay(abilitaPossedute) {
  return useMemo(() => {
    const arch = (abilitaPossedute || []).find(
      (ab) => isTrattoAuraInnita(ab) && (ab.livello_riferimento === 0 || ab.livello_riferimento === 1)
    );
    const forma = (abilitaPossedute || []).find((ab) => isTrattoAuraInnita(ab) && ab.livello_riferimento === 2);
    const archetipoLabel = arch ? stripRazzaPrefix(arch.nome) : 'Umano';
    const formaLabel = forma ? stripRazzaPrefix(forma.nome) : null;
    return { archetipoLabel, formaLabel, archetipoTrait: arch, formaTrait: forma };
  }, [abilitaPossedute]);
}

function AccentBadge({ accent, children }) {
  const cls =
    accent === 'forma'
      ? 'text-cyan-200 bg-cyan-950/30 border-cyan-700/50'
      : 'text-amber-200 bg-amber-950/30 border-amber-700/50';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] uppercase tracking-wider ${cls}`}>
      {children}
    </span>
  );
}

function ExpandableDescrizione({ descrizione }) {
  if (!descrizione) return null;
  return (
    <details className="mt-2 group">
      <summary className="list-none cursor-pointer select-none inline-flex items-center gap-1 text-[11px] text-slate-300/80 hover:text-slate-200 [&::-webkit-details-marker]:hidden">
        <span>Descrizione</span>
        <ChevronDown size={14} className="transition-transform group-open:rotate-180" />
      </summary>
      <div
        className="mt-2 text-sm text-slate-200/90 prose prose-invert prose-sm max-w-none leading-relaxed prose-p:my-1.5 prose-headings:text-slate-100"
        dangerouslySetInnerHTML={{ __html: descrizione }}
      />
    </details>
  );
}

function OptionCard({ nomeDisplay, descrizione, accent, selected, disabled, onClick, loading }) {
  const baseBorder =
    accent === 'forma' ? 'border-slate-700 hover:border-cyan-500/60' : 'border-slate-700 hover:border-amber-500/60';
  const selectedBorder =
    accent === 'forma'
      ? 'border-cyan-600/70 ring-1 ring-cyan-500/40 bg-cyan-950/20'
      : 'border-amber-600/70 ring-1 ring-amber-500/40 bg-amber-950/20';

  return null;
}

export function RazzaModal({
  isOpen,
  onClose,
  personaggioId,
  abilitaPossedute,
  punteggiBase,
  punteggiList,
  auraInnataRecord,
  onLogout,
  onUpdated,
}) {
  const [loadingId, setLoadingId] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('archetipo');
  const acquireMutation = useOptimisticAcquireAbilita();

  useEffect(() => {
    if (!isOpen) {
      setError(null);
      setLoadingId(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e) => {
      if (e.key === 'Escape' && !loadingId) onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, loadingId, onClose]);

  const ainVal = useMemo(() => {
    if (!auraInnataRecord?.nome || !punteggiBase) return 0;
    return Number(punteggiBase[auraInnataRecord.nome]) || 0;
  }, [auraInnataRecord, punteggiBase]);

  const tratti = auraInnataRecord?.tratti_disponibili || [];

  const archetipiAll = useMemo(() => {
    const list = tratti.filter((t) => t.livello_riferimento === 0 || t.livello_riferimento === 1);
    return [...list].sort((a, b) => {
      const la = a.livello_riferimento ?? 0;
      const lb = b.livello_riferimento ?? 0;
      if (la !== lb) return la - lb;
      return String(a.nome || '').localeCompare(String(b.nome || ''), 'it');
    });
  }, [tratti]);

  const formeAll = useMemo(() => tratti.filter((t) => t.livello_riferimento === 2), [tratti]);

  const excludeArchIds = useMemo(() => idsTrattiInnatiSlot(abilitaPossedute, 'archetipo'), [abilitaPossedute]);
  const excludeFormIds = useMemo(() => idsTrattiInnatiSlot(abilitaPossedute, 'forma'), [abilitaPossedute]);

  const scoresArc = useMemo(
    () => caratteristicheEscludendoAbilita(punteggiBase, punteggiList, abilitaPossedute, excludeArchIds),
    [punteggiBase, punteggiList, abilitaPossedute, excludeArchIds]
  );
  const scoresForm = useMemo(
    () => caratteristicheEscludendoAbilita(punteggiBase, punteggiList, abilitaPossedute, excludeFormIds),
    [punteggiBase, punteggiList, abilitaPossedute, excludeFormIds]
  );

  const archetipoSelezionato = useMemo(
    () =>
      (abilitaPossedute || []).find(
        (ab) => isTrattoAuraInnita(ab) && (ab.livello_riferimento === 0 || ab.livello_riferimento === 1)
      ),
    [abilitaPossedute]
  );
  const formaSelezionata = useMemo(
    () => (abilitaPossedute || []).find((ab) => isTrattoAuraInnita(ab) && ab.livello_riferimento === 2),
    [abilitaPossedute]
  );

  const archetipoAbilitato = useCallback(
    (trait) => {
      const liv = trait.livello_riferimento;
      if (liv === 0) return ainVal >= 0;
      if (liv === 1) {
        if (ainVal < 1) return false;
        const nomeC = trait.caratteristica?.nome;
        if (!nomeC) return false;
        return (scoresArc[nomeC] || 0) >= 1;
      }
      return false;
    },
    [ainVal, scoresArc]
  );

  const formaAbilitata = useCallback(
    (trait) => {
      if (ainVal < 2) return false;
      const n1 = trait.caratteristica?.nome;
      const n2 = trait.caratteristica_2?.nome;
      if (!n1 || !n2) return false;
      const v1 = scoresForm[n1] || 0;
      const v2 = scoresForm[n2] || 0;
      if (n1 === n2) return v1 >= 2;
      return v1 >= 1 && v2 >= 1;
    },
    [ainVal, scoresForm]
  );

  const archetipiVisibili = useMemo(() => {
    const deduped = dedupeArchetipiPerNomeVisualizzato(archetipiAll, archetipoSelezionato?.id);
    const selId = archetipoSelezionato?.id;
    return deduped
      .filter((t) => (selId && t.id === selId) || archetipoAbilitato(t))
      .sort((a, b) => {
        const la = a.livello_riferimento ?? 0;
        const lb = b.livello_riferimento ?? 0;
        if (la !== lb) return la - lb;
        return String(a.nome || '').localeCompare(String(b.nome || ''), 'it');
      });
  }, [archetipiAll, archetipoSelezionato?.id, archetipoAbilitato]);

  const formeVisibili = useMemo(() => {
    const selId = formaSelezionata?.id;
    return formeAll
      .filter((t) => (selId && t.id === selId) || formaAbilitata(t))
      .sort((a, b) => String(a.nome || '').localeCompare(String(b.nome || ''), 'it'));
  }, [formeAll, formaSelezionata?.id, formaAbilitata]);

  /** Tratto catalogo Umano (liv.0), per descrizione quando il PG non ha riga DB archetipo */
  const traitUmanoCatalogo = useMemo(
    () =>
      archetipiAll.find(
        (t) =>
          t.livello_riferimento === 0 && stripRazzaPrefix(t.nome).toLowerCase() === 'umano'
      ),
    [archetipiAll]
  );

  const archetipiAltri = useMemo(() => {
    return archetipiVisibili.filter((t) => {
      if (archetipoSelezionato?.id != null && String(t.id) === String(archetipoSelezionato.id))
        return false;
      if (!archetipoSelezionato) {
        const umanoL0 =
          t.livello_riferimento === 0 && stripRazzaPrefix(t.nome).toLowerCase() === 'umano';
        if (umanoL0) return false;
      }
      return true;
    });
  }, [archetipiVisibili, archetipoSelezionato]);

  const formeAltri = useMemo(() => {
    const sid = formaSelezionata?.id;
    return formeVisibili.filter((t) => sid == null || String(t.id) !== String(sid));
  }, [formeVisibili, formaSelezionata?.id]);

  const getRequisitiBadges = useCallback((trait) => {
    if (!trait) return [];
    const liv = trait.livello_riferimento;
    // Archetipo umano (liv 0): nessun badge requisiti
    if (liv === 0) return [];
    // Archetipo liv 1: 1 sulla caratteristica
    if (liv === 1) {
      return trait.caratteristica ? [{ punteggio: trait.caratteristica, value: 1 }] : [];
    }
    // Forma liv 2: badge per una o due caratteristiche
    if (liv === 2) {
      const c1 = trait.caratteristica;
      const c2 = trait.caratteristica_2;
      if (!c1 || !c2) return [];
      if (String(c1?.nome) === String(c2?.nome)) return [{ punteggio: c1, value: 2 }];
      return [
        { punteggio: c1, value: 1 },
        { punteggio: c2, value: 1 },
      ];
    }
    return [];
  }, []);

  const handlePick = async (trait) => {
    setError(null);
    setLoadingId(trait.id);
    try {
      await acquireMutation.mutateAsync({ abilitaId: trait.id, charId: personaggioId });
      // Riallinea in background con i dati server dopo update ottimistico.
      if (onUpdated) onUpdated();
    } catch (e) {
      setError(e.message || 'Selezione non consentita.');
    } finally {
      setLoadingId(null);
    }
  };

  const OptionCardV2 = useCallback(
    ({ trait, accent, selected, showSelect }) => {
      const nomeDisplay = trait ? stripRazzaPrefix(trait.nome) : 'Umano';
      const descrizione = trait?.descrizione || null;
      const badges = getRequisitiBadges(trait);

      const baseBorder =
        accent === 'forma'
          ? 'border-slate-700 hover:border-cyan-500/60'
          : 'border-slate-700 hover:border-amber-500/60';
      const selectedBorder =
        accent === 'forma'
          ? 'border-cyan-600/70 ring-1 ring-cyan-500/40 bg-cyan-950/20'
          : 'border-amber-600/70 ring-1 ring-amber-500/40 bg-amber-950/20';

      const disabledSelect = !trait || !!loadingId;

      return (
        <details
          className={`rounded-lg border px-3 py-3 bg-slate-900 transition-colors ${
            selected ? selectedBorder : baseBorder
          } ${disabledSelect && showSelect ? 'opacity-90' : ''}`}
        >
          <summary className="list-none cursor-pointer select-none [&::-webkit-details-marker]:hidden">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`font-bold text-sm ${selected ? 'text-white' : 'text-slate-100'}`}>
                    {nomeDisplay}
                  </span>
                  {selected && <AccentBadge accent={accent}>Attuale</AccentBadge>}
                </div>
                {badges.length > 0 && (
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {badges.map((b, idx) => (
                      <PunteggioDisplay
                        key={`${b.punteggio?.id || idx}`}
                        punteggio={b.punteggio}
                        value={b.value}
                        size="badge"
                        iconType="inv_circle"
                        displayText="abbr"
                        readOnly={true}
                      />
                    ))}
                  </div>
                )}
              </div>

              {showSelect && trait ? (
                <button
                  type="button"
                  disabled={!!loadingId}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handlePick(trait);
                  }}
                  className={`shrink-0 px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider border ${
                    accent === 'forma'
                      ? 'border-cyan-700/60 text-cyan-200 hover:bg-cyan-950/30'
                      : 'border-amber-700/60 text-amber-200 hover:bg-amber-950/30'
                  } disabled:opacity-60`}
                >
                  Seleziona
                </button>
              ) : null}
            </div>
          </summary>

          {trait?.descrizione ? (
            <div className="mt-3 pt-3 border-t border-slate-800">
              {loadingId === trait.id ? (
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Applico la scelta…
                </div>
              ) : null}
              <div
                className="text-sm text-slate-200/90 prose prose-invert prose-sm max-w-none leading-relaxed prose-p:my-1.5 prose-headings:text-slate-100"
                dangerouslySetInnerHTML={{ __html: descrizione }}
              />
            </div>
          ) : null}
        </details>
      );
    },
    [getRequisitiBadges, handlePick, loadingId]
  );

  if (!isOpen || !auraInnataRecord) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="razza-modal-title"
      onClick={(e) => e.target === e.currentTarget && !loadingId && onClose()}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[92vh] flex flex-col shadow-2xl">
        <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/60 rounded-t-xl shrink-0">
          <div>
            <h3 id="razza-modal-title" className="text-xl font-bold text-amber-400">
              Razza
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Archetipo:{' '}
              <span className="text-amber-200/90">
                {archetipoSelezionato ? stripRazzaPrefix(archetipoSelezionato.nome) : 'Umano'}
              </span>
              {ainVal >= 2 && (
                <>
                  {' '}
                  Forma:{' '}
                  <span className="text-cyan-200/90">
                    {formaSelezionata ? stripRazzaPrefix(formaSelezionata.nome) : 'Nessuna'}
                  </span>
                </>
              )}
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Aura innata: <span className="text-slate-300 font-semibold">{ainVal}</span>
              {ainVal < 2 ? <span className="ml-2">· Le forme si sbloccano a 2</span> : null}
            </p>
          </div>
          <button
            type="button"
            disabled={!!loadingId}
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-full text-slate-400 hover:text-white disabled:opacity-50"
            aria-label="Chiudi"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-4 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="text-sm text-red-300 bg-red-900/50 border border-red-500/50 rounded-md p-2">{error}</div>
          )}

          {/* Segmented control (mobile-friendly) */}
          <div className="sticky top-0 z-10 -mx-4 px-4 py-3 bg-slate-900/95 backdrop-blur border-b border-slate-800">
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setTab('archetipo')}
                className={`px-3 py-2 rounded-lg text-sm font-bold transition-colors border ${
                  tab === 'archetipo'
                    ? 'bg-amber-950/30 border-amber-700/60 text-amber-200'
                    : 'bg-slate-900 border-slate-700 text-slate-200 hover:border-slate-600'
                }`}
              >
                Archetipo
              </button>
              <button
                type="button"
                onClick={() => setTab('forma')}
                disabled={ainVal < 2}
                className={`px-3 py-2 rounded-lg text-sm font-bold transition-colors border ${
                  tab === 'forma'
                    ? 'bg-cyan-950/30 border-cyan-700/60 text-cyan-200'
                    : 'bg-slate-900 border-slate-700 text-slate-200 hover:border-slate-600'
                } ${ainVal < 2 ? 'opacity-50 cursor-not-allowed' : ''}`}
                title={ainVal < 2 ? 'Le forme si sbloccano a Aura innata 2' : undefined}
              >
                Forma
              </button>
            </div>
          </div>

          {tab === 'archetipo' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-wider text-slate-500">Attuale</p>
                <AccentBadge accent="archetipo">Archetipo</AccentBadge>
              </div>
              {archetipoSelezionato ? (
                <OptionCardV2 trait={archetipoSelezionato} accent="archetipo" selected showSelect={false} />
              ) : (
                <OptionCardV2 trait={traitUmanoCatalogo || null} accent="archetipo" selected showSelect={false} />
              )}

              <div className="pt-3 border-t border-slate-800">
                <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Selezionabili</p>
                <div className="space-y-2">
                  {archetipiAltri.length === 0 ? (
                    <p className="text-xs text-slate-500">Nessun altro archetipo selezionabile.</p>
                  ) : (
                    archetipiAltri.map((trait) => (
                      <OptionCardV2
                        key={trait.id}
                        accent="archetipo"
                        trait={trait}
                        selected={false}
                        showSelect={true}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {tab === 'forma' && (
            <div className="space-y-3">
              {ainVal < 2 ? (
                <div className="text-sm text-slate-300 bg-slate-800/40 border border-slate-700 rounded-lg p-3">
                  Le forme sono disponibili solo con <span className="font-semibold text-white">Aura innata 2</span>.
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-xs uppercase tracking-wider text-slate-500">Attuale</p>
                    <AccentBadge accent="forma">Forma</AccentBadge>
                  </div>
                  {formaSelezionata ? (
                    <OptionCardV2 trait={formaSelezionata} accent="forma" selected showSelect={false} />
                  ) : (
                    <div className="text-sm text-slate-300 bg-slate-800/30 border border-slate-700 rounded-lg p-3">
                      Nessuna forma selezionata.
                    </div>
                  )}

                  <div className="pt-3 border-t border-slate-800">
                    <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Selezionabili</p>
                    <div className="space-y-2">
                      {formeAltri.length === 0 ? (
                        <p className="text-xs text-slate-500">Non ci sono altre forme selezionabili.</p>
                      ) : (
                        formeAltri.map((trait) => (
                          <OptionCardV2
                            key={trait.id}
                            accent="forma"
                            trait={trait}
                            selected={false}
                            showSelect={true}
                          />
                        ))
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default RazzaModal;
