import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import RichHtml from './RichHtml';

export const TESTO_NOTA_INVIO = 'Inviata per approvazione';

function testoVisibile(value) {
  return String(value || '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Note da mostrare: lo storico datato, oppure la nota staff legacy se il log non c'è ancora. */
export function noteProposta(proposta) {
  const log = Array.isArray(proposta?.note_log)
    ? proposta.note_log.filter((nota) => testoVisibile(nota?.testo))
    : [];
  if (log.length) {
    return [...log].sort((a, b) => String(a.creata_il || '').localeCompare(String(b.creata_il || '')));
  }
  const legacy = String(proposta?.note_staff || '').trim();
  if (!legacy) return [];
  return [{
    id: 'legacy-note-staff',
    testo: legacy,
    origine: 'STAFF',
    creata_il: proposta?.data_invio || proposta?.data_creazione || null,
  }];
}

export function formatDataNota(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '';
  return data.toLocaleString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function RigaNota({ nota, compatta = false }) {
  const quando = formatDataNota(nota?.creata_il);
  const invio = nota?.origine === 'INVIO' || testoVisibile(nota?.testo) === TESTO_NOTA_INVIO;
  return (
    <div className="min-w-0">
      {quando ? (
        <div className="text-[10px] font-bold uppercase tracking-wide text-amber-200/80">{quando}</div>
      ) : null}
      {invio ? (
        <p className={`text-sm text-amber-50 break-words ${compatta ? 'line-clamp-3' : ''}`}>{TESTO_NOTA_INVIO}</p>
      ) : (
        <RichHtml
          content={nota?.testo || ''}
          className={`text-sm text-amber-50 break-words ${compatta ? 'line-clamp-3' : ''}`}
        />
      )}
    </div>
  );
}

/**
 * Mostra l'ultima nota. Un tap apre lo storico completo (e lo richiude).
 * Lo stop della propagazione evita di aprire la proposta quando la card è cliccabile.
 */
export default function NotePropostaElenco({ proposta, className = '' }) {
  const [aperto, setAperto] = useState(false);
  const note = useMemo(() => noteProposta(proposta), [proposta]);
  if (!note.length) return null;
  const ultima = note[note.length - 1];
  const storico = note.slice(0, -1);

  return (
    <div
      className={`rounded-lg border border-amber-700/60 bg-amber-950/40 min-w-0 ${className}`}
      onClick={(event) => event.stopPropagation()}
    >
      <button
        type="button"
        className="w-full min-h-11 text-left px-3 py-2 flex items-start gap-2"
        aria-expanded={aperto}
        onClick={() => setAperto((value) => !value)}
      >
        <span className="min-w-0 flex-1">
          <span className="font-black uppercase tracking-widest text-[10px] text-amber-300 block mb-1">
            Ultima nota
          </span>
          <RigaNota nota={ultima} compatta={!aperto} />
          <span className="text-[10px] text-amber-200/70 mt-1 block">
            {aperto ? 'Nascondi storico' : (storico.length ? `Storico (${storico.length})` : 'Storico')}
          </span>
        </span>
        <span className="shrink-0 text-amber-200 mt-0.5" aria-hidden="true">
          {aperto ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>
      {aperto ? (
        <div className="border-t border-amber-800/60 px-3 py-2">
          {storico.length === 0 ? (
            <p className="text-xs text-amber-100/70">Nessuna nota precedente.</p>
          ) : (
            <ul className="space-y-3">
              {storico.map((nota) => (
                <li key={nota.id || `${nota.creata_il}-${nota.origine}`} className="min-w-0">
                  <RigaNota nota={nota} />
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
