import React, { memo, useState } from 'react';
import { ArrowRightLeft, Coins, Star, Wallet } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import {
  fetchEconomiaMovimenti,
  postTrasferimentoDeposito,
} from '../api';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';

function fmt(n) {
  const v = Number(n);
  if (Number.isNaN(v)) return '0.00';
  return v.toFixed(2);
}

/**
 * Tab giocatore: saldi corrente/deposito/PC, trasferimento, log lazy.
 */
function EconomiaTab({ onLogout }) {
  const { selectedCharacterData, selectedCharacterId, refreshCharacterData } = useCharacter();
  const char = selectedCharacterData || {};
  const economia = char.economia || {};
  const [importo, setImporto] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [okMsg, setOkMsg] = useState('');
  const [logTipo, setLogTipo] = useState(null);
  const [logRows, setLogRows] = useState([]);
  const [logLoading, setLogLoading] = useState(false);

  const corrente = char.crediti_corrente ?? economia.crediti_corrente ?? char.crediti ?? 0;
  const deposito = char.crediti_deposito ?? economia.crediti_deposito ?? char.riserva ?? 0;
  const pc = char.punti_caratteristica ?? 0;
  const trasf = economia.trasferimento;

  const doTransfer = async () => {
    setError('');
    setOkMsg('');
    setBusy(true);
    try {
      const res = await postTrasferimentoDeposito(selectedCharacterId, importo, onLogout);
      setOkMsg(`Trasferiti ${res.importo} CR dal deposito al corrente.`);
      setImporto('');
      if (refreshCharacterData) await refreshCharacterData();
    } catch (e) {
      setError(e.message || 'Trasferimento non riuscito');
    } finally {
      setBusy(false);
    }
  };

  const loadLog = async (tipo) => {
    if (!selectedCharacterId) return;
    setLogTipo(tipo);
    setLogLoading(true);
    setError('');
    try {
      const res = await fetchEconomiaMovimenti(selectedCharacterId, { tipo, limit: 50 }, onLogout);
      setLogRows(res?.results || []);
    } catch (e) {
      setError(e.message || 'Errore caricamento log');
      setLogRows([]);
    } finally {
      setLogLoading(false);
    }
  };

  if (!economia.modulo_attivo && !char.economia) {
    // payload senza economia: mostra saldi base
  }

  return (
    <PlayerTabShell width="sheet" className="space-y-0">
      <PlayerTabHeader
        icon={<Wallet className="w-7 h-7 text-emerald-400" />}
        title="Economia"
        subtitle="Conti, trasferimento e movimenti"
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <div className="rounded-xl border border-emerald-800/50 bg-emerald-950/40 p-4">
          <div className="flex items-center gap-2 text-emerald-300 text-sm mb-1">
            <Coins className="w-4 h-4" /> Corrente
          </div>
          <p className="text-3xl font-black">{fmt(corrente)}</p>
          <p className="text-xs text-gray-500 mt-1">Stipendio evento e trasferimenti</p>
        </div>
        <div className="rounded-xl border border-amber-800/50 bg-amber-950/30 p-4">
          <div className="flex items-center gap-2 text-amber-300 text-sm mb-1">
            <Wallet className="w-4 h-4" /> Deposito
          </div>
          <p className="text-3xl font-black">{fmt(deposito)}</p>
          <p className="text-xs text-gray-500 mt-1">Guadagni, scommesse, ricompense</p>
        </div>
        <div className="rounded-xl border border-sky-800/50 bg-sky-950/30 p-4">
          <div className="flex items-center gap-2 text-sky-300 text-sm mb-1">
            <Star className="w-4 h-4" /> Punti caratteristica
          </div>
          <p className="text-3xl font-black">{pc}</p>
          <p className="text-xs text-gray-500 mt-1">Pool unico PC</p>
        </div>
      </div>

      <section className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 mb-6">
        <h3 className="font-semibold flex items-center gap-2 mb-2">
          <ArrowRightLeft className="w-4 h-4 text-emerald-400" />
          Trasferimento deposito → corrente
        </h3>
        {!trasf ? (
          <p className="text-sm text-gray-400">
            Disponibile solo in evento attivo (e con modulo conto deposito aperto).
          </p>
        ) : trasf.gia_effettuato ? (
          <p className="text-sm text-amber-300">Hai già trasferito per questo evento.</p>
        ) : (
          <>
            <p className="text-sm text-gray-400 mb-3">
              Tetto: {fmt(trasf.tetto)} CR (frazione × stipendio {fmt(trasf.stipendio_evento)}). Max ora:{' '}
              {fmt(trasf.importo_max)} CR.
            </p>
            <div className="flex flex-wrap gap-2 items-end">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Importo</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="bg-gray-800 border border-gray-600 rounded px-3 py-2 w-36"
                  value={importo}
                  onChange={(e) => setImporto(e.target.value)}
                />
              </div>
              <button
                type="button"
                disabled={busy || !importo}
                onClick={doTransfer}
                className="px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 font-semibold"
              >
                Trasferisci
              </button>
            </div>
          </>
        )}
        {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
        {okMsg && <p className="text-emerald-400 text-sm mt-2">{okMsg}</p>}
      </section>

      <section className="rounded-xl border border-gray-700 bg-gray-900/60 p-4">
        <h3 className="font-semibold mb-3">Log movimenti</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          <button
            type="button"
            onClick={() => loadLog('crediti')}
            className="px-3 py-1.5 text-sm rounded bg-gray-800 border border-gray-600 hover:bg-gray-700"
          >
            Carica movimenti crediti
          </button>
          <button
            type="button"
            onClick={() => loadLog('pc')}
            className="px-3 py-1.5 text-sm rounded bg-gray-800 border border-gray-600 hover:bg-gray-700"
          >
            Carica movimenti PC
          </button>
        </div>
        {logLoading && <p className="text-sm text-gray-400">Caricamento…</p>}
        {!logLoading && logTipo && (
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-sm">
              <thead className="text-gray-400 text-left">
                <tr>
                  <th className="p-2">Data</th>
                  <th className="p-2">Importo</th>
                  {logTipo === 'crediti' && <th className="p-2">Conto</th>}
                  <th className="p-2">Descrizione</th>
                </tr>
              </thead>
              <tbody>
                {logRows.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-2 text-gray-500">
                      Nessun movimento
                    </td>
                  </tr>
                )}
                {logRows.map((r, i) => (
                  <tr key={r.id || i} className="border-t border-gray-800">
                    <td className="p-2 whitespace-nowrap">
                      {r.data ? new Date(r.data).toLocaleString() : '—'}
                    </td>
                    <td className="p-2 font-mono">{r.importo}</td>
                    {logTipo === 'crediti' && (
                      <td className="p-2 text-xs">{r.conto || 'CORRENTE'}</td>
                    )}
                    <td className="p-2">{r.descrizione}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PlayerTabShell>
  );
}

export default memo(EconomiaTab);
