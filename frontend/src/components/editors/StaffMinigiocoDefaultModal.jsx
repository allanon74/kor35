import React, { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Puzzle, Save, X } from 'lucide-react';
import MinigiocoQrEditor, { emptyMinigiocoConfig } from './MinigiocoQrEditor';
import {
  loadPageMinigiocoSettings,
  savePageMinigiocoSettings,
} from '../../utils/staffMinigiocoDefaults';

/**
 * Editor template minigioco (senza QR): salva in localStorage per pagina staff.
 */
const StaffMinigiocoDefaultModal = ({ pageKey, pageLabel, open, onClose, onLogout }) => {
  const [draftConfig, setDraftConfig] = useState(null);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    if (!open) return;
    const { config } = loadPageMinigiocoSettings(pageKey);
    setDraftConfig(config || emptyMinigiocoConfig());
    setMsg('');
  }, [open, pageKey]);

  const handleSaveTemplate = useCallback(() => {
    if (!draftConfig) {
      setMsg('Nessuna configurazione da salvare.');
      return;
    }
    const current = loadPageMinigiocoSettings(pageKey);
    savePageMinigiocoSettings(pageKey, {
      applyToNew: current.applyToNew,
      config: draftConfig,
    });
    setMsg('Default pagina salvato.');
    setTimeout(onClose, 400);
  }, [draftConfig, pageKey, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[120] flex flex-col bg-black/92">
      <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800 shrink-0 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Puzzle size={18} className="text-indigo-400 shrink-0" />
          <span className="font-bold text-white text-sm truncate">
            Default minigioco — {pageLabel}
          </span>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            type="button"
            onClick={handleSaveTemplate}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded text-sm flex items-center gap-1"
          >
            <Save size={14} />
            Salva default
          </button>
          <button type="button" onClick={onClose} className="px-3 py-2 bg-gray-700 rounded text-sm">
            <X size={14} className="inline" /> Chiudi
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 max-w-2xl mx-auto w-full">
        <p className="text-xs text-gray-400 mb-3">
          Questo modello non è legato a un QR: viene copiato sui nuovi QR se attivi
          «Applica default ai nuovi QR» nella barra della pagina.
        </p>
        <MinigiocoQrEditor
          templateMode
          templateConfig={draftConfig}
          onTemplateChange={setDraftConfig}
          onLogout={onLogout}
        />
        {msg && <p className="text-xs text-center text-amber-300 mt-2">{msg}</p>}
      </div>
    </div>,
    document.body,
  );
};

export default StaffMinigiocoDefaultModal;
