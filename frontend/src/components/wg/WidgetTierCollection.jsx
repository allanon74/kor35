import React, { useEffect, useMemo, useState } from 'react';
import { getWikiTierCollectionDisplay } from '../../api';
import WidgetTier from './WidgetTier';

const TIER_TYPE_LABELS = {
  all: 'Tutti',
  G0: 'Tabelle Generali',
  T1: 'Tier 1',
  T2: 'Tier 2',
  T3: 'Tier 3',
  T4: 'Tier 4',
};

function sortItems(items, sortBy, sortDir) {
  const copy = [...items];
  const dir = sortDir === 'desc' ? -1 : 1;
  copy.sort((a, b) => {
    if (sortBy === 'widget_created') {
      const aVal = a?.id || 0;
      const bVal = b?.id || 0;
      return (aVal - bVal) * dir;
    }
    const aName = String(a?.tier_nome || '').toLowerCase();
    const bName = String(b?.tier_nome || '').toLowerCase();
    return aName.localeCompare(bName) * dir;
  });
  return copy;
}

export default function WidgetTierCollection({ id }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState('');
  const [tierType, setTierType] = useState('all');
  const [sortBy, setSortBy] = useState('tier_name');
  const [sortDir, setSortDir] = useState('asc');
  const [caratteristicheFilterMode, setCaratteristicheFilterMode] = useState('any');
  const [selectedCaratteristiche, setSelectedCaratteristiche] = useState([]);
  const [badgeMode, setBadgeMode] = useState('compact');

  useEffect(() => {
    setError(false);
    setData(null);
    getWikiTierCollectionDisplay(id)
      .then((res) => {
        setData(res);
        setTierType(res?.tier_type_filter || 'all');
        setSortBy(res?.sort_by || 'tier_name');
        setSortDir(res?.sort_dir || 'asc');
        setCaratteristicheFilterMode(res?.caratteristiche_filter_mode || 'any');
        setBadgeMode(res?.badge_mode || 'compact');
        setSelectedCaratteristiche(Array.isArray(res?.caratteristiche) ? res.caratteristiche.map((c) => c.id) : []);
      })
      .catch((err) => {
        console.error(`Errore caricamento collection widget #${id}:`, err);
        setError(true);
      });
  }, [id]);

  const filteredItems = useMemo(() => {
    const base = Array.isArray(data?.items) ? data.items : [];
    const q = String(search || '').trim().toLowerCase();
    const byType = tierType === 'all' ? base : base.filter((x) => (x?.tier_tipo || '').toUpperCase() === tierType.toUpperCase());
    const bySearch = q ? byType.filter((x) => String(x?.tier_nome || '').toLowerCase().includes(q)) : byType;
    const byCar = selectedCaratteristiche.length === 0
      ? bySearch
      : bySearch.filter((x) => {
          const ids = Array.isArray(x?.tier_caratteristiche) ? x.tier_caratteristiche.map((c) => c.id) : [];
          if (caratteristicheFilterMode === 'all') {
            return selectedCaratteristiche.every((id) => ids.includes(id));
          }
          return selectedCaratteristiche.some((id) => ids.includes(id));
        });
    return sortItems(byCar, sortBy, sortDir);
  }, [data, search, tierType, sortBy, sortDir, selectedCaratteristiche, caratteristicheFilterMode]);

  if (error) {
    return <div className="text-red-500 text-xs border border-red-300 p-2 rounded bg-red-50">Widget Collezione Tier #{id} non disponibile.</div>;
  }
  if (!data) {
    return <div className="animate-pulse h-20 bg-gray-200 rounded my-4"></div>;
  }

  const showControls = data?.show_runtime_filters !== false;

  return (
    <div className="wiki-widget-tier-collection my-6">
      {data.title && <h3 className="text-lg font-bold text-gray-800 mb-2">{data.title}</h3>}

      {showControls && (
        <div className="mb-4 p-3 border border-gray-200 rounded bg-gray-50 flex flex-col md:flex-row gap-2 md:items-center">
          <input
            type="text"
            placeholder="Cerca professione/tier..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 px-2 py-1.5 rounded text-sm flex-1"
          />
          <select value={tierType} onChange={(e) => setTierType(e.target.value)} className="border border-gray-300 px-2 py-1.5 rounded text-sm">
            {Object.entries(TIER_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="border border-gray-300 px-2 py-1.5 rounded text-sm">
            <option value="tier_name">Ordina per nome</option>
            <option value="widget_created">Ordina per creazione widget</option>
          </select>
          <select value={sortDir} onChange={(e) => setSortDir(e.target.value)} className="border border-gray-300 px-2 py-1.5 rounded text-sm">
            <option value="asc">Crescente</option>
            <option value="desc">Decrescente</option>
          </select>
          <select
            multiple
            value={selectedCaratteristiche.map(String)}
            onChange={(e) => setSelectedCaratteristiche(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}
            className="border border-gray-300 px-2 py-1.5 rounded text-sm min-w-[180px] h-[74px]"
            title="Filtra per caratteristiche Tier"
          >
            {(Array.isArray(data?.caratteristiche_available) ? data.caratteristiche_available : []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
          <select
            value={caratteristicheFilterMode}
            onChange={(e) => setCaratteristicheFilterMode(e.target.value)}
            className="border border-gray-300 px-2 py-1.5 rounded text-sm"
          >
            <option value="any">Match qualsiasi</option>
            <option value="all">Match tutte</option>
          </select>
          <select
            value={badgeMode}
            onChange={(e) => setBadgeMode(e.target.value)}
            className="border border-gray-300 px-2 py-1.5 rounded text-sm"
            title="Visualizzazione badge caratteristiche"
          >
            <option value="compact">Badge compatti (sigla)</option>
            <option value="extended">Badge estesi (nome)</option>
          </select>
        </div>
      )}

      {filteredItems.length === 0 ? (
        <div className="text-xs text-gray-600 border border-gray-200 bg-gray-50 rounded p-3">Nessun tier trovato con i filtri correnti.</div>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item) => (
            <WidgetTier key={item.token || item.id} id={item.token || item.id} badgeMode={badgeMode} />
          ))}
        </div>
      )}
    </div>
  );
}
