import React, { useEffect, useState } from 'react';
import { Loader2, Swords } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { carteGetCollezione, carteInvitaDuello } from '../api';

const MAZZO_DUELLO_SIZE = 15;

/**
 * Sfida duello da scan QR personaggio — solo modalità TEST (lista avversari).
 * In OPEN la sfida passa dalla lobby «Apri scontro» (QR sessione), non dal QR PG.
 */
export default function PersonaggioDuelloQrView({ avversario, qrcodeId, onClose, onLogout }) {
  const { selectedCharacterId } = useCharacter();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [mazzoIds, setMazzoIds] = useState([]);
  const [leaderId, setLeaderId] = useState(null);
  const [duelloAvvio, setDuelloAvvio] = useState('off');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!selectedCharacterId) {
        setLoading(false);
        return;
      }
      try {
        const data = await carteGetCollezione(selectedCharacterId, onLogout);
        if (cancelled) return;
        setDuelloAvvio(data?.duello_avvio || 'off');
        const defaultMazzo = (data?.mazzi || []).find((m) => m.is_default) || data?.mazzi?.[0];
        if (defaultMazzo?.carte_possedute_ids?.length === MAZZO_DUELLO_SIZE) {
          setMazzoIds(defaultMazzo.carte_possedute_ids);
          setLeaderId(defaultMazzo.leader_carta_posseduta_id || null);
        } else if ((data?.carte || []).length >= MAZZO_DUELLO_SIZE) {
          setMazzoIds((data.carte || []).slice(0, MAZZO_DUELLO_SIZE).map((c) => c.id));
        }
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Errore caricamento mazzo.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedCharacterId, onLogout]);

  const handleSfida = async () => {
    if (!selectedCharacterId || !qrcodeId || mazzoIds.length !== MAZZO_DUELLO_SIZE || !leaderId) {
      setError(`Servono ${MAZZO_DUELLO_SIZE} carte nel mazzo e un Leader.`);
      return;
    }
    if (String(avversario?.id) === String(selectedCharacterId)) {
      setError('Non puoi sfidare il tuo stesso personaggio.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await carteInvitaDuello(
        selectedCharacterId,
        { mazzo_ids: mazzoIds, leader_id: leaderId, qrcode_id: qrcodeId },
        onLogout,
      );
      setSuccess(
        `Sfida inviata a ${avversario?.nome || 'avversario'}. Attendi che accetti dalla tab Carte.`,
      );
    } catch (e) {
      setError(e?.message || 'Invito duello fallito.');
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

  if (duelloAvvio === 'lobby') {
    return (
      <div className="mt-4 space-y-2 rounded border border-amber-800 bg-amber-950/40 p-3 text-sm text-amber-100">
        <h4 className="flex items-center gap-2 font-bold text-amber-300">
          <Swords size={16} /> Duello carte (modalità aperta)
        </h4>
        <p className="text-xs">
          In evento <strong>OPEN</strong> non si sfida più tramite QR del personaggio.
          Usa <strong>Apri scontro</strong> nella tab Carte: mostrerai un QR di sessione
          e l&apos;avversario si unisce con lo scanner.
        </p>
        <p className="text-xs text-gray-400">
          Hai scansionato <strong>{avversario?.nome}</strong> — per un duello usa la lobby scontro.
        </p>
      </div>
    );
  }

  if (duelloAvvio !== 'lista') {
    return (
      <p className="rounded border border-amber-800 bg-amber-950/40 px-3 py-2 text-sm text-amber-200">
        I duelli carte non sono disponibili per questo personaggio in questa modalità.
      </p>
    );
  }

  return (
    <div className="mt-4 space-y-3 rounded border border-sky-800 bg-sky-950/30 p-3">
      <h4 className="flex items-center gap-2 text-sm font-bold text-sky-300">
        <Swords size={16} /> Sfida a duello carte (TEST)
      </h4>
      <p className="text-xs text-gray-400">
        Invierai una richiesta di partita a <strong className="text-white">{avversario?.nome}</strong>.
        L&apos;avversario dovrà accettare sul proprio terminale (tab Carte).
      </p>
      <p className="text-xs text-gray-500">
        Mazzo: {mazzoIds.length}/{MAZZO_DUELLO_SIZE} carte
        {mazzoIds.length !== MAZZO_DUELLO_SIZE && ' — configura il mazzo nella tab Carte prima di sfidare.'}
      </p>
      {error && (
        <p className="rounded border border-red-800 bg-red-950/50 px-2 py-1 text-xs text-red-200">{error}</p>
      )}
      {success && (
        <p className="rounded border border-emerald-800 bg-emerald-950/40 px-2 py-1 text-xs text-emerald-200">{success}</p>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={busy || mazzoIds.length !== MAZZO_DUELLO_SIZE || !!success}
          onClick={handleSfida}
          className="rounded bg-sky-800 px-3 py-1.5 text-xs font-bold disabled:opacity-50"
        >
          {busy ? 'Invio…' : 'Invia sfida'}
        </button>
        {onClose && (
          <button type="button" onClick={onClose} className="rounded bg-gray-800 px-3 py-1.5 text-xs">
            Chiudi
          </button>
        )}
      </div>
    </div>
  );
}
