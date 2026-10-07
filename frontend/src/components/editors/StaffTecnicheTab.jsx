import React, { useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import SearchableSelect from './SearchableSelect';
import {
  staffPersonaggioAssegnaTecnica,
  staffPersonaggioCatalogoTecniche,
  staffPersonaggioRimuoviTecnica,
} from '../../api';

const TIPI = [
  { id: 'infusione', label: 'Infusioni', short: 'Inf.', posseduteKey: 'infusioni_possedute', vuoto: 'Nessuna infusione posseduta.' },
  { id: 'cerimoniale', label: 'Cerimoniali', short: 'Cer.', posseduteKey: 'cerimoniali_posseduti', vuoto: 'Nessun cerimoniale posseduto.' },
  { id: 'tessitura', label: 'Tessiture', short: 'Tess.', posseduteKey: 'tessiture_possedute', vuoto: 'Nessuna tessitura posseduta.' },
];

function etichettaCatalogo(row) {
  const pezzi = [row.nome];
  if (row.livello != null) pezzi.push(`liv. ${row.livello}`);
  if (row.aura) pezzi.push(row.aura);
  if (row.non_acquistabile) pezzi.push('fuori Accademia');
  return pezzi.join(' · ');
}

/**
 * Tab staff: tecniche possedute dal personaggio (infusioni, cerimoniali, tessiture).
 */
export default function StaffTecnicheTab({ detail, onLogout, onUpdated, onError }) {
  const [tipo, setTipo] = useState('infusione');
  const [motivo, setMotivo] = useState('Intervento staff tecniche');
  const [omaggio, setOmaggio] = useState(false);
  const [catalogo, setCatalogo] = useState([]);
  const [catalogoLoading, setCatalogoLoading] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const meta = TIPI.find((t) => t.id === tipo) || TIPI[0];
  const possedute = detail?.[meta.posseduteKey] || [];

  useEffect(() => {
    setSelectedId(null);
  }, [tipo, detail?.id]);

  useEffect(() => {
    if (!detail?.id) return undefined;
    let cancel = false;
    setCatalogoLoading(true);
    staffPersonaggioCatalogoTecniche(detail.id, tipo, onLogout)
      .then((rows) => {
        if (!cancel) setCatalogo(Array.isArray(rows) ? rows : []);
      })
      .catch(() => {
        if (!cancel) setCatalogo([]);
      })
      .finally(() => {
        if (!cancel) setCatalogoLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [detail?.id, tipo, onLogout, refreshKey]);

  const opzioni = useMemo(
    () => catalogo.map((row) => ({ id: row.id, nome: etichettaCatalogo(row) })),
    [catalogo],
  );

  const assegna = async () => {
    if (!detail?.id || !selectedId || busy) return;
    setBusy(true);
    try {
      const updated = await staffPersonaggioAssegnaTecnica(
        detail.id,
        { tipo, tecnicaId: selectedId, motivo, omaggio },
        onLogout,
      );
      setSelectedId(null);
      setRefreshKey((n) => n + 1);
      onUpdated?.(
        updated,
        omaggio
          ? 'Tecnica assegnata in omaggio (nessun addebito).'
          : 'Tecnica assegnata: requisiti e costo applicati come in scheda giocatore.',
      );
    } catch (e) {
      onError?.(e.message || 'Assegnazione tecnica fallita');
    } finally {
      setBusy(false);
    }
  };

  const revoca = async (row) => {
    if (!detail?.id || busy) return;
    const pagato = Number(row.costo_crediti_pagato || 0);
    const extra = pagato > 0
      ? ` Verranno rimborsati ${row.costo_crediti_pagato} CR sul conto corrente.`
      : ' Non risulta un pagamento da rimborsare.';
    if (!window.confirm(`Revocare «${row.nome}»?${extra}`)) return;
    setBusy(true);
    try {
      const updated = await staffPersonaggioRimuoviTecnica(
        detail.id,
        { tipo, tecnicaId: row.id, motivo },
        onLogout,
      );
      setRefreshKey((n) => n + 1);
      onUpdated?.(updated, `«${row.nome}» revocata.`);
    } catch (e) {
      onError?.(e.message || 'Revoca tecnica fallita');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="staff-tecniche-tab" className="space-y-4 text-sm min-w-0">
      <div className="flex gap-1 overflow-x-auto" role="tablist" aria-label="Tipo tecnica">
        {TIPI.map((t) => {
          const attiva = t.id === tipo;
          const count = (detail?.[t.posseduteKey] || []).length;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={attiva}
              onClick={() => setTipo(t.id)}
              className={`inline-flex shrink-0 items-center gap-1.5 min-h-11 rounded-lg px-3 text-xs font-bold whitespace-nowrap ${
                attiva ? 'bg-teal-700 text-white' : 'bg-gray-800 text-gray-300'
              }`}
            >
              <span className="sm:hidden">{t.short}</span>
              <span className="hidden sm:inline">{t.label}</span>
              <span className={attiva ? 'text-teal-100' : 'text-gray-500'}>{count}</span>
            </button>
          );
        })}
      </div>

      <p className="text-xs text-gray-400 leading-relaxed">
        Acquisto usa le regole della scheda (requisiti, Accademia, crediti sul conto corrente).
        Omaggio assegna la tecnica senza requisiti né costo. La revoca da qui è sempre
        consentita allo staff, anche durante un evento, e rimborsa solo i crediti pagati.
      </p>

      <div>
        <label className="text-xs text-gray-400 block mb-1" htmlFor="staff-tecniche-motivo">
          Motivo (log / movimenti)
        </label>
        <input
          id="staff-tecniche-motivo"
          className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded px-2 py-1.5"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
      </div>

      <div className="bg-gray-800/80 border border-gray-700 rounded-lg p-3 space-y-3">
        <h4 className="font-bold text-white">Aggiungi {meta.label.toLowerCase()}</h4>
        <label className="flex items-start gap-3 cursor-pointer min-h-11">
          <input
            type="checkbox"
            className="mt-1"
            checked={omaggio}
            disabled={busy}
            onChange={(e) => setOmaggio(e.target.checked)}
          />
          <span>
            <span className="text-white font-medium block">Omaggio staff</span>
            <span className="text-gray-400 text-xs block mt-0.5">
              Ignora requisiti e Accademia, non addebita crediti.
            </span>
          </span>
        </label>
        {catalogoLoading ? (
          <p className="text-gray-400 text-xs inline-flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" />
            Caricamento catalogo…
          </p>
        ) : (
          <SearchableSelect
            options={opzioni}
            value={selectedId}
            onChange={setSelectedId}
            placeholder={opzioni.length ? 'Seleziona tecnica…' : 'Nessuna tecnica assegnabile'}
            disabled={busy || !opzioni.length}
          />
        )}
        <button
          type="button"
          disabled={!selectedId || busy}
          onClick={() => void assegna()}
          className="min-h-11 w-full sm:w-auto px-4 rounded bg-emerald-700 hover:bg-emerald-600 font-bold text-sm disabled:opacity-40"
        >
          Assegna
        </button>
      </div>

      <div>
        <h4 className="font-bold text-white mb-2">
          Possedute ({possedute.length})
        </h4>
        <ul className="space-y-2">
          {possedute.map((row) => (
            <li
              key={row.id}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 min-w-0"
            >
              <div className="min-w-0">
                <div className="font-medium text-white break-words">{row.nome}</div>
                <div className="text-[11px] text-gray-400 break-words">
                  Liv. {row.livello ?? 0}
                  {row.aura ? ` · ${row.aura}` : ''}
                  {` · pagati ${row.costo_crediti_pagato ?? '0.00'} CR`}
                </div>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => void revoca(row)}
                className="min-h-11 w-full sm:w-auto px-3 rounded text-xs font-bold bg-red-900/70 hover:bg-red-800 disabled:opacity-40"
              >
                Revoca
              </button>
            </li>
          ))}
          {!possedute.length && <li className="text-gray-500">{meta.vuoto}</li>}
        </ul>
      </div>
    </div>
  );
}
