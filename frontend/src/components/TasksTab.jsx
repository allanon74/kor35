import React from 'react';
import { useCharacter } from './CharacterContext';
import MissioniPersonaggioPanel from './MissioniPersonaggioPanel';

/** Tab dedicata alle task/missioni dell'evento per il personaggio selezionato. */
export default function TasksTab({ onLogout }) {
  const { selectedCharacterId, selectedCharacterData, personaggiList } = useCharacter();
  const nome =
    selectedCharacterData?.nome
    || personaggiList?.find((p) => String(p.id) === String(selectedCharacterId))?.nome
    || '';

  return (
    <div className="h-full overflow-y-auto p-4 animate-fadeIn">
      <MissioniPersonaggioPanel
        personaggioId={selectedCharacterId}
        personaggioNome={nome}
        onLogout={onLogout}
        standalone
      />
    </div>
  );
}
