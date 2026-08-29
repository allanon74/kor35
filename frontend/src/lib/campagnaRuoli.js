/** Ruoli campagna: etichette UI (allineate a CampagnaUtente.ruolo). */

export const CAMPAGNA_ROLE_LABELS = {
  PLAYER: 'Giocatore',
  REDACTOR: 'Redactor',
  HELPER: 'Aiuto staff',
  STAFFER: 'Staffer',
  MASTER: 'Master',
  HEAD_MASTER: 'Head Master',
};

export function campagnaRuoloLabel(ruolo) {
  const key = String(ruolo || '').trim().toUpperCase();
  return CAMPAGNA_ROLE_LABELS[key] || key || 'Giocatore';
}
