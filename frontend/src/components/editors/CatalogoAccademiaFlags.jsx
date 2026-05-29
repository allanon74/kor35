import React from 'react';

/**
 * Checkbox condivisi per escludere contenuti dall'Accademia o da tutti i negozi.
 */
export default function CatalogoAccademiaFlags({
  formData,
  setFormData,
  syncTecnicaNonAcquistabile = false,
}) {
  const setEscluso = (checked) => {
    const next = { ...formData, escluso_negozio_ufficiale: checked };
    if (syncTecnicaNonAcquistabile && checked) {
      next.non_acquistabile = true;
    }
    if (!syncTecnicaNonAcquistabile && checked) {
      next.in_vendita = false;
    }
    setFormData(next);
  };

  const setNonVendibile = (checked) => {
    const next = { ...formData, non_vendibile: checked };
    if (syncTecnicaNonAcquistabile && checked) {
      next.non_acquistabile = true;
    }
    if (!syncTecnicaNonAcquistabile && checked) {
      next.in_vendita = false;
    }
    setFormData(next);
  };

  return (
    <div className="flex flex-wrap gap-6 pt-2 border-t border-gray-800">
      <label className="flex items-center gap-2 text-xs font-bold cursor-pointer hover:text-amber-300 transition-colors">
        <input
          type="checkbox"
          className="accent-amber-500 w-4 h-4"
          checked={!!formData.escluso_negozio_ufficiale}
          onChange={(e) => setEscluso(e.target.checked)}
        />
        Escluso Accademia
      </label>
      <label className="flex items-center gap-2 text-xs font-bold cursor-pointer hover:text-red-300 transition-colors">
        <input
          type="checkbox"
          className="accent-red-500 w-4 h-4"
          checked={!!formData.non_vendibile}
          onChange={(e) => setNonVendibile(e.target.checked)}
        />
        Non vendibile (nessun negozio)
      </label>
    </div>
  );
}
