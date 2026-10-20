import React, { useEffect, useMemo, useState } from 'react';
import { staffCreaIstanzaDaInfusione, staffGetPersonaggi, staffGetPersonaggioDetail } from '../../api';
import StaffEditorModal from './StaffEditorModal';
import {
  SLOT_CORPO,
  TIPO_OGGETTO_LABEL,
  etichettaSlot,
  isAumentoCorporeo,
  mappaSlotOccupati,
  permessiSlotInfusione,
  slotLiberoSelezionabile,
} from '../../lib/slotCorpoStaff';

/**
 * Crea un'istanza da un'infusione di catalogo.
 * Il personaggio è opzionale: se scelto, mutazione/innesto richiedono uno slot libero
 * e materia/mod possono essere installate su un oggetto fisico del PG.
 */
export default function CreaIstanzaInfusioneModal({
  open,
  infusione,
  onClose,
  onLogout,
  onCreated,
}) {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState([]);
  const [cercando, setCercando] = useState(false);
  const [pg, setPg] = useState(null);
  const [pgDetail, setPgDetail] = useState(null);
  const [slot, setSlot] = useState('');
  const [hostId, setHostId] = useState('');
  const [motivo, setMotivo] = useState('Assegnazione staff');
  const [errore, setErrore] = useState('');
  const [saving, setSaving] = useState(false);

  const aumento = isAumentoCorporeo(infusione);
  const permessi = useMemo(() => permessiSlotInfusione(infusione), [infusione]);
  const occupati = useMemo(
    () => mappaSlotOccupati(pgDetail?.oggetti_inventario),
    [pgDetail],
  );
  const hostOptions = useMemo(
    () => (pgDetail?.oggetti_inventario || []).filter((o) => o.tipo_oggetto === 'FIS'),
    [pgDetail],
  );
  const slotUtili = useMemo(
    () => SLOT_CORPO.filter((s) => slotLiberoSelezionabile(s.code, { occupati, permessi })),
    [occupati, permessi],
  );

  useEffect(() => {
    if (!open) return undefined;
    setQ('');
    setHits([]);
    setPg(null);
    setPgDetail(null);
    setSlot('');
    setHostId('');
    setMotivo('Assegnazione staff');
    setErrore('');
    return undefined;
  }, [open, infusione?.id]);

  useEffect(() => {
    if (!open || pg) return undefined;
    const term = q.trim();
    if (term.length < 2) {
      setHits([]);
      return undefined;
    }
    let cancel = false;
    const timer = setTimeout(async () => {
      setCercando(true);
      try {
        const data = await staffGetPersonaggi({ q: term, page_size: 12 }, onLogout);
        if (!cancel) setHits(data?.results || []);
      } catch (e) {
        if (!cancel) setErrore(e.message || 'Ricerca personaggi non riuscita');
      } finally {
        if (!cancel) setCercando(false);
      }
    }, 300);
    return () => {
      cancel = true;
      clearTimeout(timer);
    };
  }, [q, pg, open, onLogout]);

  const scegliPersonaggio = async (row) => {
    setPg(row);
    setHits([]);
    setQ('');
    setSlot('');
    setHostId('');
    setErrore('');
    try {
      const detail = await staffGetPersonaggioDetail(row.id, onLogout);
      setPgDetail(detail);
    } catch (e) {
      setPgDetail(null);
      setErrore(e.message || 'Dettaglio personaggio non disponibile');
    }
  };

  const salva = async () => {
    if (!infusione?.id) return;
    if (pg && aumento && !slot) {
      setErrore('Scegli uno slot corporeo libero.');
      return;
    }
    setSaving(true);
    setErrore('');
    try {
      const payload = {
        motivo,
        personaggio_id: pg?.id || null,
      };
      if (pg && aumento) payload.slot_corpo = slot;
      if (pg && !aumento && hostId) payload.oggetto_ospite_id = hostId;
      const res = await staffCreaIstanzaDaInfusione(infusione.id, payload, onLogout);
      onCreated?.(res?.detail || `Istanza di «${infusione.nome}» creata.`);
    } catch (e) {
      setErrore(e.message || 'Errore creazione istanza');
    } finally {
      setSaving(false);
    }
  };

  if (!open || !infusione) return null;

  const tipoNota = aumento
    ? 'Innesto o mutazione: con un personaggio lo slot corporeo libero è obbligatorio.'
    : 'Materia o mod: puoi lasciarla in inventario oppure installarla su un oggetto fisico del personaggio.';

  return (
    <StaffEditorModal
      title={`Istanza — ${infusione.nome}`}
      onClose={onClose}
      onSave={salva}
      saveLabel="Crea istanza"
      saving={saving}
      isDirty={Boolean(pg || slot || hostId)}
    >
      <p className="text-xs text-gray-400 break-words">{tipoNota}</p>
      <label className="block text-xs text-gray-400">
        Personaggio (opzionale)
        {pg ? (
          <div className="mt-1 flex flex-col sm:flex-row sm:items-center gap-2">
            <span className="text-sm text-white font-bold break-words">{pg.nome}</span>
            <button
              type="button"
              className="min-h-11 px-3 rounded bg-gray-700 text-xs font-bold"
              onClick={() => {
                setPg(null);
                setPgDetail(null);
                setSlot('');
                setHostId('');
              }}
            >
              Rimuovi
            </button>
          </div>
        ) : (
          <input
            className="mt-1 w-full min-h-11 bg-gray-950 border border-gray-700 rounded px-2 py-2 text-sm text-white"
            placeholder="Cerca per nome (almeno 2 lettere)…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        )}
      </label>
      {!pg && hits.length > 0 && (
        <ul className="border border-gray-700 rounded divide-y divide-gray-800 max-h-48 overflow-y-auto">
          {hits.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                className="w-full text-left min-h-11 px-3 py-2 text-sm hover:bg-gray-800 break-words"
                onClick={() => scegliPersonaggio(row)}
              >
                {row.nome}
                <span className="text-gray-500 text-xs ml-2">#{row.id}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {cercando && <p className="text-xs text-gray-500">Ricerca…</p>}

      {pg && aumento && (
        <label className="block text-xs text-gray-400">
          Slot corporeo libero
          <select
            className="mt-1 w-full min-h-11 bg-gray-950 border border-gray-700 rounded px-2 py-2 text-sm text-white"
            value={slot}
            onChange={(e) => setSlot(e.target.value)}
          >
            <option value="">Scegli uno slot…</option>
            {SLOT_CORPO.map((s) => {
              const libero = slotLiberoSelezionabile(s.code, { occupati, permessi });
              const perche = occupati[s.code]
                ? ` — occupato (${occupati[s.code]})`
                : (permessi.length && !permessi.includes(s.code) ? ' — non consentito' : '');
              return (
                <option key={s.code} value={s.code} disabled={!libero}>
                  {s.label}{perche}
                </option>
              );
            })}
          </select>
          {!slotUtili.length && (
            <span className="block mt-1 text-amber-300">
              Nessuno slot libero consentito per questa infusione.
            </span>
          )}
        </label>
      )}

      {pg && !aumento && (
        <label className="block text-xs text-gray-400">
          Installa su un oggetto fisico (opzionale)
          <select
            className="mt-1 w-full min-h-11 bg-gray-950 border border-gray-700 rounded px-2 py-2 text-sm text-white"
            value={hostId}
            onChange={(e) => setHostId(e.target.value)}
          >
            <option value="">Lascia in inventario</option>
            {hostOptions.map((o) => (
              <option key={o.id} value={o.id}>
                {o.nome} (#{o.id}, {TIPO_OGGETTO_LABEL[o.tipo_oggetto] || o.tipo_oggetto})
              </option>
            ))}
          </select>
          {!hostOptions.length && (
            <span className="block mt-1 text-gray-500">
              {pg.nome} non ha oggetti fisici in inventario.
            </span>
          )}
        </label>
      )}

      <label className="block text-xs text-gray-400">
        Motivo (log PG)
        <input
          className="mt-1 w-full min-h-11 bg-gray-950 border border-gray-700 rounded px-2 py-2 text-sm text-white"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
      </label>
      {errore ? <p className="text-sm text-red-300 break-words">{errore}</p> : null}
      {slot ? (
        <p className="text-xs text-gray-500">Slot scelto: {etichettaSlot(slot)}</p>
      ) : null}
    </StaffEditorModal>
  );
}
