import React from 'react';
import { useCharacter } from '../CharacterContext';
import IconaPunteggio from '../IconaPunteggio';
import MasterGenericList from './MasterGenericList';

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
  addLabel = "Nuovo",
  loading = false 
}) => {
  const { punteggiList } = useCharacter();

  // 1. Configurazione Filtri (Livelli e Aure)
  const filterConfig = [
    {
      key: 'livello_virtual', // Chiave virtuale, usiamo match personalizzato
      label: 'Livelli',
      type: 'button',
      options: [1, 2, 3, 4, 5, 6, 7].map(l => ({ id: l, label: l.toString() })),
      // Logica di matching per coprire sia il campo 'livello' che 'liv'
      match: (item, values) => values.includes(item.livello || item.liv)
    },
    {
      key: 'aura_richiesta',
      label: 'Aure',
      type: 'icon',
      options: punteggiList.filter(p => p.tipo === 'AU'),
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
        return values.includes(itemAuraId);
      }
    }
  ];

  // 2. Definizione Colonne
  const columns = [
    { 
      header: 'Lvl', 
      width: '60px', 
      align: 'center',
      render: (item) => (
        <span className="font-mono font-bold text-gray-400">
          {item.livello || item.liv}
        </span>
      )
    },
    { 
      header: 'Au', 
      width: '50px', 
      align: 'center',
      render: (item) => {
        const aura = item.aura_richiesta;
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
      }
    },
    { 
      header: 'Nome', 
      render: (item) => (
        <div className="font-bold text-cyan-50 truncate max-w-[150px] md:max-w-xs">
          {item.nome}
        </div>
      )
    }
  ];

  // 3. Logica di Ordinamento: Aura -> Livello -> Nome
  const sortLogic = (a, b) => {
    // Ordine Aura
    const auraA = a.aura_richiesta?.ordine ?? 999;
    const auraB = b.aura_richiesta?.ordine ?? 999;
    if (auraA !== auraB) return auraA - auraB;

    // Ordine Livello
    const livA = a.livello || a.liv || 0;
    const livB = b.livello || b.liv || 0;
    if (livA !== livB) return livA - livB;

    // Ordine Alfabetico
    return (a.nome || "").localeCompare(b.nome || "");
  };

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
      onDelete={onDelete}
      loading={loading}
      addLabel={addLabel}
      emptyMessage="Seleziona un Livello o un'Aura per visualizzare i dati."
    />
  );
};

export default MasterTechniqueList;