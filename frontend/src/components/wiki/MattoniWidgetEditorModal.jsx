import React, { useEffect, useMemo, useState } from 'react';
import { getWikiMattoniWidget, getWikiPunteggi } from '../../api';

function normalizeIds(v) {
  if (!Array.isArray(v)) return [];
  return v.map(x => (typeof x === 'object' ? x?.id : x)).filter(Boolean);
}

export default function MattoniWidgetEditorModal({ onClose, onSave, initialData = null }) {
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState(initialData?.title || '');
  const [filterType, setFilterType] = useState(initialData?.filter_type || 'all');
  const [aure, setAure] = useState([]);
  const [caratteristiche, setCaratteristiche] = useState([]);
  const [selectedAure, setSelectedAure] = useState(normalizeIds(initialData?.aure));
  const [selectedCar, setSelectedCar] = useState(normalizeIds(initialData?.caratteristiche));

  useEffect(() => {
    getWikiPunteggi('AU')
      .then(setAure)
      .catch(err => console.error('Errore caricamento aure:', err));
    getWikiPunteggi('CA')
      .then(setCaratteristiche)
      .catch(err => console.error('Errore caricamento caratteristiche:', err));
  }, []);

  useEffect(() => {
    if (initialData?.id && (!initialData?.aure || !initialData?.caratteristiche)) {
      getWikiMattoniWidget(initialData.id)
        .then(w => {
          setTitle(w.title || '');
          setFilterType(w.filter_type || 'all');
          setSelectedAure(normalizeIds(w.aure));
          setSelectedCar(normalizeIds(w.caratteristiche));
        })
        .catch(err => console.error('Errore caricamento widget mattoni:', err));
    }
  }, [initialData?.id]);

  const sortedAure = useMemo(
    () => [...(aure || [])].sort((a, b) => (a.nome || '').localeCompare(b.nome || '')),
    [aure]
  );
  const sortedCar = useMemo(
    () => [...(caratteristiche || [])].sort((a, b) => (a.nome || '').localeCompare(b.nome || '')),
    [caratteristiche]
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        title: title || '',
        filter_type: filterType || 'all',
        aure_ids: (filterType === 'aura' ? selectedAure : []),
        caratteristiche_ids: (filterType === 'caratteristica' ? selectedCar : []),
      };
      await onSave(payload, initialData?.id);
      onClose();
    } catch (err) {
      console.error('Errore salvataggio widget mattoni:', err);
      alert(err?.message || 'Errore durante il salvataggio.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-60 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="font-bold text-lg text-gray-800">
            {initialData?.id ? 'Modifica Widget Mattoni' : 'Nuovo Widget Mattoni'}
          </h3>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-red-600 font-bold text-xl px-1">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Titolo (opzionale)</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full border border-gray-300 px-2 py-1.5 rounded text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              placeholder="Es. Mattoni - Aura Fuoco"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Filtro</label>
            <select
              value={filterType}
              onChange={e => setFilterType(e.target.value)}
              className="w-full border border-gray-300 p-2 rounded text-sm"
            >
              <option value="all">Mostra tutti</option>
              <option value="aura">Filtra per Aura</option>
              <option value="caratteristica">Filtra per Caratteristica</option>
            </select>
            <p className="text-[11px] text-gray-500 mt-1">Se non selezioni nulla, verranno mostrati tutti i mattoni.</p>
          </div>

          {filterType === 'aura' && (
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Aure incluse</label>
              <select
                multiple
                value={selectedAure.map(String)}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions).map(o => Number(o.value));
                  setSelectedAure(values);
                }}
                className="w-full border border-gray-300 p-2 rounded text-sm h-40"
              >
                {sortedAure.map(a => (
                  <option key={a.id} value={a.id}>{a.nome}</option>
                ))}
              </select>
            </div>
          )}

          {filterType === 'caratteristica' && (
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Caratteristiche incluse</label>
              <select
                multiple
                value={selectedCar.map(String)}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions).map(o => Number(o.value));
                  setSelectedCar(values);
                }}
                className="w-full border border-gray-300 p-2 rounded text-sm h-40"
              >
                {sortedCar.map(c => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-3 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded">
              Annulla
            </button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-indigo-600 text-white font-bold rounded hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Salvataggio...' : (initialData?.id ? 'Salva modifiche' : 'Crea widget')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

