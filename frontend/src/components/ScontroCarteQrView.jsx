import React, { useEffect, useState } from 'react';
import { Loader2, Swords } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { carteUniscitiScontro } from '../api';

export default function ScontroCarteQrView({ data, qrcodeId, onClose, onLogout }) {
  const { selectedCharacterId } = useCharacter();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    setLoading(false);
  }, []);

  const handleUnisciti = async () => {
    if (!selectedCharacterId) {
      setError('Seleziona un personaggio.');
      return;
    }
    if (!data?.puo_unirsi && !data?.gia_partecipante) {
      setError('Questo scontro non accetta nuovi giocatori.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await carteUniscitiScontro(
        selectedCharacterId,
        { qrcode_id: qrcodeId, duello_id: data?.duello_id },
        onLogout,
      );
      setSuccess(
        `Sei entrato nello scontro contro ${data?.sfidante?.nome || 'avversario'}. `
        + 'Completa la preparazione nella tab Carte.',
      );
    } catch (e) {
      setError(e?.message || 'Impossibile unirsi allo scontro.');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-6 text-gray-400">
        <Loader2 className="animate-spin" size={28} />
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded border border-sky-800 bg-sky-950/30 p-3">
      <h4 className="flex items-center gap-2 text-sm font-bold text-sky-300">
        <Swords size={16} /> Scontro carte
      </h4>
      <p className="text-xs text-gray-300">
        <strong>{data?.sfidante?.nome}</strong> ha aperto uno scontro in attesa di un avversario.
      </p>
      {error && (
        <p className="rounded border border-red-800 bg-red-950/50 px-2 py-1 text-xs text-red-200">{error}</p>
      )}
      {success && (
        <p className="rounded border border-emerald-800 bg-emerald-950/40 px-2 py-1 text-xs text-emerald-200">{success}</p>
      )}
      <div className="flex gap-2">
        {data?.puo_unirsi && (
          <button
            type="button"
            disabled={busy || !!success}
            onClick={handleUnisciti}
            className="rounded bg-sky-800 px-3 py-1.5 text-xs font-bold disabled:opacity-50"
          >
            {busy ? 'Connessione…' : 'Unisciti allo scontro'}
          </button>
        )}
        {data?.gia_partecipante && (
          <p className="text-xs text-emerald-300">Sei già in questo scontro — apri la tab Carte.</p>
        )}
        {onClose && (
          <button type="button" onClick={onClose} className="rounded bg-gray-800 px-3 py-1.5 text-xs">
            Chiudi
          </button>
        )}
      </div>
      <p className="text-[10px] text-gray-500">
        Dopo l&apos;ingresso scegli mazzo, posta e modalità di gioco nella tab Carte.
      </p>
    </div>
  );
}
