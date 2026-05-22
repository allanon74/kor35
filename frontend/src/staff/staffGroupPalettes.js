/** Palette Tailwind condivise per i pulsanti di uno stesso gruppo. */
export const STAFF_GROUP_PALETTES = {
  indigo: ['bg-indigo-500', 'bg-indigo-600', 'bg-indigo-700', 'bg-indigo-800', 'bg-indigo-900'],
  sky: ['bg-sky-500', 'bg-sky-600', 'bg-sky-700', 'bg-sky-800', 'bg-sky-900'],
  blue: ['bg-blue-500', 'bg-blue-600', 'bg-blue-700', 'bg-blue-800', 'bg-blue-900'],
  cyan: ['bg-cyan-500', 'bg-cyan-600', 'bg-cyan-700', 'bg-cyan-800', 'bg-cyan-900'],
  teal: ['bg-teal-500', 'bg-teal-600', 'bg-teal-700', 'bg-teal-800', 'bg-teal-900'],
  emerald: ['bg-emerald-500', 'bg-emerald-600', 'bg-emerald-700', 'bg-emerald-800', 'bg-emerald-900'],
  violet: ['bg-violet-500', 'bg-violet-600', 'bg-violet-700', 'bg-violet-800', 'bg-violet-900'],
  purple: ['bg-purple-500', 'bg-purple-600', 'bg-purple-700', 'bg-purple-800', 'bg-purple-900'],
  fuchsia: ['bg-fuchsia-500', 'bg-fuchsia-600', 'bg-fuchsia-700', 'bg-fuchsia-800', 'bg-fuchsia-900'],
  rose: ['bg-rose-500', 'bg-rose-600', 'bg-rose-700', 'bg-rose-800', 'bg-rose-900'],
  red: ['bg-red-500', 'bg-red-600', 'bg-red-700', 'bg-red-800', 'bg-red-900'],
  orange: ['bg-orange-500', 'bg-orange-600', 'bg-orange-700', 'bg-orange-800', 'bg-orange-900'],
  amber: ['bg-amber-500', 'bg-amber-600', 'bg-amber-700', 'bg-amber-800', 'bg-amber-900'],
  stone: ['bg-stone-500', 'bg-stone-600', 'bg-stone-700', 'bg-stone-800', 'bg-stone-900'],
  slate: ['bg-slate-500', 'bg-slate-600', 'bg-slate-700', 'bg-slate-800', 'bg-slate-900'],
};

export const STAFF_PALETTE_OPTIONS = [
  { id: 'indigo', label: 'Indaco', sample: 'bg-indigo-600' },
  { id: 'sky', label: 'Cielo', sample: 'bg-sky-600' },
  { id: 'blue', label: 'Blu', sample: 'bg-blue-600' },
  { id: 'cyan', label: 'Ciano', sample: 'bg-cyan-600' },
  { id: 'teal', label: 'Teal', sample: 'bg-teal-600' },
  { id: 'emerald', label: 'Smeraldo', sample: 'bg-emerald-600' },
  { id: 'violet', label: 'Viola', sample: 'bg-violet-600' },
  { id: 'purple', label: 'Porpora', sample: 'bg-purple-600' },
  { id: 'fuchsia', label: 'Fucsia', sample: 'bg-fuchsia-600' },
  { id: 'rose', label: 'Rosa', sample: 'bg-rose-600' },
  { id: 'red', label: 'Rosso', sample: 'bg-red-600' },
  { id: 'orange', label: 'Arancio', sample: 'bg-orange-600' },
  { id: 'amber', label: 'Ambra', sample: 'bg-amber-600' },
  { id: 'stone', label: 'Pietra', sample: 'bg-stone-600' },
  { id: 'slate', label: 'Ardesia', sample: 'bg-slate-600' },
];

export const DEFAULT_GROUP_PALETTE_BY_ID = {
  evento: 'indigo',
  database: 'blue',
  giocatori: 'teal',
  comunicazione: 'emerald',
  sistema: 'slate',
  altro: 'stone',
};

export const PINNED_PALETTE_ID = 'violet';

export function getPaletteColor(paletteId, index = 0) {
  const shades = STAFF_GROUP_PALETTES[paletteId] || STAFF_GROUP_PALETTES.slate;
  return shades[Math.abs(index) % shades.length];
}

export function resolveGroupPalette(group) {
  if (group?.palette && STAFF_GROUP_PALETTES[group.palette]) {
    return group.palette;
  }
  return DEFAULT_GROUP_PALETTE_BY_ID[group?.id] || 'slate';
}
