import React from 'react';
import { useCharacter } from './CharacterContext';
import MissioniPersonaggioPanel from './MissioniPersonaggioPanel';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import { ListTodo } from 'lucide-react';

/** Tab dedicata alle task/missioni dell'evento per il personaggio selezionato. */
export default function TasksTab({ onLogout, eventoStato = null }) {
  const { selectedCharacterId, selectedCharacterData, personaggiList } = useCharacter();
  const nome =
    selectedCharacterData?.nome
    || personaggiList?.find((p) => String(p.id) === String(selectedCharacterId))?.nome
    || '';
  const eventoTitolo = eventoStato?.titolo || '';
  const nonIscritto = eventoStato?.attivo && eventoStato?.iscritto === false;

  return (
    <PlayerTabShell width="wide" animate>
      <PlayerTabHeader
        icon={<ListTodo size={22} />}
        title="Tasks"
        subtitle={nome ? `Missioni per ${nome}` : 'Missioni evento'}
      />
      {eventoTitolo ? (
        <p className="mb-3 text-xs text-gray-400">
          Evento in corso: <span className="font-semibold text-lime-200">{eventoTitolo}</span>
        </p>
      ) : null}
      {nonIscritto ? (
        <p className="mb-3 rounded-lg border border-amber-700/60 bg-amber-950/30 px-3 py-2 text-xs text-amber-100">
          Non risulti fra i partecipanti dell&apos;evento in corso: le task restano vuote
          finché lo staff non ti iscrive.
        </p>
      ) : null}
      <MissioniPersonaggioPanel
        personaggioId={selectedCharacterId}
        personaggioNome={nome}
        onLogout={onLogout}
        standalone
      />
    </PlayerTabShell>
  );
}
