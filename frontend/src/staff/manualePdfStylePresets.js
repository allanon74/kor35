/** Preset stile PDF (allineati a backend/gestione_plot/wiki_pdf_styles.py) */

export const MANUALE_PDF_PRESET_OPTIONS = [
  { value: 'giocatore', label: 'Giocatore — A5 compatto' },
  { value: 'master', label: 'Master — A4 completo' },
  { value: 'reference', label: 'Reference — A5 solo testo' },
  { value: 'stampa_economica', label: 'Stampa economica — A4 B/N' },
  { value: 'personalizzato', label: 'Personalizzato (override sotto)' },
];

export const MANUALE_PDF_OVERRIDE_FIELDS = [
  { key: 'formato', label: 'Formato', type: 'select', options: ['A4', 'A5'] },
  { key: 'margini', label: 'Margini', type: 'select', options: ['stretto', 'normale', 'ampio'] },
  { key: 'font_family', label: 'Font', type: 'select', options: ['serif', 'sans'] },
  { key: 'font_size_pt', label: 'Dimensione testo (pt)', type: 'number', min: 8, max: 14 },
  { key: 'line_height', label: 'Interlinea', type: 'number', min: 1.2, max: 1.8, step: 0.05 },
  {
    key: 'immagini',
    label: 'Immagini',
    type: 'select',
    options: [
      { value: 'si', label: 'Sì' },
      { value: 'inline_piccole', label: 'Solo piccole' },
      { value: 'no', label: 'No' },
    ],
  },
  {
    key: 'widget_modalita',
    label: 'Widget regole',
    type: 'select',
    options: [
      { value: 'completo', label: 'Completo' },
      { value: 'compatto', label: 'Compatto' },
      { value: 'solo_testo', label: 'Solo elenco nomi' },
    ],
  },
  { key: 'indice_profondita', label: 'Profondità indice', type: 'number', min: 1, max: 4 },
  {
    key: 'colore',
    label: 'Colore',
    type: 'select',
    options: [
      { value: 'accento', label: 'Brand' },
      { value: 'bn', label: 'Bianco e nero' },
    ],
  },
  {
    key: 'copertina',
    label: 'Copertina',
    type: 'select',
    options: [
      { value: 'immagine', label: 'Con immagine' },
      { value: 'minimal', label: 'Minimal' },
      { value: 'testo', label: 'Solo testo' },
    ],
  },
  {
    key: 'colophon',
    label: 'Colophon',
    type: 'select',
    options: [
      { value: 'breve', label: 'Breve' },
      { value: 'dettagliato', label: 'Dettagliato' },
      { value: 'off', label: 'Off' },
    ],
  },
];

export const emptyStileOverride = () => ({});
