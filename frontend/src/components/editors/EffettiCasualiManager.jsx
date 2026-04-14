import React, { useState, useEffect, useCallback } from 'react';
import { Tab } from '@headlessui/react';
import { fetchAuthenticated, getPersonaggiList } from '../../api';
import { Loader2, Plus, Pencil, Trash2, X } from 'lucide-react';
import ConfirmDialog from './ConfirmDialog';

const API_BASE = '/api/personaggi/api/staff';
const AURA_TIPO = 'AU'; // tipo Punteggio per Aura

const EffettiCasualiManager = ({ onBack, onLogout }) => {
  const [tipologie, setTipologie] = useState([]);
  const [effetti, setEffetti] = useState([]);
  const [personaggi, setPersonaggi] = useState([]);
  const [aure, setAure] = useState([]);
  const [mattoniMagici, setMattoniMagici] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState('tipologie');
  const [selezionaTipologia, setSelezionaTipologia] = useState(null);
  const [selezionaPersonaggio, setSelezionaPersonaggio] = useState('');
  const [risultato, setRisultato] = useState(null);

  // Form Tipologia
  const [showFormTipologia, setShowFormTipologia] = useState(false);
  const [editTipologiaId, setEditTipologiaId] = useState(null);
  const [formTipologia, setFormTipologia] = useState({ nome: '', tipo: 'OGG', aura_collegata: '' });
  const [savingTipologia, setSavingTipologia] = useState(false);

  // Form Effetto
  const [showFormEffetto, setShowFormEffetto] = useState(false);
  const [editEffettoId, setEditEffettoId] = useState(null);
  const [formEffetto, setFormEffetto] = useState({
    tipologia: '',
    nome: '',
    descrizione: '',
    formula: '',
    elemento_principale: '',
  });
  const [savingEffetto, setSavingEffetto] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [status, setStatus] = useState({ type: '', message: '' });

  const loadTipologie = useCallback(async () => {
    try {
      const data = await fetchAuthenticated(`${API_BASE}/tipologie-effetto/`, { method: 'GET' }, onLogout);
      setTipologie(Array.isArray(data) ? data : data.results || []);
    } catch (e) {
      console.error(e);
      setTipologie([]);
    }
  }, [onLogout]);

  const loadEffetti = useCallback(async () => {
    try {
      const data = await fetchAuthenticated(`${API_BASE}/effetti-casuali/`, { method: 'GET' }, onLogout);
      setEffetti(Array.isArray(data) ? data : data.results || []);
    } catch (e) {
      console.error(e);
      setEffetti([]);
    }
  }, [onLogout]);

  const loadPersonaggi = useCallback(async () => {
    try {
      const data = await getPersonaggiList(onLogout, true);
      setPersonaggi(Array.isArray(data) ? data : []);
    } catch (e) {
      setPersonaggi([]);
    }
  }, [onLogout]);

  const loadAure = useCallback(async () => {
    try {
      const data = await fetchAuthenticated('/api/personaggi/api/punteggio/', { method: 'GET' }, onLogout);
      const list = Array.isArray(data) ? data : data.results || [];
      setAure(list.filter((p) => p.tipo === AURA_TIPO));
    } catch (e) {
      setAure([]);
    }
  }, [onLogout]);

  const loadMattoniMagici = useCallback(async () => {
    try {
      const data = await fetchAuthenticated(`${API_BASE}/mattoni-magici/`, { method: 'GET' }, onLogout);
      setMattoniMagici(Array.isArray(data) ? data : []);
    } catch (e) {
      setMattoniMagici([]);
    }
  }, [onLogout]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([
        loadTipologie(),
        loadEffetti(),
        loadPersonaggi(),
        loadAure(),
        loadMattoniMagici(),
      ]);
      setLoading(false);
    };
    load();
  }, [loadTipologie, loadEffetti, loadPersonaggi, loadAure, loadMattoniMagici]);

  const handleSelezionaEffetto = async () => {
    if (!selezionaTipologia) {
      setStatus({ type: 'warning', message: 'Seleziona una tipologia.' });
      return;
    }
    try {
      const res = await fetchAuthenticated(
        '/api/personaggi/api/staff/seleziona-effetto-casuale/',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tipologia_id: selezionaTipologia,
            personaggio_id: selezionaPersonaggio || null,
          }),
        },
        onLogout
      );
      setRisultato(res);
      setStatus({ type: 'success', message: 'Effetto casuale estratto correttamente.' });
    } catch (e) {
      setStatus({ type: 'error', message: `Errore: ${e.message}` });
    }
  };

  const openNewTipologia = () => {
    setEditTipologiaId(null);
    setFormTipologia({ nome: '', tipo: 'OGG', aura_collegata: '' });
    setShowFormTipologia(true);
  };

  const openEditTipologia = (t) => {
    setEditTipologiaId(t.id);
    setFormTipologia({
      nome: t.nome || '',
      tipo: t.tipo || 'OGG',
      aura_collegata: t.aura_collegata ?? '',
    });
    setShowFormTipologia(true);
  };

  const saveTipologia = async () => {
    if (!formTipologia.nome.trim()) {
      setStatus({ type: 'warning', message: 'Inserisci un nome.' });
      return;
    }
    setSavingTipologia(true);
    try {
      const payload = {
        nome: formTipologia.nome.trim(),
        tipo: formTipologia.tipo,
        aura_collegata: formTipologia.aura_collegata ? parseInt(formTipologia.aura_collegata, 10) : null,
      };
      if (editTipologiaId) {
        await fetchAuthenticated(
          `${API_BASE}/tipologie-effetto/${editTipologiaId}/`,
          { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
          onLogout
        );
      } else {
        await fetchAuthenticated(
          `${API_BASE}/tipologie-effetto/`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
          onLogout
        );
      }
      setShowFormTipologia(false);
      await loadTipologie();
      setStatus({ type: 'success', message: 'Tipologia salvata correttamente.' });
    } catch (e) {
      setStatus({ type: 'error', message: `Errore: ${e.message || 'Salvataggio tipologia'}` });
    } finally {
      setSavingTipologia(false);
    }
  };

  const deleteTipologia = async (t) => {
    try {
      await fetchAuthenticated(
        `${API_BASE}/tipologie-effetto/${t.id}/`,
        { method: 'DELETE' },
        onLogout
      );
      await loadTipologie();
      await loadEffetti();
      setStatus({ type: 'success', message: 'Tipologia eliminata correttamente.' });
    } catch (e) {
      setStatus({ type: 'error', message: `Errore: ${e.message}` });
    }
  };

  const openNewEffetto = () => {
    setEditEffettoId(null);
    setFormEffetto({
      tipologia: tipologie.length ? String(tipologie[0].id) : '',
      nome: '',
      descrizione: '',
      formula: '',
      elemento_principale: '',
    });
    setShowFormEffetto(true);
  };

  const openEditEffetto = (eff) => {
    setEditEffettoId(eff.id);
    const tipId = typeof eff.tipologia === 'object' ? eff.tipologia?.id : eff.tipologia;
    const elemId = typeof eff.elemento_principale === 'object' ? eff.elemento_principale?.id : eff.elemento_principale;
    setFormEffetto({
      tipologia: tipId != null ? String(tipId) : '',
      nome: eff.nome || '',
      descrizione: eff.descrizione || '',
      formula: eff.formula || '',
      elemento_principale: elemId != null ? String(elemId) : '',
    });
    setShowFormEffetto(true);
  };

  const saveEffetto = async () => {
    if (!formEffetto.tipologia || !formEffetto.nome.trim()) {
      setStatus({ type: 'warning', message: 'Inserisci tipologia e nome.' });
      return;
    }
    const tipologia = tipologie.find((x) => x.id === parseInt(formEffetto.tipologia, 10));
    if (tipologia?.tipo === 'TES' && !formEffetto.formula?.trim()) {
      setStatus({ type: 'warning', message: 'Per tipologia Tessitura la formula è obbligatoria.' });
      return;
    }
    setSavingEffetto(true);
    try {
      const payload = {
        tipologia: parseInt(formEffetto.tipologia, 10),
        nome: formEffetto.nome.trim(),
        descrizione: formEffetto.descrizione?.trim() || '',
        formula: formEffetto.formula?.trim() || null,
        elemento_principale: formEffetto.elemento_principale ? parseInt(formEffetto.elemento_principale, 10) : null,
      };
      if (editEffettoId) {
        await fetchAuthenticated(
          `${API_BASE}/effetti-casuali/${editEffettoId}/`,
          { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
          onLogout
        );
      } else {
        await fetchAuthenticated(
          `${API_BASE}/effetti-casuali/`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
          onLogout
        );
      }
      setShowFormEffetto(false);
      await loadEffetti();
      setStatus({ type: 'success', message: 'Effetto salvato correttamente.' });
    } catch (err) {
      const msg = err?.response?.data || err.message;
      setStatus({ type: 'error', message: `Errore: ${typeof msg === 'object' ? JSON.stringify(msg) : msg}` });
    } finally {
      setSavingEffetto(false);
    }
  };

  const deleteEffetto = async (e) => {
    try {
      await fetchAuthenticated(
        `${API_BASE}/effetti-casuali/${e.id}/`,
        { method: 'DELETE' },
        onLogout
      );
      await loadEffetti();
      setStatus({ type: 'success', message: 'Effetto eliminato correttamente.' });
    } catch (err) {
      setStatus({ type: 'error', message: `Errore: ${err.message}` });
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="animate-spin text-indigo-500" size={48} />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <button
        onClick={onBack}
        className="text-gray-400 hover:text-white flex items-center gap-2 mb-4 transition-colors"
      >
        ← Torna agli Strumenti Master
      </button>

      <h2 className="text-xl font-bold text-white">Effetti Casuali</h2>
      {status.message && (
        <div className={`text-xs border rounded-md px-3 py-1 inline-block ${
          status.type === 'error'
            ? 'text-red-200 bg-red-900/20 border-red-700/40'
            : status.type === 'warning'
              ? 'text-amber-200 bg-amber-900/20 border-amber-700/40'
              : 'text-emerald-300 bg-emerald-900/20 border-emerald-700/40'
        }`}>
          {status.message}
        </div>
      )}

      <Tab.Group>
        <Tab.List className="flex gap-2 p-1 bg-gray-800 rounded-lg">
          <Tab className={({ selected }) =>
            `px-4 py-2 rounded-lg font-bold text-sm transition-colors ${selected ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white'}`
          }>
            Tipologie
          </Tab>
          <Tab className={({ selected }) =>
            `px-4 py-2 rounded-lg font-bold text-sm transition-colors ${selected ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white'}`
          }>
            Effetti
          </Tab>
          <Tab className={({ selected }) =>
            `px-4 py-2 rounded-lg font-bold text-sm transition-colors ${selected ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white'}`
          }>
            Seleziona Casuale
          </Tab>
        </Tab.List>

        <Tab.Panels className="mt-4">
          {/* Tab Tipologie */}
          <Tab.Panel>
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
              <div className="flex justify-between items-center mb-4">
                <p className="text-gray-400 text-sm">Gestisci le tipologie (Oggetto / Tessitura).</p>
                <button
                  type="button"
                  onClick={openNewTipologia}
                  className="flex items-center gap-2 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded font-bold text-white text-sm"
                >
                  <Plus size={16} />
                  Nuova tipologia
                </button>
              </div>
              {showFormTipologia && (
                <div className="mb-6 p-4 bg-gray-900 rounded-lg border border-gray-600 space-y-3">
                  <h4 className="font-bold text-white">{editTipologiaId ? 'Modifica tipologia' : 'Nuova tipologia'}</h4>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Nome</label>
                    <input
                      type="text"
                      value={formTipologia.nome}
                      onChange={(e) => setFormTipologia((f) => ({ ...f, nome: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                      placeholder="Es. Pozione Magica"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Tipo</label>
                    <select
                      value={formTipologia.tipo}
                      onChange={(e) => setFormTipologia((f) => ({ ...f, tipo: e.target.value }))}
                      className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                    >
                      <option value="OGG">Oggetto</option>
                      <option value="TES">Tessitura</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Aura collegata (solo per Oggetto, opzionale)</label>
                    <select
                      value={formTipologia.aura_collegata}
                      onChange={(e) => setFormTipologia((f) => ({ ...f, aura_collegata: e.target.value }))}
                      className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                    >
                      <option value="">— Nessuna —</option>
                      {aure.map((a) => (
                        <option key={a.id} value={a.id}>{a.nome}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={saveTipologia}
                      disabled={savingTipologia}
                      className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded font-bold text-white disabled:opacity-50"
                    >
                      {savingTipologia ? <Loader2 className="animate-spin inline" size={18} /> : 'Salva'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowFormTipologia(false)}
                      className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded font-bold text-white flex items-center gap-1"
                    >
                      <X size={16} /> Annulla
                    </button>
                  </div>
                </div>
              )}
              <ul className="space-y-2">
                {tipologie.map((t) => (
                  <li key={t.id} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                    <span className="font-bold text-gray-200">{t.nome}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-400 mr-2">
                      {t.tipo === 'OGG' ? 'Oggetto' : 'Tessitura'}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => openEditTipologia(t)}
                        className="p-2 text-amber-400 hover:bg-amber-900/30 rounded"
                        title="Modifica"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setPendingDelete({
                          title: 'Eliminare tipologia?',
                          message: `Eliminare la tipologia "${t.nome}"? Verranno eliminati anche tutti gli effetti collegati.`,
                          action: () => deleteTipologia(t),
                        })}
                        className="p-2 text-red-400 hover:bg-red-900/30 rounded"
                        title="Elimina"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </li>
                ))}
                {tipologie.length === 0 && !showFormTipologia && <li className="text-gray-500">Nessuna tipologia.</li>}
              </ul>
            </div>
          </Tab.Panel>

          {/* Tab Effetti */}
          <Tab.Panel>
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
              <div className="flex justify-between items-center mb-4">
                <p className="text-gray-400 text-sm">Gestisci gli effetti casuali (nome, descrizione, formula).</p>
                <button
                  type="button"
                  onClick={openNewEffetto}
                  disabled={tipologie.length === 0}
                  className="flex items-center gap-2 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded font-bold text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Plus size={16} />
                  Nuovo effetto
                </button>
              </div>
              {showFormEffetto && (
                <div className="mb-6 p-4 bg-gray-900 rounded-lg border border-gray-600 space-y-3">
                  <h4 className="font-bold text-white">{editEffettoId ? 'Modifica effetto' : 'Nuovo effetto'}</h4>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Tipologia *</label>
                    <select
                      value={formEffetto.tipologia}
                      onChange={(e) => setFormEffetto((f) => ({ ...f, tipologia: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                    >
                      <option value="">— Seleziona —</option>
                      {tipologie.map((t) => (
                        <option key={t.id} value={t.id}>{t.nome} ({t.tipo === 'OGG' ? 'Oggetto' : 'Tessitura'})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Nome *</label>
                    <input
                      type="text"
                      value={formEffetto.nome}
                      onChange={(e) => setFormEffetto((f) => ({ ...f, nome: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                      placeholder="Es. Pozione di Forza"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Descrizione (usa {'{parametro}'} per statistiche)</label>
                    <textarea
                      value={formEffetto.descrizione}
                      onChange={(e) => setFormEffetto((f) => ({ ...f, descrizione: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white min-h-[80px]"
                      placeholder="Testo con placeholder..."
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Formula (obbligatoria se tipologia Tessitura)</label>
                    <textarea
                      value={formEffetto.formula}
                      onChange={(e) => setFormEffetto((f) => ({ ...f, formula: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white min-h-[60px]"
                      placeholder="Formula con placeholder..."
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Elemento principale (Mattoni aura Magica, opzionale)</label>
                    <select
                      value={formEffetto.elemento_principale}
                      onChange={(e) => setFormEffetto((f) => ({ ...f, elemento_principale: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                    >
                      <option value="">— Nessuno —</option>
                      {mattoniMagici.map((m) => (
                        <option key={m.id} value={m.id}>{m.nome}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={saveEffetto}
                      disabled={savingEffetto}
                      className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded font-bold text-white disabled:opacity-50"
                    >
                      {savingEffetto ? <Loader2 className="animate-spin inline" size={18} /> : 'Salva'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowFormEffetto(false)}
                      className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded font-bold text-white flex items-center gap-1"
                    >
                      <X size={16} /> Annulla
                    </button>
                  </div>
                </div>
              )}
              <ul className="space-y-2">
                {effetti.map((e) => (
                  <li key={e.id} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                    <div>
                      <span className="font-bold text-gray-200">{e.nome}</span>
                      <span className="text-xs text-gray-500 ml-2">{e.tipologia?.nome}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => openEditEffetto(e)}
                        className="p-2 text-amber-400 hover:bg-amber-900/30 rounded"
                        title="Modifica"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setPendingDelete({
                          title: 'Eliminare effetto?',
                          message: `Eliminare l'effetto "${e.nome}"?`,
                          action: () => deleteEffetto(e),
                        })}
                        className="p-2 text-red-400 hover:bg-red-900/30 rounded"
                        title="Elimina"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </li>
                ))}
                {effetti.length === 0 && !showFormEffetto && <li className="text-gray-500">Nessun effetto.</li>}
              </ul>
            </div>
          </Tab.Panel>

          <Tab.Panel>
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4 space-y-4">
              <p className="text-gray-400 text-sm">
                Seleziona una tipologia e opzionalmente un personaggio. Se scegli un personaggio, l&apos;effetto verrà applicato (oggetto in inventario o consumabile).
              </p>
              <div className="flex flex-wrap gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Tipologia</label>
                  <select
                    value={selezionaTipologia || ''}
                    onChange={(e) => setSelezionaTipologia(e.target.value ? parseInt(e.target.value, 10) : null)}
                    className="bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="">-- Seleziona --</option>
                    {tipologie.map((t) => (
                      <option key={t.id} value={t.id}>{t.nome} ({t.tipo === 'OGG' ? 'Oggetto' : 'Tessitura'})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Personaggio (opzionale)</label>
                  <select
                    value={selezionaPersonaggio}
                    onChange={(e) => setSelezionaPersonaggio(e.target.value)}
                    className="bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="">-- Nessuno (solo anteprima) --</option>
                    {personaggi.map((p) => (
                      <option key={p.id} value={p.id}>{p.nome}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleSelezionaEffetto}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded font-bold text-white"
                  >
                    Estrai Casuale
                  </button>
                </div>
              </div>
              {risultato && (
                <div className="mt-6 p-4 bg-gray-900 rounded border border-gray-600">
                  <h4 className="font-bold text-amber-400 mb-2">{risultato.nome}</h4>
                  <div className="text-sm text-gray-300 prose prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: risultato.descrizione }} />
                  {risultato.formula && (
                    <div className="mt-2 pt-2 border-t border-gray-700">
                      <span className="text-xs text-gray-500">Formula: </span>
                      <span dangerouslySetInnerHTML={{ __html: risultato.formula }} />
                    </div>
                  )}
                  {(risultato.oggetto_creato_id || risultato.consumabile_creato_id) && (
                    <p className="mt-2 text-green-400 text-sm">
                      ✓ Applicato al personaggio
                      {risultato.oggetto_creato_id && ' (oggetto in inventario)'}
                      {risultato.consumabile_creato_id && ' (consumabile aggiunto)'}
                    </p>
                  )}
                </div>
              )}
            </div>
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title={pendingDelete?.title || 'Conferma eliminazione'}
        message={pendingDelete?.message || ''}
        confirmLabel="Elimina"
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          const action = pendingDelete?.action;
          setPendingDelete(null);
          if (action) await action();
        }}
      />
    </div>
  );
};

export default EffettiCasualiManager;
