import React, { useState } from 'react';
import { Loader2, Package, Sparkles } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { carteApriBustina } from '../api';

export default function BustinaCarteQrView({ data, onClose, onLogout }) {
  const { selectedCharacterId } = useCharacter();
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState('');
  const [carte, setCarte] = useState(null);

  const handleApri = async () => {
    if (!selectedCharacterId || !data?.bustina_id || opening) return;
    if (!data?.puo_accedere) {
      setError('Le carte non sono disponibili per questo personaggio.');
      return;
    }
    setOpening(true);
    setError('');
    try {
      const res = await carteApriBustina(selectedCharacterId, data.bustina_id, onLogout);
      setCarte(res.carte || []);
    } catch (e) {
      setError(e?.message || 'Apertura bustina fallita.');
    } finally {
      setOpening(false);
    }
  };

  return (
    <div className="space-y-4 p-2 text-gray-100">
      <div className="flex items-center gap-3">
        <Package className="text-violet-400" size={40} />
        <div>
          <h3 className="text-xl font-bold">{data?.nome || 'Bustina carte'}</h3>
          {data?.descrizione && <p className="text-sm text-gray-400">{data.descrizione}</p>}
        </div>
      </div>
      <p className="text-sm text-gray-300">
        Costo: <strong>{Number(data?.costo_crediti || 0).toFixed(0)} CR</strong>
        {' · '}
        {data?.carte_per_bustina || 5} carte
      </p>
      {!data?.puo_accedere && (
        <p className="rounded border border-amber-800 bg-amber-950/40 px-3 py-2 text-sm text-amber-200">
          Il gioco carte non è attivo per questo personaggio (modalità testing riservata ai PNG staff).
        </p>
      )}
      {error && (
        <p className="rounded border border-red-800 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p>
      )}
      {carte && (
        <div className="rounded border border-violet-800 bg-violet-950/30 p-3">
          <p className="mb-2 flex items-center gap-1 text-sm font-bold text-violet-200">
            <Sparkles size={16} /> Carte ottenute
          </p>
          <ul className="space-y-1 text-sm">
            {carte.map((c) => (
              <li key={c.id || c.carta?.id}>{c.carta?.nome || c.nome}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={opening || !data?.puo_accedere}
          onClick={handleApri}
          className="rounded bg-violet-800 px-4 py-2 text-sm font-bold disabled:opacity-50"
        >
          {opening ? <Loader2 className="inline animate-spin" size={16} /> : 'Apri bustina'}
        </button>
        <button type="button" onClick={onClose} className="rounded bg-gray-800 px-4 py-2 text-sm">
          Chiudi
        </button>
      </div>
    </div>
  );
}
