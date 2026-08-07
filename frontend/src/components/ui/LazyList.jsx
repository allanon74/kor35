import React, { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';

/**
 * Lista a batch (virtualizzazione leggera): monta `batchSize` item alla volta
 * e mostra un bottone "Carica altri" — adatto a inventari/cataloghi lunghi su mobile.
 */
export function LazyList({ items, renderItem, batchSize = 10, className = 'space-y-2' }) {
  const list = Array.isArray(items) ? items : [];
  const itemsKey = list.map((item) => item?.id).join(',');
  const [visibleCount, setVisibleCount] = useState(batchSize);

  useEffect(() => {
    setVisibleCount(batchSize);
  }, [itemsKey, batchSize]);

  const displayedItems = list.slice(0, visibleCount);

  return (
    <div className={className}>
      {displayedItems.map(renderItem)}
      {visibleCount < list.length && (
        <button
          type="button"
          onClick={() => setVisibleCount((prev) => Math.min(prev + batchSize, list.length))}
          className="w-full py-3 mt-2 text-sm font-bold text-gray-400 bg-gray-800/50 hover:bg-gray-700 border border-dashed border-gray-600 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          <ChevronDown size={16} aria-hidden="true" /> Carica altri ({list.length - visibleCount})
        </button>
      )}
    </div>
  );
}

export default LazyList;
