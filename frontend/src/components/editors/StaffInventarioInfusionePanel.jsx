import React, { useEffect, useMemo, useState } from 'react';
import {
  staffGetInfusioni,
  staffPersonaggioCreaOggettoDaInfusione,
  staffPersonaggioMontaPotenziamento,
} from '../../api';
import SearchableSelect from './SearchableSelect';
import {
  SLOT_CORPO,
  TIPO_OGGETTO_LABEL,
  TIPI_POTENZIAMENTO,
  isAumentoCorporeo,
  mappaSlotOccupati,
  permessiSlotInfusione,
  slotLiberoSelezionabile,
} from '../../lib/slotCorpoStaff';

function normalizzaInfusioni(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

/**
 * Inventario staff: istanza da infusione e montaggio/smontaggio d'ufficio
 * di materia o mod, entrambe in possesso dello stesso personaggio.
 */
export default function StaffInventarioInfusionePanel({
  personaggioId,
  oggetti = [],
  motivo = 'Intervento staff inventario',
  onLogout,
  onMessage,
  onReload,
}) {
  const [infusioni, setInfusioni] = useState([]);
  const [infusioneId, setInfusioneId] = useState('');
  const [slot, setSlot] = useState('');
  const [hostCreaId, setHostCreaId] = useState('');
  const [componenteId, setComponenteId] = useState('');
  const [hostMontaId, setHostMontaId] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancel = false;
    staffGetInfusioni(onLogout)
      .then((data) => {
        if (!cancel) setInfusioni(normalizzaInfusioni(data));
      })
      .catch(() => {
        if (!cancel) setInfusioni([]);
      });
    return () => {
      cancel = true;
    };
  }, [onLogout]);

  const infusione = infusioni.find((row) => String(row.id) === String(infusioneId)) || null;
  const aumento = isAumentoCorporeo(infusione);
  const permessi = permessiSlotInfusione(infusione);
  const occupati = useMemo(() => mappaSlotOccupati(oggetti), [oggetti]);
  const hostFisici = useMemo(
    () => oggetti.filter((o) => o.tipo_oggetto === 'FIS'),
    [oggetti],
  );
  const materieLibere = useMemo(
    () => oggetti.filter((o) => TIPI_POTENZIAMENTO.includes(o.tipo_oggetto)),
    [oggetti],
  );
  const opzioniInfusione = useMemo(
    () => infusioni.map((row) => ({
      id: row.id,
      nome: `${row.nome} · ${row.tipo_risultato === 'AUM' ? 'innesto/mutazione' : 'materia/mod'}`,
    })),
    [infusioni],
  );

  const crea = async () => {
    if (!infusioneId) return;
    if (aumento && !slot) {
      onMessage?.('Scegli uno slot corporeo libero.');
      return;
    }
    setBusy(true);
    try {
      const payload = {
        infusione_id: infusioneId,
        motivo,
        slot_corpo: aumento ? slot : '',
        oggetto_ospite_id: !aumento && hostCreaId ? hostCreaId : null,
      };
      const res = await staffPersonaggioCreaOggettoDaInfusione(personaggioId, payload, onLogout);
      onMessage?.(res.detail || 'Istanza creata.');
      setSlot('');
      setHostCreaId('');
      await onReload?.();
    } catch (e) {
      onMessage?.(e.message || 'Errore creazione da infusione');
    } finally {
      setBusy(false);
    }
  };

  const monta = async () => {
    if (!componenteId || !hostMontaId) {
      onMessage?.('Scegli materia (o mod) e oggetto fisico, entrambi in inventario.');
      return;
    }
    setBusy(true);
    try {
      const res = await staffPersonaggioMontaPotenziamento(
        personaggioId, componenteId, hostMontaId, motivo, onLogout,
      );
      onMessage?.(res.detail || 'Montaggio eseguito.');
      setComponenteId('');
      setHostMontaId('');
      await onReload?.();
    } catch (e) {
      onMessage?.(e.message || 'Errore montaggio');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="bg-gray-800/80 border border-purple-900/50 rounded-lg p-3 space-y-2">
        <p className="text-xs text-gray-400 break-words">
          Crea un&apos;istanza da <strong>infusione</strong> e mettila nell&apos;inventario.
          Materia o mod: installazione opzionale su un oggetto fisico del personaggio.
          Mutazione o innesto: slot corporeo libero obbligatorio.
        </p>
        <SearchableSelect
          options={opzioniInfusione}
          value={infusioneId}
          onChange={(v) => {
            setInfusioneId(v || '');
            setSlot('');
            setHostCreaId('');
          }}
          placeholder="Seleziona infusione…"
        />
        {infusione && aumento && (
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
                const nota = occupati[s.code]
                  ? ` — occupato (${occupati[s.code]})`
                  : (permessi.length && !permessi.includes(s.code) ? ' — non consentito' : '');
                return (
                  <option key={s.code} value={s.code} disabled={!libero}>
                    {s.label}{nota}
                  </option>
                );
              })}
            </select>
          </label>
        )}
        {infusione && !aumento && (
          <label className="block text-xs text-gray-400">
            Installa su oggetto fisico (opzionale)
            <select
              className="mt-1 w-full min-h-11 bg-gray-950 border border-gray-700 rounded px-2 py-2 text-sm text-white"
              value={hostCreaId}
              onChange={(e) => setHostCreaId(e.target.value)}
            >
              <option value="">Lascia in inventario</option>
              {hostFisici.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nome} (#{o.id})
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          type="button"
          disabled={busy || !infusioneId || (aumento && !slot)}
          onClick={crea}
          className="min-h-11 w-full sm:w-auto px-4 py-2 bg-purple-700 rounded font-bold text-sm disabled:opacity-40"
        >
          Crea istanza da infusione
        </button>
      </div>

      <div className="bg-gray-800/80 border border-amber-900/50 rounded-lg p-3 space-y-2">
        <p className="text-xs text-gray-400 break-words">
          Monta d&apos;ufficio una <strong>materia o mod</strong> già in inventario
          su un oggetto fisico dello stesso personaggio. La competenza del PG non è richiesta.
        </p>
        <SearchableSelect
          options={materieLibere.map((o) => ({
            id: o.id,
            nome: `${o.nome} (#${o.id}, ${TIPO_OGGETTO_LABEL[o.tipo_oggetto] || o.tipo_oggetto})`,
          }))}
          value={componenteId}
          onChange={(v) => setComponenteId(v || '')}
          placeholder="Materia o mod in inventario…"
        />
        <SearchableSelect
          options={hostFisici
            .filter((o) => String(o.id) !== String(componenteId))
            .map((o) => ({ id: o.id, nome: `${o.nome} (#${o.id})` }))}
          value={hostMontaId}
          onChange={(v) => setHostMontaId(v || '')}
          placeholder="Oggetto fisico ospite…"
        />
        <button
          type="button"
          disabled={busy || !componenteId || !hostMontaId}
          onClick={monta}
          className="min-h-11 w-full sm:w-auto px-4 py-2 bg-amber-700 rounded font-bold text-sm disabled:opacity-40"
        >
          Monta d&apos;ufficio
        </button>
      </div>
    </div>
  );
}

export function PotenziamentiMontati({ potenziamenti = [], onSmonta, busy = false }) {
  if (!potenziamenti.length) return null;
  return (
    <ul className="w-full mt-1 space-y-1">
      {potenziamenti.map((p) => (
        <li
          key={p.id}
          className="flex flex-wrap items-center justify-between gap-2 bg-gray-900/80 border border-gray-700 rounded px-2 py-1"
        >
          <span className="text-xs text-amber-100 break-words min-w-0">
            Montata: {p.nome}
            <span className="text-gray-500 font-mono ml-1">
              #{p.id} · {TIPO_OGGETTO_LABEL[p.tipo_oggetto] || p.tipo_oggetto}
            </span>
          </span>
          <button
            type="button"
            disabled={busy}
            className="min-h-11 px-3 bg-amber-900/70 border border-amber-800 rounded text-xs font-bold disabled:opacity-40"
            onClick={() => onSmonta(p)}
          >
            Smonta
          </button>
        </li>
      ))}
    </ul>
  );
}
