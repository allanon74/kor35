/** Slot corporei per innesti e mutazioni (allineati a SLOT_CORPO_CHOICES). */
export const SLOT_CORPO = [
  { code: 'HD1', label: 'Testa 1' },
  { code: 'HD2', label: 'Testa 2' },
  { code: 'TR1', label: 'Tronco 1' },
  { code: 'TR2', label: 'Tronco 2' },
  { code: 'RA', label: 'Braccio Dx' },
  { code: 'LA', label: 'Braccio Sx' },
  { code: 'RL', label: 'Gamba Dx' },
  { code: 'LL', label: 'Gamba Sx' },
];

export const TIPO_OGGETTO_LABEL = {
  FIS: 'Oggetto fisico',
  MAT: 'Materia',
  MOD: 'Mod',
  INN: 'Innesto',
  MUT: 'Mutazione',
  AUM: 'Aumento',
  POT: 'Potenziamento',
};

export const TIPI_POTENZIAMENTO = ['MAT', 'MOD', 'POT'];

export function permessiSlotInfusione(infusione) {
  return String(infusione?.slot_corpo_permessi || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isAumentoCorporeo(infusione) {
  return infusione?.tipo_risultato === 'AUM';
}

/** Slot occupati da innesti/mutazioni equipaggiati nell'inventario del PG. */
export function mappaSlotOccupati(oggetti) {
  const map = {};
  (oggetti || []).forEach((o) => {
    if (o?.slot_corpo && o.is_equipaggiato) {
      map[o.slot_corpo] = o.nome || `#${o.id}`;
    }
  });
  return map;
}

export function slotLiberoSelezionabile(code, { occupati = {}, permessi = [] } = {}) {
  if (occupati[code]) return false;
  if (permessi.length && !permessi.includes(code)) return false;
  return true;
}

export function etichettaSlot(code) {
  return SLOT_CORPO.find((s) => s.code === code)?.label || code || '';
}
