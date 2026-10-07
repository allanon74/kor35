import { Skull } from 'lucide-react';

/**
 * Colonne elenco personaggi. Su telefono: nome + tipo in evidenza, proprietario/era
 * su una riga, crediti e KORP come chip. QR, deposito e allineamento restano in tabella desktop.
 */
export function buildPersonaggioListColumns() {
  return [
    {
      key: 'nome',
      header: 'Nome',
      mobileRole: 'title',
      getSortValue: (row) => row.nome || '',
      render: (row) => (
        <span className="font-bold text-white">
          {row.data_morte && <Skull size={12} className="inline mr-1 text-red-400" />}
          {row.nome}
        </span>
      ),
    },
    {
      key: 'tipo',
      header: 'Tipo',
      mobileRole: 'badge',
      getSortValue: (row) => (row.giocante ? 'PG' : 'PNG'),
      render: (row) => (
        <span className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] font-bold uppercase text-gray-200">
          {row.giocante ? 'PG' : 'PNG'}
        </span>
      ),
    },
    {
      key: 'proprietario',
      header: 'Proprietario',
      mobileRole: 'subtitle',
      getSortValue: (row) => row.proprietario_nome || row.proprietario_username || '',
      render: (row) => <span className="text-gray-300">{row.proprietario_nome || row.proprietario_username}</span>,
    },
    {
      key: 'era',
      header: 'Era',
      mobileRole: 'subtitle',
      getSortValue: (row) => row.era_nome || '',
      render: (row) => <span className="text-gray-400">{row.era_nome || '—'}</span>,
    },
    {
      key: 'korp',
      header: 'KORP / Carriere',
      mobileHeader: 'KORP',
      mobileRole: 'meta',
      getSortValue: (row) => (row.korp_attivi || []).join(', '),
      render: (row) => <span className="text-gray-400 text-xs break-words">{(row.korp_attivi || []).join(', ') || '—'}</span>,
    },
    {
      key: 'qr',
      header: 'QR',
      mobileRole: 'hidden',
      getSortValue: (row) => row.qrcode_id || '',
      render: (row) => <span className="font-mono text-xs text-indigo-300">{row.qrcode_id || '—'}</span>,
    },
    {
      key: 'corrente',
      header: 'Corrente',
      mobileRole: 'meta',
      getSortValue: (row) => Number(row.crediti_corrente ?? row.crediti ?? 0),
      render: (row) => <span className="text-emerald-300">{row.crediti_corrente ?? row.crediti}</span>,
      align: 'right',
    },
    {
      key: 'deposito',
      header: 'Deposito',
      mobileRole: 'hidden',
      getSortValue: (row) => Number(row.crediti_deposito ?? 0),
      render: (row) => <span className="text-amber-300">{row.crediti_deposito ?? '—'}</span>,
      align: 'right',
    },
    {
      key: 'prestigio',
      header: 'Prestigio',
      mobileRole: 'meta',
      getSortValue: (row) => Number(row.prestigio || 0),
      render: (row) => <span className="text-fuchsia-300">{row.prestigio ?? 0}</span>,
      align: 'right',
      width: 90,
    },
    {
      key: 'allineamento',
      header: 'L/O/G',
      mobileRole: 'hidden',
      getSortValue: (row) =>
        Number(row.punti_luminosi || 0) + Number(row.punti_oscuri || 0) + Number(row.punti_grigi || 0),
      render: (row) => (
        <span className="text-xs whitespace-nowrap" title="Luminoso / Oscuro / Grigio">
          <span className="text-amber-200">{row.punti_luminosi ?? 0}</span>
          <span className="text-gray-600">/</span>
          <span className="text-violet-300">{row.punti_oscuri ?? 0}</span>
          <span className="text-gray-600">/</span>
          <span className="text-gray-400">{row.punti_grigi ?? 0}</span>
        </span>
      ),
      width: 90,
    },
  ];
}
