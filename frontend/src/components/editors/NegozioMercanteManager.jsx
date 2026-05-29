import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Store, Plus, RefreshCw, QrCode } from 'lucide-react';
import StaffQrTab from '../StaffQrTab';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import { RegoleAperturaEditor, RegoleVisibilitaEditor } from './RequisitiAccessoEditor';
import NegozioConfigEconomiaEditor from './NegozioConfigEconomiaEditor';
import NegozioReadinessBadge from '../NegozioReadinessBadge';
import RichTextEditor from '../RichTextEditor';
import {
  staffGetNegoziMercante,
  staffCreateNegozioMercante,
  staffUpdateNegozioMercante,
  staffGetNegozioMercanteVoci,
  staffCreateNegozioMercanteVoce,
  staffDeleteNegozioMercanteVoce,
  staffAssociaQrNegozioMercante,
  staffScollegaQrNegozioMercante,
  staffGetNegozioMercanteReadiness,
  staffGetNegozioMercanteMovimenti,
  staffGetOggettiBase,
  staffGetKorps,
  staffGetCarriere,
  staffGetCariche,
  staffGetAbilitaListAll,
} from '../../api';

const TIPO_VOCE_OPTS = [
  { id: 'OGB', nome: 'Oggetto base' },
  { id: 'OGG', nome: 'Oggetto (istanza)' },
  { id: 'ABL', nome: 'Abilità' },
  { id: 'INF', nome: 'Infusione' },
  { id: 'TES', nome: 'Tessitura' },
  { id: 'CER', nome: 'Cerimoniale' },
  { id: 'CON', nome: 'Consumabile' },
];

const emptyNegozio = () => ({
  nome: '',
  descrizione: '',
  tipo_negozio: 'ALT',
  attivo: true,
  saldo_crediti: 0,
  incassa_acquisti_catalogo: true,
  regole_apertura: { modalita: 'sempre_aperto' },
  regole_visibilita: { operator: 'OR', requisiti: [] },
  config_economia: {},
  descrizione_immersiva: '',
});

const NegozioMercanteManager = ({ onLogout }) => {
  const [negozi, setNegozi] = useState([]);
  const [selected, setSelected] = useState(null);
  const [voci, setVoci] = useState([]);
  const [form, setForm] = useState(emptyNegozio());
  const [voceDraft, setVoceDraft] = useState({
    tipo_voce: 'OGB',
    prezzo_crediti: 100,
    ref_id: '',
    quantita_residua: '',
    search: '',
  });
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const [scanningId, setScanningId] = useState(null);
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [movimenti, setMovimenti] = useState([]);
  const [lookup, setLookup] = useState({
    abilita: [],
    korps: [],
    carriere: [],
    cariche: [],
    oggettiBase: [],
  });

  const loadNegozi = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetNegoziMercante(onLogout);
      setNegozi(Array.isArray(data) ? data : data?.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  const loadVoci = useCallback(
    async (negozioId) => {
      if (!negozioId) {
        setVoci([]);
        return;
      }
      const data = await staffGetNegozioMercanteVoci(negozioId, onLogout);
      setVoci(Array.isArray(data) ? data : data?.results || []);
    },
    [onLogout],
  );

  useEffect(() => {
    loadNegozi();
    Promise.all([
      staffGetOggettiBase(onLogout),
      staffGetKorps(onLogout),
      staffGetCarriere(onLogout),
      staffGetCariche(onLogout),
      staffGetAbilitaListAll(onLogout, { pageSize: 500 }),
    ])
      .then(([ogb, korps, carriere, cariche, abilita]) => {
        setLookup({
          oggettiBase: Array.isArray(ogb) ? ogb : ogb?.results || [],
          korps: Array.isArray(korps) ? korps : korps?.results || [],
          carriere: Array.isArray(carriere) ? carriere : carriere?.results || [],
          cariche: Array.isArray(cariche) ? cariche : cariche?.results || [],
          abilita: Array.isArray(abilita) ? abilita : [],
        });
      })
      .catch(console.error);
  }, [loadNegozi, onLogout]);

  const refreshReadiness = useCallback(async (negozioId) => {
    if (!negozioId) {
      setReadiness(null);
      setMovimenti([]);
      return;
    }
    try {
      const [rdy, mov] = await Promise.all([
        staffGetNegozioMercanteReadiness(negozioId, onLogout),
        staffGetNegozioMercanteMovimenti(negozioId, onLogout),
      ]);
      setReadiness(rdy);
      setMovimenti(Array.isArray(mov) ? mov : []);
    } catch {
      setReadiness(null);
      setMovimenti([]);
    }
  }, [onLogout]);

  useEffect(() => {
    if (selected) {
      setForm({ ...emptyNegozio(), ...selected });
      if (selected.id) {
        loadVoci(selected.id);
        refreshReadiness(selected.id);
      } else {
        setVoci([]);
        setReadiness(null);
        setMovimenti([]);
      }
    }
  }, [selected, loadVoci, refreshReadiness]);

  const saveNegozio = async () => {
    const payload = {
      ...form,
      saldo_crediti: Number(form.saldo_crediti) || 0,
    };
    try {
      if (selected?.id) {
        await staffUpdateNegozioMercante(selected.id, payload, onLogout);
      } else {
        await staffCreateNegozioMercante(payload, onLogout);
      }
      setMsg('Negozio salvato.');
      await loadNegozi();
      setSelected(null);
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio.');
    }
  };

  const addVoce = async () => {
    if (!selected?.id) return;
    const body = {
      negozio: selected.id,
      tipo_voce: voceDraft.tipo_voce,
      prezzo_crediti: Number(voceDraft.prezzo_crediti) || 0,
      attivo: true,
    };
    const refId = voceDraft.ref_id?.trim();
    if (voceDraft.tipo_voce === 'OGB' && refId) body.oggetto_base = refId;
    if (voceDraft.tipo_voce === 'OGG' && refId) body.oggetto = refId;
    if (voceDraft.tipo_voce === 'ABL' && refId) body.abilita = refId;
    if (voceDraft.tipo_voce === 'INF' && refId) body.infusione = refId;
    if (voceDraft.tipo_voce === 'TES' && refId) body.tessitura = refId;
    if (voceDraft.tipo_voce === 'CER' && refId) body.cerimoniale = refId;
    if (voceDraft.quantita_residua !== '') {
      body.quantita_residua = Number(voceDraft.quantita_residua);
    }
    await staffCreateNegozioMercanteVoce(body, onLogout);
    await loadVoci(selected.id);
    await refreshReadiness(selected.id);
    setVoceDraft((d) => ({ ...d, ref_id: '', search: '' }));
  };

  const abilitaFiltrate = useMemo(() => {
    if (voceDraft.tipo_voce !== 'ABL') return [];
    const q = (voceDraft.search || '').trim().toLowerCase();
    const list = lookup.abilita || [];
    if (!q) return list.slice(0, 40);
    return list.filter((a) => (a.nome || '').toLowerCase().includes(q)).slice(0, 40);
  }, [lookup.abilita, voceDraft.search, voceDraft.tipo_voce]);

  const oggettiBaseFiltrati = useMemo(() => {
    if (voceDraft.tipo_voce !== 'OGB') return [];
    const q = (voceDraft.search || '').trim().toLowerCase();
    const list = lookup.oggettiBase || [];
    if (!q) return list.slice(0, 40);
    return list
      .filter((o) => (o.nome || '').toLowerCase().includes(q))
      .slice(0, 40);
  }, [lookup.oggettiBase, voceDraft.search, voceDraft.tipo_voce]);

  const handleQrScan = async (qrId, force = false) => {
    if (!selected?.id) return;
    try {
      await staffAssociaQrNegozioMercante(selected.id, qrId, onLogout, force);
      setScanningId(null);
      setPendingQrConflict(null);
      setMsg('QR associato al negozio.');
      await loadNegozi();
      const fresh = (await staffGetNegoziMercante(onLogout)) || [];
      const list = Array.isArray(fresh) ? fresh : fresh.results || [];
      const updated = list.find((n) => n.id === selected.id);
      if (updated) {
        setSelected(updated);
        await refreshReadiness(updated.id);
      }
    } catch (error) {
      if (error.status === 409 && error.data?.already_associated) {
        setPendingQrConflict({ negozioId: selected.id, qrId, errorData: error.data });
        setScanningId(null);
      } else {
        setMsg(error.message || 'Errore associazione QR.');
      }
    }
  };

  return (
    <div className="p-4 text-white max-w-5xl mx-auto space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold text-amber-400 flex items-center gap-2">
          <Store />
          Negozi mercante
        </h1>
        <button type="button" onClick={loadNegozi} className="p-2 rounded bg-gray-700">
          <RefreshCw size={18} />
        </button>
      </div>
      {msg && <p className="text-sm text-amber-200">{msg}</p>}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-3 max-h-[50vh] overflow-y-auto">
          {loading && <p className="text-gray-500 text-sm">Caricamento…</p>}
          {negozi.map((n) => (
            <button
              key={n.id}
              type="button"
              onClick={() => setSelected(n)}
              className={`w-full text-left p-2 rounded mb-1 ${
                selected?.id === n.id ? 'bg-amber-900/50' : 'hover:bg-gray-700'
              }`}
            >
              <div className="font-semibold">{n.nome}</div>
              <div className="text-xs text-gray-400">
                {n.tipo_negozio} · {n.saldo_crediti} CR
                {n.qr_code && ` · QR #${n.qr_code}`}
              </div>
            </button>
          ))}
          <button
            type="button"
            className="mt-2 w-full py-2 border border-dashed border-gray-600 rounded text-sm text-gray-400"
            onClick={() => {
              setSelected({ id: null });
              setForm(emptyNegozio());
              setVoci([]);
            }}
          >
            <Plus className="inline w-4 h-4 mr-1" />
            Nuovo negozio
          </button>
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 space-y-3 max-h-[85vh] overflow-y-auto">
          <input
            className="w-full bg-gray-900 border border-gray-600 rounded p-2"
            placeholder="Nome"
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
          />
          <RichTextEditor
            label="Descrizione in-game (giocatori, scan QR)"
            value={form.descrizione_immersiva || ''}
            onChange={(v) => setForm({ ...form, descrizione_immersiva: v })}
          />
          <textarea
            className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-sm"
            placeholder="Note staff (opzionali, non mostrate ai PG se c'è testo in-game)"
            rows={2}
            value={form.descrizione}
            onChange={(e) => setForm({ ...form, descrizione: e.target.value })}
          />
          <select
            className="w-full bg-gray-900 border border-gray-600 rounded p-2"
            value={form.tipo_negozio}
            onChange={(e) => setForm({ ...form, tipo_negozio: e.target.value })}
          >
            <option value="ALT">Alternativo (QR)</option>
            <option value="CORP">Corporativo (tab)</option>
          </select>
          <label className="block text-sm">
            Saldo cassa (CR)
            <input
              type="number"
              className="w-full mt-1 bg-gray-900 border border-gray-600 rounded p-2"
              value={form.saldo_crediti}
              onChange={(e) => setForm({ ...form, saldo_crediti: e.target.value })}
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.attivo}
              onChange={(e) => setForm({ ...form, attivo: e.target.checked })}
            />
            Attivo
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.incassa_acquisti_catalogo !== false}
              onChange={(e) => setForm({ ...form, incassa_acquisti_catalogo: e.target.checked })}
            />
            Incassa acquisti catalogo in cassa
          </label>

          <NegozioConfigEconomiaEditor
            value={form.config_economia}
            onChange={(config_economia) => setForm({ ...form, config_economia })}
          />

          {selected?.id && readiness && (
            <div className="border border-gray-700 rounded-lg p-2 bg-gray-900/50">
              <div className="text-xs text-gray-400 uppercase font-semibold mb-1">Checklist prontezza</div>
              <NegozioReadinessBadge readiness={readiness} />
            </div>
          )}

          {form.tipo_negozio === 'ALT' ? (
            <RegoleAperturaEditor
              value={form.regole_apertura}
              onChange={(regole_apertura) => setForm({ ...form, regole_apertura })}
              lookup={lookup}
            />
          ) : (
            <RegoleVisibilitaEditor
              value={form.regole_visibilita}
              onChange={(regole_visibilita) => setForm({ ...form, regole_visibilita })}
              lookup={lookup}
            />
          )}

          {selected?.id && form.tipo_negozio === 'ALT' && (
            <div className="flex flex-wrap gap-2 items-center text-sm border-t border-gray-700 pt-3">
              <span className="text-gray-400">
                QR: {form.qr_code ? `#${form.qr_code}` : 'non collegato'}
              </span>
              <button
                type="button"
                className="px-3 py-1.5 bg-indigo-700 rounded flex items-center gap-1"
                onClick={() => setScanningId(selected.id)}
              >
                <QrCode size={16} />
                Scansiona QR
              </button>
              {form.qr_code && (
                <button
                  type="button"
                  className="px-3 py-1.5 bg-gray-700 rounded"
                  onClick={async () => {
                    await staffScollegaQrNegozioMercante(selected.id, onLogout);
                    setMsg('QR scollegato.');
                    await loadNegozi();
                  }}
                >
                  Scollega
                </button>
              )}
            </div>
          )}

          <button type="button" onClick={saveNegozio} className="w-full py-2 bg-amber-700 rounded font-bold">
            Salva negozio
          </button>

          {selected?.id && (
            <>
              <hr className="border-gray-600" />
              <h3 className="font-bold text-sm text-gray-300">Voci catalogo</h3>
              <ul className="text-xs space-y-1 max-h-32 overflow-y-auto">
                {voci.map((v) => (
                  <li key={v.id} className="flex justify-between gap-2 bg-gray-900/50 p-1 rounded">
                    <span>
                      {v.tipo_voce} — {v.entita_nome || v.id} — {v.prezzo_crediti} CR
                    </span>
                    <button
                      type="button"
                      className="text-red-400"
                      onClick={async () => {
                        await staffDeleteNegozioMercanteVoce(v.id, onLogout);
                        loadVoci(selected.id);
                      }}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <select
                  value={voceDraft.tipo_voce}
                  onChange={(e) => setVoceDraft({ ...voceDraft, tipo_voce: e.target.value })}
                  className="bg-gray-900 border border-gray-600 rounded p-1"
                >
                  {TIPO_VOCE_OPTS.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.nome}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  placeholder="Prezzo CR"
                  className="bg-gray-900 border border-gray-600 rounded p-1"
                  value={voceDraft.prezzo_crediti}
                  onChange={(e) =>
                    setVoceDraft({ ...voceDraft, prezzo_crediti: e.target.value })
                  }
                />
                {voceDraft.tipo_voce === 'OGB' || voceDraft.tipo_voce === 'ABL' ? (
                  <div className="col-span-2 space-y-1">
                    <input
                      placeholder={voceDraft.tipo_voce === 'OGB' ? 'Cerca oggetto base…' : 'Cerca abilità…'}
                      className="w-full bg-gray-900 border border-gray-600 rounded p-1"
                      value={voceDraft.search}
                      onChange={(e) => setVoceDraft({ ...voceDraft, search: e.target.value })}
                    />
                    <select
                      className="w-full bg-gray-900 border border-gray-600 rounded p-1 text-xs"
                      value={voceDraft.ref_id}
                      onChange={(e) => setVoceDraft({ ...voceDraft, ref_id: e.target.value })}
                    >
                      <option value="">— seleziona —</option>
                      {(voceDraft.tipo_voce === 'OGB' ? oggettiBaseFiltrati : abilitaFiltrate).map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.nome}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <input
                    placeholder="UUID entità"
                    className="col-span-2 bg-gray-900 border border-gray-600 rounded p-1"
                    value={voceDraft.ref_id || ''}
                    onChange={(e) => setVoceDraft({ ...voceDraft, ref_id: e.target.value })}
                  />
                )}
                <input
                  placeholder="Quantità (vuoto=∞)"
                  className="col-span-2 bg-gray-900 border border-gray-600 rounded p-1"
                  value={voceDraft.quantita_residua}
                  onChange={(e) =>
                    setVoceDraft({ ...voceDraft, quantita_residua: e.target.value })
                  }
                />
              </div>
              <button type="button" onClick={addVoce} className="w-full py-1.5 bg-gray-700 rounded text-sm">
                Aggiungi voce
              </button>

              {movimenti.length > 0 && (
                <>
                  <h3 className="font-bold text-sm text-gray-300 mt-2">Ultimi movimenti cassa</h3>
                  <ul className="text-[10px] max-h-28 overflow-y-auto space-y-0.5 text-gray-400">
                    {movimenti.map((m) => (
                      <li key={m.id} className="flex justify-between gap-2 border-b border-gray-800/50 py-0.5">
                        <span>
                          {m.tipo} {m.personaggio ? `· ${m.personaggio}` : ''}
                        </span>
                        <span className="font-mono text-amber-400/90">
                          {m.importo > 0 ? '+' : ''}
                          {m.importo} → {m.saldo_dopo}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {scanningId && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR al negozio</span>
            <button type="button" onClick={() => setScanningId(null)} className="px-4 py-2 bg-red-600 rounded">
              Chiudi
            </button>
          </div>
          <div className="flex-1">
            <StaffQrTab
              onScanSuccess={(qr_id) => handleQrScan(qr_id)}
              onLogout={onLogout}
            />
          </div>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingQrConflict)}
        title="QR già associato"
        message=""
        confirmLabel="Conferma collegamento"
        confirmTone="warning"
        onCancel={() => setPendingQrConflict(null)}
        onConfirm={() => {
          const p = pendingQrConflict;
          if (p?.qrId) handleQrScan(p.qrId, true);
        }}
      >
        {pendingQrConflict?.errorData ? (
          <QrAssociationConflictBody
            errorData={pendingQrConflict.errorData}
            targetHint="questo negozio"
          />
        ) : null}
      </ConfirmDialog>
    </div>
  );
};

export default NegozioMercanteManager;
