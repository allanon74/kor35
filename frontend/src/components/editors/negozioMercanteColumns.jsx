/** Colonne elenco negozi: card compatte su telefono, tabella completa da `lg`. */
export const NEGOZIO_COLUMNS = [
  {
    header: 'Nome',
    key: 'nome',
    mobileRole: 'title',
    sortable: true,
    filterable: true,
    render: (row) => <span className="font-semibold text-white">{row.nome}</span>,
  },
  {
    header: 'Tipo',
    key: 'tipo_negozio',
    mobileRole: 'badge',
    sortable: true,
    render: (row) => (
      <span className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] font-bold uppercase text-gray-200">
        <span className="lg:hidden">{row.tipo_negozio === 'CORP' ? 'Corp' : 'QR'}</span>
        <span className="hidden lg:inline">{row.tipo_negozio === 'CORP' ? 'Corporativo' : 'QR'}</span>
      </span>
    ),
  },
  {
    header: 'Attivo',
    key: 'attivo',
    mobileRole: 'badge',
    sortable: true,
    render: (row) => (
      <span
        className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
          row.attivo ? 'bg-emerald-900/70 text-emerald-300' : 'bg-gray-800 text-gray-500'
        }`}
      >
        <span className="lg:hidden">{row.attivo ? 'On' : 'Off'}</span>
        <span className="hidden lg:inline">{row.attivo ? 'Sì' : 'No'}</span>
      </span>
    ),
  },
  {
    header: 'Modalità',
    key: 'negozio_prestiti',
    mobileRole: 'meta',
    sortable: true,
    render: (row) =>
      row.negozio_prestiti ? (
        <span className="text-sky-300">Prestiti (max {row.limite_prestiti_per_personaggio || 1})</span>
      ) : (
        <span className="text-gray-400">Vendita</span>
      ),
  },
  {
    header: 'Cassa',
    key: 'saldo_crediti',
    mobileRole: 'meta',
    sortable: true,
    align: 'right',
    render: (row) => (
      <span className="font-mono text-amber-300">{row.saldo_crediti ?? 0} CR</span>
    ),
  },
  {
    header: 'Voci',
    key: 'voci_count',
    mobileRole: 'meta',
    sortable: true,
    getSortValue: (row) => (row.voci || []).length,
    render: (row) => (row.voci || []).length,
  },
  {
    header: 'QR',
    key: 'qr_code',
    mobileRole: 'meta',
    render: (row) => (row.qr_code ? `#${row.qr_code}` : '—'),
  },
];
