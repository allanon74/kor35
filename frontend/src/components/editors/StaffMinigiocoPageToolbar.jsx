import React, { useCallback, useState } from 'react';
import { Puzzle } from 'lucide-react';
import StaffMinigiocoDefaultModal from './StaffMinigiocoDefaultModal';
import {
  loadPageMinigiocoSettings,
  setPageMinigiocoApplyToNew,
} from '../../utils/staffMinigiocoDefaults';

const StaffMinigiocoPageToolbar = ({ pageKey, pageLabel, onLogout }) => {
  const [applyToNew, setApplyToNew] = useState(() => loadPageMinigiocoSettings(pageKey).applyToNew);
  const [defaultModalOpen, setDefaultModalOpen] = useState(false);

  const toggleApply = useCallback(() => {
    const next = !applyToNew;
    setApplyToNew(next);
    setPageMinigiocoApplyToNew(pageKey, next);
  }, [applyToNew, pageKey]);

  const hasDefault = Boolean(loadPageMinigiocoSettings(pageKey).config);

  return (
    <>
      <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg border border-indigo-900/40 bg-indigo-950/20 text-sm">
        <span className="text-indigo-300 font-semibold text-xs uppercase tracking-wide flex items-center gap-1">
          <Puzzle size={14} />
          Minigioco pagina
        </span>
        <button
          type="button"
          className="px-2 py-1 rounded bg-indigo-800 hover:bg-indigo-700 text-xs"
          onClick={() => setDefaultModalOpen(true)}
        >
          {hasDefault ? 'Modifica default' : 'Crea default minigioco'}
        </button>
        <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer ml-auto">
          <input type="checkbox" checked={applyToNew} onChange={toggleApply} />
          Applica default ai nuovi QR
        </label>
        {!hasDefault && applyToNew && (
          <span className="text-[10px] text-amber-400 w-full">
            Attiva «Crea default minigioco» prima di associare nuovi QR.
          </span>
        )}
      </div>
      <StaffMinigiocoDefaultModal
        pageKey={pageKey}
        pageLabel={pageLabel}
        open={defaultModalOpen}
        onClose={() => setDefaultModalOpen(false)}
        onLogout={onLogout}
      />
    </>
  );
};

export default StaffMinigiocoPageToolbar;
