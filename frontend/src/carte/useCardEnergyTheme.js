import { useMemo } from 'react';
import { useCharacter } from '../components/CharacterContext';
import { mergeTemaEnergie } from './carteEnergyAuraMap';
import { buildCardFrameStyles } from './cardFrameUtils';

export function useCardEnergyTheme(apiTema) {
  const { punteggiList } = useCharacter() || {};
  const temaEnergie = useMemo(
    () => mergeTemaEnergie(apiTema, punteggiList),
    [apiTema, punteggiList],
  );

  const getTheme = (energia) => temaEnergie[energia] || temaEnergie.MAR || {
    colore: '#6b7280',
    nome: 'Neutra',
    sigla: '?',
    icona_url: null,
  };

  const getFrameStyles = (energia) => buildCardFrameStyles(getTheme(energia));

  return { temaEnergie, getTheme, getFrameStyles };
}
