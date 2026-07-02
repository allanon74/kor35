import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import {
  RazzaPickerContent,
  stripRazzaPrefix,
  useRazzaDisplay,
} from '../RazzaCollapsible';
import {
  getModelliAura,
  getPunteggiList,
  staffPersonaggioAssegnaAbilita,
  staffPersonaggioRimuoviAbilita,
  staffPersonaggioAssegnaModelloAura,
  staffPersonaggioRimuoviModelloAura,
} from '../../api';

function isTrattoAuraInnita(ab) {
  return (
    ab?.is_tratto_aura
    && ab?.aura_riferimento
    && String(ab.aura_riferimento.sigla || '').toUpperCase() === 'AIN'
  );
}

const StaffRazzaAuraTab = ({
  detail,
  onLogout,
  onDetailUpdated,
  motivo = 'Intervento staff razza/aura',
}) => {
  const [punteggiList, setPunteggiList] = useState([]);
  const [punteggiLoading, setPunteggiLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [modelliByAura, setModelliByAura] = useState({});
  const [modelliLoading, setModelliLoading] = useState({});

  const auraInnataRecord = useMemo(
    () => (punteggiList || []).find((p) => p.tipo === 'AU' && String(p.sigla || '').toUpperCase() === 'AIN'),
    [punteggiList],
  );

  const aurasConModelli = useMemo(
    () => (punteggiList || []).filter((p) => p.tipo === 'AU' && p.has_models),
    [punteggiList],
  );

  const razzaAbilita = detail?.razza_abilita || [];
  const abilitaPerPicker = razzaAbilita;

  const { archetipoLabel, formaLabel } = useRazzaDisplay(razzaAbilita);
  const canEditRazza = !!detail?.can_edit_razza;

  const formaTrait = useMemo(
    () => razzaAbilita.find((ab) => isTrattoAuraInnita(ab) && ab.livello_riferimento === 2),
    [razzaAbilita],
  );

  useEffect(() => {
    let cancelled = false;
    setPunteggiLoading(true);
    getPunteggiList(onLogout)
      .then((data) => {
        if (!cancelled) setPunteggiList(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (!cancelled) setPunteggiList([]);
      })
      .finally(() => {
        if (!cancelled) setPunteggiLoading(false);
      });
    return () => { cancelled = true; };
  }, [onLogout]);

  const loadModelliAura = useCallback(async (auraId) => {
    if (!auraId || modelliByAura[auraId]) return;
    setModelliLoading((s) => ({ ...s, [auraId]: true }));
    try {
      const rows = await getModelliAura(auraId);
      setModelliByAura((s) => ({ ...s, [auraId]: Array.isArray(rows) ? rows : [] }));
    } catch {
      setModelliByAura((s) => ({ ...s, [auraId]: [] }));
    } finally {
      setModelliLoading((s) => ({ ...s, [auraId]: false }));
    }
  }, [modelliByAura]);

  useEffect(() => {
    aurasConModelli.forEach((aura) => {
      void loadModelliAura(aura.id);
    });
  }, [aurasConModelli, loadModelliAura]);

  const handlePickRazza = async (abilitaId) => {
    if (!detail?.id) return;
    setBusy(true);
    try {
      const updated = await staffPersonaggioAssegnaAbilita(
        detail.id,
        abilitaId,
        { motivo },
        onLogout,
      );
      onDetailUpdated(updated);
    } catch (e) {
      throw new Error(e.message || 'Assegnazione razza fallita');
    } finally {
      setBusy(false);
    }
  };

  const handleRevocaTrait = async (trait) => {
    if (!detail?.id || !trait?.id) return;
    if (!trait.is_modifiable) return;
    const label = stripRazzaPrefix(trait.nome);
    if (!window.confirm(`Revocare il tratto «${label}»? Verranno applicati rimborsi e regole standard.`)) {
      return;
    }
    setBusy(true);
    try {
      const updated = await staffPersonaggioRimuoviAbilita(
        detail.id,
        trait.id,
        { motivo },
        onLogout,
      );
      onDetailUpdated(updated);
    } catch (e) {
      window.alert(e.message || 'Revoca fallita');
    } finally {
      setBusy(false);
    }
  };

  const handleAssegnaModello = async (auraId, modelloId) => {
    if (!detail?.id || !modelloId) return;
    setBusy(true);
    try {
      const updated = await staffPersonaggioAssegnaModelloAura(
        detail.id,
        modelloId,
        { motivo },
        onLogout,
      );
      onDetailUpdated(updated);
    } catch (e) {
      window.alert(e.message || 'Assegnazione modello aura fallita');
    } finally {
      setBusy(false);
    }
  };

  const handleRimuoviModello = async (auraId, modelloId) => {
    if (!detail?.id) return;
    if (!window.confirm('Rimuovere il modello di aura per questa aura?')) return;
    setBusy(true);
    try {
      const updated = await staffPersonaggioRimuoviModelloAura(
        detail.id,
        { aura_id: auraId, modello_aura_id: modelloId },
        { motivo },
        onLogout,
      );
      onDetailUpdated(updated);
    } catch (e) {
      window.alert(e.message || 'Rimozione modello aura fallita');
    } finally {
      setBusy(false);
    }
  };

  if (punteggiLoading) {
    return (
      <p className="text-sm text-gray-400 flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" />
        Caricamento catalogo punteggi…
      </p>
    );
  }

  return (
    <div className="space-y-8 text-sm">
      <section className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h4 className="font-bold text-white uppercase text-xs tracking-wide">
            Razza (Archetipo / Forma)
          </h4>
          <p className="text-gray-400 text-xs">
            Attuale:{' '}
            <span className="text-amber-200">{archetipoLabel}</span>
            {formaLabel ? (
              <>
                {' '}
                · <span className="text-cyan-200">{formaLabel}</span>
              </>
            ) : null}
          </p>
        </div>

        <p className="text-xs text-gray-500">
          Assegnazione e revoca usano gli stessi endpoint e vincoli del tab Abilità
          (<code className="text-gray-400">assegna-abilita</code> / <code className="text-gray-400">rimuovi-abilita</code>).
          Il blocco per eventi si applica come per il giocatore, salvo flag
          «Consenti modifica oltre i vincoli evento» nel tab Abilità.
        </p>

        {detail?.scheda_modifica_libera && (
          <p className="text-xs text-emerald-400 bg-emerald-950/30 border border-emerald-800/50 rounded px-2 py-1.5">
            Modifica scheda sbloccata: il personaggio può cambiare razza anche con eventi in corso.
          </p>
        )}

        <div className="bg-gray-900/80 border border-gray-700 rounded-lg p-4">
          <RazzaPickerContent
            inline
            abilitaPossedute={abilitaPerPicker}
            punteggiBase={detail?.punteggi_base || {}}
            punteggiList={punteggiList}
            auraInnataRecord={auraInnataRecord}
            canEdit={canEditRazza && !busy}
            editBlockedMessage={
              detail?.scheda_modifica_libera
                ? 'Modifica temporaneamente non disponibile.'
                : 'Modifica razza bloccata: il personaggio partecipa già a un evento iniziato. Attiva «Consenti modifica oltre i vincoli evento» nel tab Abilità.'
            }
            onPick={handlePickRazza}
          />
        </div>

        {formaTrait && (
          <div className="bg-gray-800/80 border border-gray-700 rounded-lg p-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-medium text-white">Forma attuale: {stripRazzaPrefix(formaTrait.nome)}</div>
              {!formaTrait.is_modifiable && formaTrait.revoca_blocco && (
                <div className="text-[10px] text-amber-400 mt-0.5">{formaTrait.revoca_blocco}</div>
              )}
            </div>
            <button
              type="button"
              disabled={busy || !formaTrait.is_modifiable}
              title={formaTrait.revoca_blocco || ''}
              onClick={() => void handleRevocaTrait(formaTrait)}
              className="px-3 py-1 rounded text-xs font-bold bg-red-900/70 hover:bg-red-800 disabled:opacity-40"
            >
              Revoca forma
            </button>
          </div>
        )}

        {razzaAbilita
          .filter((t) => isTrattoAuraInnita(t) && (t.livello_riferimento === 0 || t.livello_riferimento === 1))
          .map((trait) => (
            <div
              key={trait.id}
              className="bg-gray-800/80 border border-gray-700 rounded-lg p-3 flex flex-wrap items-center justify-between gap-2"
            >
              <div>
                <div className="font-medium text-white">
                  Archetipo DB: {stripRazzaPrefix(trait.nome)}
                </div>
                {!trait.is_modifiable && trait.revoca_blocco && (
                  <div className="text-[10px] text-amber-400 mt-0.5">{trait.revoca_blocco}</div>
                )}
              </div>
              <button
                type="button"
                disabled={busy || !trait.is_modifiable}
                title={trait.revoca_blocco || ''}
                onClick={() => void handleRevocaTrait(trait)}
                className="px-3 py-1 rounded text-xs font-bold bg-red-900/70 hover:bg-red-800 disabled:opacity-40"
              >
                Revoca archetipo
              </button>
            </div>
          ))}
      </section>

      <section className="space-y-4 border-t border-gray-700 pt-6">
        <h4 className="font-bold text-white uppercase text-xs tracking-wide">
          Modelli di aura
        </h4>
        <p className="text-xs text-gray-500">
          Lo staff può assegnare, sostituire o rimuovere i modelli (il giocatore in scheda ha scelta definitiva).
        </p>

        {aurasConModelli.length === 0 && (
          <p className="text-gray-500 text-xs">Nessuna aura con modelli configurati.</p>
        )}

        {aurasConModelli.map((aura) => {
          const assigned = (detail?.modelli_aura || []).find((m) => m.aura === aura.id);
          const modelli = modelliByAura[aura.id] || [];
          const loading = modelliLoading[aura.id];

          return (
            <div key={aura.id} className="bg-gray-800 border border-gray-700 rounded-lg p-3 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-bold text-white">{aura.nome}</span>
                <span className="text-xs text-gray-400">
                  {assigned ? `Modello: ${assigned.nome}` : 'Nessun modello'}
                </span>
              </div>

              {loading ? (
                <p className="text-xs text-gray-500">Caricamento modelli…</p>
              ) : (
                <div className="flex flex-wrap gap-2 items-end">
                  <select
                    className="bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm min-w-[200px] flex-1"
                    defaultValue=""
                    disabled={busy}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v) void handleAssegnaModello(aura.id, v);
                      e.target.value = '';
                    }}
                  >
                    <option value="">
                      {assigned ? 'Sostituisci con…' : 'Assegna modello…'}
                    </option>
                    {modelli.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.nome}
                        {assigned?.id === m.id ? ' (attuale)' : ''}
                      </option>
                    ))}
                  </select>
                  {assigned && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void handleRimuoviModello(aura.id, assigned.id)}
                      className="px-3 py-1.5 rounded text-xs font-bold bg-red-900/70 hover:bg-red-800 disabled:opacity-40"
                    >
                      Rimuovi
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </section>
    </div>
  );
};

export default StaffRazzaAuraTab;
