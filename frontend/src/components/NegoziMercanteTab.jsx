import React, { useCallback, useEffect, useState } from 'react';
import { Store } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { fetchNegoziCorporativi } from '../api';
import NegozioMercanteModal from './NegozioMercanteModal';

const NegoziMercanteTab = ({ onLogout }) => {
  const { selectedCharacterId } = useCharacter();
  const [negozi, setNegozi] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState(null);
  const [subTab, setSubTab] = useState(null);

  const load = useCallback(async () => {
    if (!selectedCharacterId) {
      setNegozi([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchNegoziCorporativi(selectedCharacterId, onLogout);
      setNegozi(Array.isArray(data) ? data : []);
      if (data?.length && !subTab) setSubTab(data[0].id);
    } catch (e) {
      console.error(e);
      setNegozi([]);
    } finally {
      setLoading(false);
    }
  }, [selectedCharacterId, onLogout, subTab]);

  useEffect(() => {
    load();
  }, [load]);

  if (!selectedCharacterId) {
    return <p className="p-4 text-gray-400">Seleziona un personaggio.</p>;
  }

  if (loading) {
    return <p className="p-4 text-gray-400">Caricamento negozi corporativi…</p>;
  }

  if (!negozi.length) {
    return (
      <p className="p-4 text-gray-500 text-sm">
        Nessun negozio corporativo accessibile per questo personaggio.
      </p>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-lg font-bold text-amber-400 flex items-center gap-2">
        <Store size={20} />
        Negozi corporativi
      </h2>
      <div className="flex flex-wrap gap-2 border-b border-gray-700 pb-2">
        {negozi.map((n) => (
          <button
            key={n.id}
            type="button"
            onClick={() => setSubTab(n.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${
              subTab === n.id
                ? 'bg-amber-700 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            {n.nome}
          </button>
        ))}
      </div>
      {subTab && (
        <button
          type="button"
          onClick={() => setActiveId(subTab)}
          className="w-full py-3 rounded-xl bg-amber-800/80 hover:bg-amber-700 text-white font-bold"
        >
          Apri negozio
        </button>
      )}
      {activeId && (
        <NegozioMercanteModal
          negozioId={activeId}
          onClose={() => {
            setActiveId(null);
            load();
          }}
          onLogout={onLogout}
        />
      )}
    </div>
  );
};

export default NegoziMercanteTab;
