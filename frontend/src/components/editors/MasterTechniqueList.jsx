import React, { useMemo } from 'react';
import { useCharacter } from '../CharacterContext';
import IconaPunteggio from '../IconaPunteggio';
import MasterGenericList from './MasterGenericList';
import StaffQrBadge from './StaffQrBadge';

/**
 * MasterTechniqueList
 * Wrapper di MasterGenericList specializzato per la gestione di 
 * Infusioni, Tessiture e Cerimoniali.
 */
const MasterTechniqueList = ({ 
  items, 
  title, 
  onAdd, 
  onEdit, 
  onDelete, 
  onScanQr,
  onMinigioco,
  addLabel = "Nuovo",
  loading = false 
}) => {
  const { punteggiList } = useCharacter();

  // 1. Configurazione Filtri (Livelli e Aure)
  const filterConfig = useMemo(
    () => [
      {
        key: 'livello_virtual', // Chiave virtuale, usiamo match personalizzato
        label: 'Livelli',
        type: 'button',
        options: [1, 2, 3, 4, 5, 6, 7].map((l) => ({ id: l, label: l.toString() })),
        // Logica di matching per coprire sia il campo 'livello' che 'liv'
        match: (item, values) => values.includes(item.livello || item.liv),
      },
      {
        key: 'aura_richiesta',
        label: 'Aure',
        type: 'icon',
        options: punteggiList.filter((p) => p.tipo === 'AU'),
        renderOption: (opt) => (
          <IconaPunteggio
            url={opt.icona_url || opt.icona}
            color={opt.colore}
            size="xs"
            mode="cerchio_inv"
          />
        ),
        // Matcher per gestire ID o oggetti nidificati per l'aura
        match: (item, values) => {
          const itemAuraId = item.aura_richiesta?.id || item.aura_richiesta;
          return values.some((v) => String(v) === String(itemAuraId));
        },
      },
    ],
    [punteggiList],
  );

  // 2. Definizione Colonne
  const columns = useMemo(
    () => [
      {
        key: 'qr',
        header: 'QR',
        width: '44px',
        align: 'center',
        getSortValue: (item) => (item.has_qrcode ? 1 : 0),
        getFilterValue: (item) => (item.has_qrcode ? 'QR' : ''),
        render: (item) => <StaffQrBadge hasQr={item.has_qrcode} />,
      },
      {
        key: 'lvl',
        header: 'Lvl',
        width: '60px',
        align: 'center',
        getSortValue: (item) => item.livello || item.liv || 0,
        render: (item) => (
          <span className="font-mono font-bold text-gray-400">
            {item.livello || item.liv}
          </span>
        ),
      },
      {
        key: 'au',
        header: 'Au',
        width: '50px',
        align: 'center',
        getSortValue: (item) => {
          const auraId = item.aura_richiesta?.id || item.aura_richiesta;
          const aura = item.aura_richiesta?.id
            ? item.aura_richiesta
            : punteggiList.find((p) => String(p.id) === String(auraId));
          return aura?.ordine ?? 999;
        },
        getFilterValue: (item) => {
          const auraId = item.aura_richiesta?.id || item.aura_richiesta;
          const aura = item.aura_richiesta?.id
            ? item.aura_richiesta
            : punteggiList.find((p) => String(p.id) === String(auraId));
          return aura?.nome || '';
        },
        render: (item) => {
          const auraId = item.aura_richiesta?.id || item.aura_richiesta;
          const aura = item.aura_richiesta?.id
            ? item.aura_richiesta
            : punteggiList.find((p) => String(p.id) === String(auraId));
          return aura ? (
            <div className="flex justify-center" title={aura.nome}>
              <IconaPunteggio
                url={aura.icona_url || aura.icona}
                color={aura.colore}
                size="xs"
                mode="cerchio_inv"
              />
            </div>
          ) : <span className="text-gray-600 text-[10px]">—</span>;
        },
      },
      {
        key: 'nome',
        header: 'Nome',
        getSortValue: (item) => item.nome || '',
        render: (item) => (
          <div className="font-bold text-cyan-50 truncate max-w-[150px] md:max-w-xs">
            {item.nome}
          </div>
        ),
      },
      {
        key: 'mattoni',
        header: 'Mattoni',
        getSortValue: (item) => (Array.isArray(item.componenti) ? item.componenti.length : 0),
        getFilterValue: (item) => {
          const rows = Array.isArray(item.componenti) ? item.componenti : [];
          return rows.map((row) => `${row.nome || '?'} x${row.valore ?? 1}`).join(' ');
        },
        render: (item) => {
          const rows = Array.isArray(item.componenti) ? item.componenti : [];
          if (!rows.length) return <span className="text-[10px] text-gray-600">—</span>;
          return (
            <div className="text-[10px] text-gray-300 leading-tight max-w-[260px]">
              {rows.map((row) => `${row.nome || '?'} x${row.valore ?? 1}`).join(' · ')}
            </div>
          );
        },
      },
    ],
    [punteggiList],
  );

  // 3. Logica di Ordinamento: Aura -> Livello -> Nome
  const sortLogic = useMemo(
    () => (a, b) => {
      const auraAId = a.aura_richiesta?.id || a.aura_richiesta;
      const auraBId = b.aura_richiesta?.id || b.aura_richiesta;
      const auraAObj = a.aura_richiesta?.id
        ? a.aura_richiesta
        : punteggiList.find((p) => String(p.id) === String(auraAId));
      const auraBObj = b.aura_richiesta?.id
        ? b.aura_richiesta
        : punteggiList.find((p) => String(p.id) === String(auraBId));
      const auraA = auraAObj?.ordine ?? 999;
      const auraB = auraBObj?.ordine ?? 999;
      if (auraA !== auraB) return auraA - auraB;

      const livA = a.livello || a.liv || 0;
      const livB = b.livello || b.liv || 0;
      if (livA !== livB) return livA - livB;

      return (a.nome || '').localeCompare(b.nome || '');
    },
    [punteggiList],
  );

  return (
    <MasterGenericList 
      title={title}
      items={items}
      columns={columns}
      filterConfig={filterConfig}
      sortLogic={sortLogic}
      onAdd={onAdd} 
      onEdit={onEdit} 
      onScanQr={onScanQr}
      onMinigioco={onMinigioco}
      onDelete={onDelete}
      loading={loading}
      addLabel={addLabel}
      emptyMessage="Seleziona un Livello o un'Aura per visualizzare i dati."
    />
  );
};

export default MasterTechniqueList;