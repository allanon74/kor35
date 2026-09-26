import React, { useState } from 'react';
import { FileSignature } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { contrattiAzione } from '../api';

const STATO_LABEL = {
  IN_ATTESA: 'In attesa di firma',
  STIPULATO: 'Stipulato',
  SCADUTO: 'Scaduto',
  RIFIUTATO: 'Rifiutato',
  RISOLTO: 'Risolto',
  ANNULLATO: 'Annullato',
};

function formatScadenza(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function ContrattoQrView({ data, onClose, onLogout }) {
  const { selectedCharacterId } = useCharacter();
  const [scheda, setScheda] = useState(data || {});
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState('');

  const esegui = async (azione) => {
    if (!selectedCharacterId || !scheda?.id) return;
    setBusy(true);
    setErrore('');
    try {
      const aggiornato = await contrattiAzione(selectedCharacterId, scheda.id, azione, {}, onLogout);
      setScheda(aggiornato);
    } catch (e) {
      setErrore(e.message || 'Operazione non riuscita.');
    } finally {
      setBusy(false);
    }
  };

  const scadenza = formatScadenza(scheda.scadenza);

  return (
    <div className="space-y-4 text-gray-100">
      <div className="flex items-center gap-2 text-amber-300">
        <FileSignature size={20} />
        <h2 className="text-lg font-bold">{scheda.nome || 'Contratto'}</h2>
      </div>
      <p className="text-xs uppercase tracking-wide text-gray-400">
        {STATO_LABEL[scheda.stato] || scheda.stato}
        {scadenza ? ` · fino al ${scadenza}` : ''}
      </p>
      <p className="text-sm text-gray-300">
        Proponente: {scheda.proponente?.nome || '—'}
        {scheda.cliente ? ` · Cliente: ${scheda.cliente.nome}` : ''}
      </p>
      <div className="whitespace-pre-wrap rounded border border-gray-700 bg-gray-950 p-3 text-sm leading-relaxed">
        {scheda.testo || 'Nessun testo.'}
      </div>
      {scheda.motivo_blocco ? <p className="text-sm text-amber-300">{scheda.motivo_blocco}</p> : null}
      {errore ? <p className="text-sm text-red-400">{errore}</p> : null}
      <div className="flex flex-wrap gap-2">
        {scheda.puo_firmare ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => esegui('firma')}
            className="rounded bg-emerald-700 px-3 py-2 text-sm font-semibold hover:bg-emerald-600 disabled:opacity-50"
          >
            {scadenza ? `Sottoscrivi fino al ${scadenza}` : 'Sottoscrivi'}
          </button>
        ) : null}
        {scheda.puo_rifiutare ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => esegui('rifiuta')}
            className="rounded bg-gray-700 px-3 py-2 text-sm font-semibold hover:bg-gray-600 disabled:opacity-50"
          >
            Rifiuta
          </button>
        ) : null}
        <button type="button" onClick={onClose} className="rounded border border-gray-600 px-3 py-2 text-sm">
          Chiudi
        </button>
      </div>
    </div>
  );
}
