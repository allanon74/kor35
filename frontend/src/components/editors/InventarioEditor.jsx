import React, { useState, useEffect } from 'react';
import {
  staffCreateInventario,
  staffUpdateInventario,
  staffGetInventarioOggetti,
  staffAggiungiOggettoInventario,
  staffRimuoviOggettoInventario,
  staffGetOggettiSenzaPosizione,
  getOggettoDetail,
  staffGetInventarioConsumabili,
  staffAggiungiConsumabileInventario,
  staffRimuoviConsumabileInventario,
  staffCreaOggettoDaInfusioneInventario,
  staffCreaOggettoDaBaseInventario,
  staffGetInfusioni,
  staffGetTessiture,
  staffGetOggettiBase,
} from '../../api';
import RichTextEditor from '../RichTextEditor';
import EditorSaveActions from './EditorSaveActions';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import ConfirmDialog from './ConfirmDialog';
import { staffEditorShellClass, StaffEditorHeader } from '../../staff/StaffToolShell';

const InventarioEditor = ({ onBack, onLogout, initialData = null }) => {
  const [currentId, setCurrentId] = useState(initialData?.id || null);
  const [formData, setFormData] = useState(initialData || {
    nome: '',
    testo: '',
    crediti_deposito_contenuti: '0',
  });
  const [oggettiInventario, setOggettiInventario] = useState([]);
  const [consumabiliInventario, setConsumabiliInventario] = useState([]);
  const [oggettiSenzaPosizione, setOggettiSenzaPosizione] = useState([]);
  const [loadingOggetti, setLoadingOggetti] = useState(false);
  const [loadingSenzaPosizione, setLoadingSenzaPosizione] = useState(false);
  const [saving, setSaving] = useState(false);
  const [manualOggettoId, setManualOggettoId] = useState('');
  const [newConsumabileNome, setNewConsumabileNome] = useState('');
  const [infusioneId, setInfusioneId] = useState('');
  const [oggettoBaseId, setOggettoBaseId] = useState('');
  const [tessituraId, setTessituraId] = useState('');
  const [infusioniOpts, setInfusioniOpts] = useState([]);
  const [tessitureOpts, setTessitureOpts] = useState([]);
  const [oggettiBaseOpts, setOggettiBaseOpts] = useState([]);
  const [status, setStatus] = useState({ type: 'success', message: '' });
  const [pendingRemoveOggettoId, setPendingRemoveOggettoId] = useState(null);

  useEffect(() => {
    if (initialData) {
      setCurrentId(initialData.id || null);
      setFormData({
        nome: initialData.nome || '',
        testo: initialData.testo || '',
        crediti_deposito_contenuti: initialData.crediti_deposito_contenuti ?? '0',
      });
      if (initialData.id) {
        loadOggettiInventario();
        loadConsumabili();
      }
    } else {
      setCurrentId(null);
    }
    loadOggettiSenzaPosizione();
    (async () => {
      try {
        const [inf, tess, base] = await Promise.all([
          staffGetInfusioni(onLogout, { page_size: 500 }).catch(() => []),
          staffGetTessiture(onLogout, { page_size: 500 }).catch(() => []),
          staffGetOggettiBase(onLogout).catch(() => []),
        ]);
        const unwrap = (d) => (Array.isArray(d) ? d : d?.results || []);
        setInfusioniOpts(unwrap(inf));
        setTessitureOpts(unwrap(tess));
        setOggettiBaseOpts(unwrap(base));
      } catch {
        /* ignore catalog load */
      }
    })();
  }, [initialData]);

  const loadOggettiInventario = async () => {
    if (!currentId) return;
    setLoadingOggetti(true);
    try {
      const data = await staffGetInventarioOggetti(currentId, onLogout);
      setOggettiInventario(data || []);
    } catch (error) {
      console.error("Errore caricamento oggetti inventario:", error);
    } finally {
      setLoadingOggetti(false);
    }
  };

  const loadConsumabili = async () => {
    if (!currentId) return;
    try {
      const data = await staffGetInventarioConsumabili(currentId, onLogout);
      setConsumabiliInventario(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Errore caricamento consumabili:', error);
    }
  };

  const loadOggettiSenzaPosizione = async () => {
    setLoadingSenzaPosizione(true);
    try {
      const data = await staffGetOggettiSenzaPosizione(onLogout);
      setOggettiSenzaPosizione(data || []);
    } catch (error) {
      console.error("Errore caricamento oggetti senza posizione:", error);
    } finally {
      setLoadingSenzaPosizione(false);
    }
  };

  const handleSave = async (mode = 'save_close') => {
    try {
      setSaving(true);
      
      const isSaveAsNew = mode === 'save_as_new';
      const isExisting = !!currentId && !isSaveAsNew;
      const saved = isExisting
        ? await staffUpdateInventario(currentId, formData, onLogout)
        : await staffCreateInventario(formData, onLogout);
      const recordName = saved?.nome || formData.nome || 'Record';
      if (mode === 'save_as_new') setStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
      if (mode === 'save_continue') setStatus({ type: 'success', message: `"${recordName}" salvato.` });
      if (mode === 'save_new_blank') {
        setCurrentId(null);
        setFormData({ nome: '', testo: '', crediti_deposito_contenuti: '0' });
        setOggettiInventario([]);
        setConsumabiliInventario([]);
        setStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
      }
      if (mode === 'save_close') onBack();
      if (mode !== 'save_close' && mode !== 'save_new_blank' && saved?.id) {
        setCurrentId(saved.id);
        setFormData((prev) => ({ ...prev, nome: saved.nome ?? prev.nome, testo: saved.testo ?? prev.testo }));
      }
    } catch (e) { 
      console.error(e);
      setStatus({ type: 'error', message: `Errore salvataggio: ${e.message || 'Errore sconosciuto'}` });
    } finally {
      setSaving(false);
    }
  };

  const handleAggiungiOggetto = async (oggettoId) => {
    if (!currentId) {
      setStatus({ type: 'warning', message: "Salva prima l'inventario per aggiungere oggetti." });
      return;
    }
    try {
      await staffAggiungiOggettoInventario(currentId, oggettoId, onLogout);
      await loadOggettiInventario();
      await loadOggettiSenzaPosizione();
      setStatus({ type: 'success', message: "Oggetto aggiunto all'inventario." });
    } catch (error) {
      setStatus({ type: 'error', message: `Errore: ${error.message}` });
    }
  };

  const handleRimuoviOggetto = async (oggettoId) => {
    if (!currentId) return;

    try {
      await staffRimuoviOggettoInventario(currentId, oggettoId, onLogout);
      await loadOggettiInventario();
      await loadOggettiSenzaPosizione();
      setStatus({ type: 'success', message: "Oggetto rimosso dall'inventario." });
    } catch (error) {
      setStatus({ type: 'error', message: `Errore: ${error.message}` });
    }
  };

  const handleAddOggettoManuale = async () => {
    if (!manualOggettoId.trim()) return;
    const id = parseInt(manualOggettoId.trim());
    if (isNaN(id)) {
      setStatus({ type: 'warning', message: 'ID oggetto non valido.' });
      return;
    }

    try {
      const oggetto = await getOggettoDetail(id, onLogout);
      if (oggetto) {
        if (!oggettiSenzaPosizione.find(o => o.id === id)) {
          setOggettiSenzaPosizione(prev => [...prev, oggetto]);
        }
        setManualOggettoId('');
      }
    } catch (error) {
      setStatus({ type: 'error', message: "Impossibile recuperare l'oggetto. Verifica che l'ID sia corretto." });
    }
  };

  return (
    <div className={`${staffEditorShellClass} max-w-7xl`}>
      <StaffEditorHeader
        title={currentId ? `Modifica: ${formData.nome || 'Inventario'}` : 'Nuovo Inventario'}
        titleClassName="text-emerald-400"
        actions={(
          <EditorSaveActions
            onSave={() => handleSave('save_close')}
            onSaveAndContinue={() => handleSave('save_continue')}
            onSaveAsNew={currentId ? () => handleSave('save_as_new') : null}
            onSaveAndNew={() => handleSave('save_new_blank')}
            onCancel={onBack}
            saving={saving}
            saveLabel="Salva"
            statusMessage={status.message}
            statusType={status.type}
          />
        )}
      />

      <div className="grid grid-cols-1 gap-4 bg-gray-900/40 p-4 rounded-xl">
        <div>
          <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Nome</label>
          <input 
            className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm" 
            value={formData.nome} 
            onChange={e => setFormData({...formData, nome: e.target.value})} 
            placeholder="Nome inventario"
          />
        </div>

        <RichTextEditor 
          label="Descrizione" 
          value={formData.testo} 
          onChange={v => setFormData({...formData, testo: v})} 
        />

        <div>
          <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">
            Crediti deposito (prelevabili)
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm"
            value={formData.crediti_deposito_contenuti}
            onChange={(e) => setFormData({ ...formData, crediti_deposito_contenuti: e.target.value })}
            placeholder="0"
          />
          <p className="text-[10px] text-gray-500 mt-1">
            Lascia 0 se non ci sono crediti. Il giocatore li prende sul deposito.
          </p>
        </div>
      </div>

      {/* Gestione Oggetti (solo se inventario esistente) */}
      {currentId && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Oggetti nell'inventario */}
          <div className="bg-gray-900/40 p-4 rounded-xl">
            <h3 className="text-sm font-bold text-gray-300 mb-3">Oggetti nell'Inventario</h3>
            {loadingOggetti ? (
              <div className="text-center p-4 text-gray-500">Caricamento...</div>
            ) : oggettiInventario.length === 0 ? (
              <p className="text-xs text-gray-500 italic">Nessun oggetto</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {oggettiInventario.map(oggetto => (
                  <div key={oggetto.id} className="flex justify-between items-center p-2 bg-gray-800 rounded border border-gray-700">
                    <span className="text-sm text-white">{oggetto.nome}</span>
                    <button
                      onClick={() => setPendingRemoveOggettoId(oggetto.id)}
                      className="p-1 bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded text-xs"
                    >
                      Rimuovi
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Oggetti senza posizione */}
          <div className="bg-gray-900/40 p-4 rounded-xl">
            <h3 className="text-sm font-bold text-gray-300 mb-3">Oggetti Senza Posizione</h3>
            
            {/* Input per aggiungere oggetto manualmente */}
            <div className="mb-2 flex gap-2">
              <input
                type="number"
                value={manualOggettoId}
                onChange={e => setManualOggettoId(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && handleAddOggettoManuale()}
                placeholder="Inserisci ID oggetto..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              />
              <button
                onClick={handleAddOggettoManuale}
                className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white text-sm font-bold"
              >
                +
              </button>
            </div>

            {loadingSenzaPosizione ? (
              <div className="text-center p-4 text-gray-500">Caricamento...</div>
            ) : oggettiSenzaPosizione.length === 0 ? (
              <p className="text-xs text-gray-500 italic">Nessun oggetto senza posizione</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {oggettiSenzaPosizione.map(oggetto => (
                  <div key={oggetto.id} className="flex justify-between items-center p-2 bg-gray-800 rounded border border-gray-700">
                    <span className="text-sm text-white">{oggetto.nome}</span>
                    <button
                      onClick={() => handleAggiungiOggetto(oggetto.id)}
                      className="p-1 bg-green-600/20 text-green-400 hover:bg-green-600/40 rounded text-xs"
                    >
                      Aggiungi
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {currentId && (
        <div className="bg-gray-900/40 p-4 rounded-xl space-y-3">
          <h3 className="text-sm font-bold text-gray-300">Crea istanze (infusione / listino)</h3>
          <p className="text-[10px] text-gray-500">
            Genera un oggetto nell&apos;inventario da infusione (materia/mod/craft) o da oggetto base del listino.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <select
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm min-h-11"
              value={infusioneId}
              onChange={(e) => setInfusioneId(e.target.value)}
            >
              <option value="">— Infusione —</option>
              {infusioniOpts.map((i) => (
                <option key={i.id} value={i.id}>{i.nome}</option>
              ))}
            </select>
            <button
              type="button"
              className="px-3 py-2 bg-violet-700 hover:bg-violet-600 rounded-lg text-white text-sm font-bold min-h-11"
              onClick={async () => {
                if (!infusioneId) return;
                try {
                  const res = await staffCreaOggettoDaInfusioneInventario(currentId, infusioneId, onLogout);
                  await loadOggettiInventario();
                  setStatus({ type: 'success', message: res?.success || 'Istanza da infusione creata.' });
                } catch (e) {
                  setStatus({ type: 'error', message: e.message || 'Errore creazione' });
                }
              }}
            >
              Crea da infusione
            </button>
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <select
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm min-h-11"
              value={oggettoBaseId}
              onChange={(e) => setOggettoBaseId(e.target.value)}
            >
              <option value="">— Oggetto base —</option>
              {oggettiBaseOpts.map((o) => (
                <option key={o.id} value={o.id}>{o.nome}</option>
              ))}
            </select>
            <button
              type="button"
              className="px-3 py-2 bg-indigo-700 hover:bg-indigo-600 rounded-lg text-white text-sm font-bold min-h-11"
              onClick={async () => {
                if (!oggettoBaseId) return;
                try {
                  const res = await staffCreaOggettoDaBaseInventario(currentId, oggettoBaseId, onLogout);
                  await loadOggettiInventario();
                  setStatus({ type: 'success', message: res?.success || 'Istanza da listino creata.' });
                } catch (e) {
                  setStatus({ type: 'error', message: e.message || 'Errore creazione' });
                }
              }}
            >
              Crea da listino
            </button>
          </div>
        </div>
      )}

      {currentId && (
        <div className="bg-gray-900/40 p-4 rounded-xl space-y-3">
          <h3 className="text-sm font-bold text-gray-300">Consumabili nell&apos;inventario</h3>
          <div className="flex flex-col sm:flex-row gap-2">
            <select
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm min-h-11"
              value={tessituraId}
              onChange={(e) => setTessituraId(e.target.value)}
            >
              <option value="">— Da tessitura (opz.) —</option>
              {tessitureOpts.map((t) => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </select>
            <input
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm min-h-11"
              placeholder="Nome consumabile ad hoc"
              value={newConsumabileNome}
              onChange={(e) => setNewConsumabileNome(e.target.value)}
            />
            <button
              type="button"
              className="px-3 py-2 bg-amber-700 hover:bg-amber-600 rounded-lg text-white text-sm font-bold min-h-11"
              onClick={async () => {
                if (!newConsumabileNome.trim() && !tessituraId) return;
                try {
                  await staffAggiungiConsumabileInventario(
                    currentId,
                    {
                      nome: newConsumabileNome.trim() || undefined,
                      tessitura_id: tessituraId || undefined,
                      utilizzi_rimanenti: 1,
                    },
                    onLogout,
                  );
                  setNewConsumabileNome('');
                  setTessituraId('');
                  await loadConsumabili();
                  setStatus({ type: 'success', message: 'Consumabile aggiunto.' });
                } catch (e) {
                  setStatus({ type: 'error', message: e.message || 'Errore consumabile' });
                }
              }}
            >
              Aggiungi
            </button>
          </div>
          {consumabiliInventario.length === 0 ? (
            <p className="text-xs text-gray-500 italic">Nessun consumabile</p>
          ) : (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {consumabiliInventario.map((c) => (
                <div key={c.id} className="flex justify-between items-center p-2 bg-gray-800 rounded border border-gray-700 gap-2">
                  <span className="text-sm text-white min-w-0 break-words">{c.nome} ×{c.utilizzi_rimanenti}</span>
                  <button
                    type="button"
                    className="p-1 bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded text-xs shrink-0"
                    onClick={async () => {
                      try {
                        await staffRimuoviConsumabileInventario(currentId, c.id, onLogout);
                        await loadConsumabili();
                      } catch (e) {
                        setStatus({ type: 'error', message: e.message || 'Errore' });
                      }
                    }}
                  >
                    Rimuovi
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <StaffMinigiocoQrSection qrcodeId={initialData?.qrcode_id} onLogout={onLogout} />

      <ConfirmDialog
        open={pendingRemoveOggettoId !== null}
        title="Rimuovere oggetto dall'inventario?"
        message="L'oggetto verrà spostato tra quelli senza posizione."
        confirmLabel="Rimuovi"
        onCancel={() => setPendingRemoveOggettoId(null)}
        onConfirm={async () => {
          const toRemove = pendingRemoveOggettoId;
          setPendingRemoveOggettoId(null);
          if (toRemove !== null) {
            await handleRimuoviOggetto(toRemove);
          }
        }}
      />
    </div>
  );
};

export default InventarioEditor;
