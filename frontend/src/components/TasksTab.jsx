import React from 'react';
import { useCharacter } from './CharacterContext';
import MissioniPersonaggioPanel from './MissioniPersonaggioPanel';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import { ListTodo } from 'lucide-react';

/** Tab dedicata alle task/missioni dell'evento per il personaggio selezionato. */
export default function TasksTab({ onLogout }) {
  const { selectedCharacterId, selectedCharacterData, personaggiList } = useCharacter();
  const nome =
    selectedCharacterData?.nome
    || personaggiList?.find((p) => String(p.id) === String(selectedCharacterId))?.nome
    || '';

  return (
    <PlayerTabShell width="wide" animate>
      <PlayerTabHeader
        icon={<ListTodo size={22} />}
        title="Tasks"
        subtitle={nome ? `Missioni per ${nome}` : 'Missioni evento'}
      />
      <MissioniPersonaggioPanel
        personaggioId={selectedCharacterId}
        personaggioNome={nome}
        onLogout={onLogout}
        standalone
      />
    </PlayerTabShell>
  );
}
