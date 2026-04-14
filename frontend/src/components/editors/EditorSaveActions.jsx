import React from 'react';

const EditorSaveActions = ({
  onSave,
  onSaveAndContinue,
  onSaveAsNew,
  onCancel,
  saving = false,
  saveLabel = 'Salva',
}) => {
  return (
    <div className="flex flex-wrap gap-2 justify-end">
      <button
        onClick={onSave}
        disabled={saving}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-2 rounded-lg font-black text-xs uppercase text-white"
      >
        {saving ? 'Salvataggio...' : saveLabel}
      </button>
      {onSaveAndContinue && (
        <button
          onClick={onSaveAndContinue}
          disabled={saving}
          className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-2 rounded-lg font-black text-xs uppercase text-white"
        >
          Salva e continua
        </button>
      )}
      {onSaveAsNew && (
        <button
          onClick={onSaveAsNew}
          disabled={saving}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-2 rounded-lg font-black text-xs uppercase text-white"
        >
          Salva come nuovo
        </button>
      )}
      {onCancel && (
        <button
          onClick={onCancel}
          disabled={saving}
          className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-xs uppercase text-white"
        >
          Annulla
        </button>
      )}
    </div>
  );
};

export default EditorSaveActions;
