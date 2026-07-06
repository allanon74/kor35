import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Plus, RefreshCw, Store, X } from 'lucide-react';
import {
  carteGetMercato,
  carteCreaOffertaMercato,
  carteAccettaOffertaMercato,
  carteAnnullaOffertaMercato,
} from '../api';
import { CARTA_RARITA_LABEL } from './carteConstants';

const STATO_LABEL = {
  APR: 'Aperta',
  ACC: 'Accettata',
  ANN: 'Annullata',
  SCD: 'Scaduta',
};

function OffertaRow({ offerta, onAccept, onCancel, acceptingId, charId }) {
  const off = offerta.carta_offerta?.carta;
  const rich = offerta.richiesta_carta;
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900/50 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-bold text-violet-200">{offerta.offerente?.nome}</p>
          <p className="mt-1 text-gray-300">
            Offre: <span className="font-semibold">{off?.nome || '?'}</span>
            {off?.codice ? <span className="text-gray-500"> ({off.codice})</span> : null}
          </p>
          <p className="text-gray-400">
            Vuole:{' '}
            {rich ? (
              <span>{rich.nome} ({CARTA_RARITA_LABEL[rich.rarita] || rich.rarita})</span>
            ) : null}
            {rich && offerta.richiesta_crediti ? ' + ' : ''}
            {offerta.richiesta_crediti ? (
              <span>{offerta.richiesta_crediti} CR</span>
            ) : null}
            {!rich && !offerta.richiesta_crediti ? '—' : null}
          </p>
          {offerta.messaggio?.trim() && (
            <p className="mt-1 text-xs italic text-gray-500">{offerta.messaggio}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-1">
          {offerta.mio && onCancel && (
            <button
              type="button"
              className="rounded bg-red-900/80 px-2 py-1 text-xs font-bold"
              onClick={() => onCancel(offerta.id)}
            >
              Annulla
            </button>
          )}
          {!offerta.mio && offerta.posso_accettare && onAccept && (
            <button
              type="button"
              disabled={acceptingId === offerta.id}
              className="rounded bg-emerald-800 px-2 py-1 text-xs font-bold disabled:opacity-50"
              onClick={() => onAccept(offerta)}
            >
              {acceptingId === offerta.id ? '…' : 'Accetta'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MercatoCartePanel({ charId, onLogout, onCollezioneUpdate, onError }) {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [mercato, setMercato] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [acceptTarget, setAcceptTarget] = useState(null);
  const [form, setForm] = useState({
    carta_offerta_id: '',
    richiesta_carta_id: '',
    richiesta_crediti: '',
    messaggio: '',
    tipo_richiesta: 'carta',
  });
  const [contropartitaId, setContropartitaId] = useState('');

  const load = useCallback(async () => {
    if (!charId) return;
    setLoading(true);
    try {
      const payload = await carteGetMercato(charId, onLogout);
      setMercato(payload);
    } catch (e) {
      onError?.(e?.message || 'Errore caricamento mercato.');
    } finally {
      setLoading(false);
    }
  }, [charId, onLogout, onError]);

  useEffect(() => {
    load();
  }, [load]);

  const carteScambiabili = useMemo(
    () => (mercato?.carte_scambiabili || []).filter((c) => c.scambiabile),
    [mercato?.carte_scambiabili],
  );

  const contropartiteDisponibili = useMemo(() => {
    if (!acceptTarget?.richiesta_carta?.id) return [];
    return (mercato?.carte_scambiabili || []).filter(
      (c) => c.scambiabile && c.carta?.id === acceptTarget.richiesta_carta.id,
    );
  }, [acceptTarget, mercato?.carte_scambiabili]);

  const handleCreate = async () => {
    if (!form.carta_offerta_id) {
      onError?.('Seleziona la carta da offrire.');
      return;
    }
    setBusy(true);
    onError?.('');
    try {
      const payload = await carteCreaOffertaMercato(charId, {
        carta_offerta_id: form.carta_offerta_id,
        richiesta_carta_id:
          form.tipo_richiesta === 'crediti' ? null : (form.richiesta_carta_id || null),
        richiesta_crediti:
          form.tipo_richiesta === 'carta' ? null : (form.richiesta_crediti || null),
        messaggio: form.messaggio,
      }, onLogout);
      setMercato(payload);
      setCreateOpen(false);
      setForm({
        carta_offerta_id: '',
        richiesta_carta_id: '',
        richiesta_crediti: '',
        messaggio: '',
        tipo_richiesta: 'carta',
      });
    } catch (e) {
      onError?.(e?.message || 'Creazione offerta fallita.');
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async (offertaId) => {
    setBusy(true);
    try {
      const payload = await carteAnnullaOffertaMercato(charId, offertaId, onLogout);
      setMercato(payload);
    } catch (e) {
      onError?.(e?.message || 'Annullamento fallito.');
    } finally {
      setBusy(false);
    }
  };

  const handleAccept = async (offerta) => {
    if (offerta.richiesta_carta && !contropartitaId) {
      setAcceptTarget(offerta);
      return;
    }
    setBusy(true);
    setAcceptTarget(null);
    try {
      const payload = await carteAccettaOffertaMercato(charId, offerta.id, {
        carta_contropartita_id: contropartitaId || undefined,
      }, onLogout);
      setMercato(payload);
      if (payload.collezione) onCollezioneUpdate?.(payload.collezione);
      setContropartitaId('');
    } catch (e) {
      onError?.(e?.message || 'Accettazione fallita.');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-10 text-gray-400">
        <Loader2 className="animate-spin" size={28} />
      </div>
    );
  }

  if (!mercato?.puo_accedere) {
    return <p className="text-sm text-gray-500">Mercato non disponibile.</p>;
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-3">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="flex items-center gap-1 text-sm font-bold text-emerald-300">
            <Store size={16} /> Mercato carte
          </h3>
          <div className="flex gap-2">
            <button type="button" className="rounded bg-gray-800 p-1.5" onClick={load} title="Aggiorna">
              <RefreshCw size={14} />
            </button>
            <button
              type="button"
              className="flex items-center gap-1 rounded bg-emerald-800 px-2 py-1 text-xs font-bold"
              onClick={() => setCreateOpen((v) => !v)}
            >
              <Plus size={12} /> Nuova offerta
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-400">
          Crediti: <span className="font-bold text-emerald-200">{Number(mercato.crediti || 0).toFixed(0)} CR</span>
          {' · '}
          Commissione piattaforma: {mercato.commissione_pct}%
        </p>

        {createOpen && (
          <div className="mt-3 space-y-2 rounded border border-gray-700 bg-gray-900/60 p-3">
            <label className="block text-xs">
              Carta che offri
              <select
                className="mt-1 w-full rounded bg-gray-950 px-2 py-1.5 text-sm text-white"
                value={form.carta_offerta_id}
                onChange={(e) => setForm((p) => ({ ...p, carta_offerta_id: e.target.value }))}
              >
                <option value="">— Seleziona —</option>
                {carteScambiabili.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.carta?.nome} ({c.carta?.codice})
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap gap-2 text-xs">
              <label className="flex items-center gap-1">
                <input
                  type="radio"
                  checked={form.tipo_richiesta === 'carta'}
                  onChange={() => setForm((p) => ({ ...p, tipo_richiesta: 'carta' }))}
                />
                Richiedi carta
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="radio"
                  checked={form.tipo_richiesta === 'crediti'}
                  onChange={() => setForm((p) => ({ ...p, tipo_richiesta: 'crediti' }))}
                />
                Solo crediti
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="radio"
                  checked={form.tipo_richiesta === 'entrambi'}
                  onChange={() => setForm((p) => ({ ...p, tipo_richiesta: 'entrambi' }))}
                />
                Carta + crediti
              </label>
            </div>
            {(form.tipo_richiesta === 'carta' || form.tipo_richiesta === 'entrambi') && (
              <label className="block text-xs">
                Carta catalogo richiesta
                <select
                  className="mt-1 w-full rounded bg-gray-950 px-2 py-1.5 text-sm text-white"
                  value={form.richiesta_carta_id}
                  onChange={(e) => setForm((p) => ({ ...p, richiesta_carta_id: e.target.value }))}
                >
                  <option value="">— Seleziona —</option>
                  {(mercato.catalogo_richieste || []).map((c) => (
                    <option key={c.id} value={c.id}>{c.nome} ({c.codice})</option>
                  ))}
                </select>
              </label>
            )}
            {(form.tipo_richiesta === 'crediti' || form.tipo_richiesta === 'entrambi') && (
              <label className="block text-xs">
                Crediti richiesti
                <input
                  type="number"
                  min={0}
                  className="mt-1 w-full rounded bg-gray-950 px-2 py-1.5 text-sm text-white"
                  value={form.richiesta_crediti}
                  onChange={(e) => setForm((p) => ({ ...p, richiesta_crediti: e.target.value }))}
                />
              </label>
            )}
            <label className="block text-xs">
              Messaggio (opzionale)
              <input
                className="mt-1 w-full rounded bg-gray-950 px-2 py-1.5 text-sm text-white"
                value={form.messaggio}
                onChange={(e) => setForm((p) => ({ ...p, messaggio: e.target.value }))}
              />
            </label>
            <button
              type="button"
              disabled={busy}
              className="rounded bg-emerald-700 px-3 py-1.5 text-xs font-bold disabled:opacity-50"
              onClick={handleCreate}
            >
              Pubblica offerta
            </button>
          </div>
        )}
      </section>

      {(mercato.offerte_aperte || []).length > 0 && (
        <section>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-400">Offerte al mercato</h4>
          <div className="space-y-2">
            {mercato.offerte_aperte.map((o) => (
              <OffertaRow
                key={o.id}
                offerta={o}
                charId={charId}
                onAccept={(off) => {
                  if (off.richiesta_carta) {
                    setAcceptTarget(off);
                    setContropartitaId('');
                  } else {
                    handleAccept(off);
                  }
                }}
                acceptingId={busy ? acceptTarget?.id : null}
              />
            ))}
          </div>
        </section>
      )}

      {(mercato.mie_offerte || []).length > 0 && (
        <section>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-400">Le tue offerte</h4>
          <div className="space-y-2">
            {mercato.mie_offerte.map((o) => (
              <OffertaRow key={o.id} offerta={o} onCancel={handleCancel} />
            ))}
          </div>
        </section>
      )}

      {(mercato.storico || []).length > 0 && (
        <section>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-400">Storico scambi</h4>
          <ul className="space-y-1 text-xs text-gray-400">
            {mercato.storico.map((o) => (
              <li key={o.id} className="rounded border border-gray-800 bg-gray-900/40 px-2 py-1.5">
                <span className="text-emerald-400">{STATO_LABEL[o.stato] || o.stato}</span>
                {' · '}
                {o.offerente?.nome} → {o.accettante?.nome || '?'}
                {' · '}
                {o.carta_offerta?.carta?.nome}
                {o.carta_contropartita?.carta?.nome ? ` ↔ ${o.carta_contropartita.carta.nome}` : ''}
                {o.crediti_trasferiti ? ` · ${o.crediti_trasferiti} CR` : ''}
              </li>
            ))}
          </ul>
        </section>
      )}

      {acceptTarget && (
        <div className="fixed inset-0 z-[95] flex items-end justify-center bg-black/70 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-xl border border-gray-600 bg-gray-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-bold">Scegli contropartita</h3>
              <button type="button" onClick={() => setAcceptTarget(null)}><X size={18} /></button>
            </div>
            <p className="mb-2 text-xs text-gray-400">
              Devi cedere una copia di «{acceptTarget.richiesta_carta?.nome}».
            </p>
            <select
              className="mb-3 w-full rounded bg-gray-950 px-2 py-2 text-sm text-white"
              value={contropartitaId}
              onChange={(e) => setContropartitaId(e.target.value)}
            >
              <option value="">— Seleziona copia —</option>
              {contropartiteDisponibili.map((c) => (
                <option key={c.id} value={c.id}>{c.carta?.nome}</option>
              ))}
            </select>
            <button
              type="button"
              disabled={!contropartitaId || busy}
              className="w-full rounded bg-emerald-800 py-2 text-sm font-bold disabled:opacity-50"
              onClick={() => handleAccept(acceptTarget)}
            >
              Conferma scambio
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
