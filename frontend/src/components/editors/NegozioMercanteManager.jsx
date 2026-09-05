import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Store, RefreshCw, QrCode, Pencil, Trash2, Package } from 'lucide-react';
import StaffQrTab from '../StaffQrTab';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import { RegoleAperturaEditor, RegoleVisibilitaEditor } from './RequisitiAccessoEditor';
import NegozioConfigEconomiaEditor from './NegozioConfigEconomiaEditor';
import NegozioReadinessBadge from '../NegozioReadinessBadge';
import RichTextEditor from '../RichTextEditor';
import StaffEditorModal from './StaffEditorModal';
import MasterGenericList from './MasterGenericList';
import SearchableSelect from './SearchableSelect';
import {
  StaffToolShell,
  StaffToolHeader,
  staffSecondaryBtnClass,
} from '../../staff/StaffToolShell';
import {
  staffGetNegoziMercante,
  staffCreateNegozioMercante,
  staffUpdateNegozioMercante,
  staffDeleteNegozioMercante,
  staffGetNegozioMercanteVoci,
  staffCreateNegozioMercanteVoce,
  staffUpdateNegozioMercanteVoce,
  staffDeleteNegozioMercanteVoce,
  staffGetNegozioMercanteBundle,
  staffCreateNegozioMercanteBundle,
  staffUpdateNegozioMercanteBundle,
  staffDeleteNegozioMercanteBundle,
  staffAssociaQrNegozioMercante,
  staffScollegaQrNegozioMercante,
  staffGetNegozioMercanteReadiness,
  staffGetNegozioMercanteMovimenti,
  staffGetOggettiBase,
  staffGetOggettiSenzaPosizione,
  staffGetKorps,
  staffGetCarriere,
  staffGetCariche,
  staffGetAbilitaListAll,
  staffGetInfusioni,
  staffGetTessiture,
  staffGetCerimoniali,
} from '../../api';

const TIPO_VOCE_OPTS = [
  { id: 'OGB', nome: 'Oggetto base' },
  { id: 'OGG', nome: 'Oggetto (istanza unica)' },
  { id: 'ABL', nome: 'Abilità' },
  { id: 'INF', nome: 'Infusione (ricetta o istanza)' },
  { id: 'TES', nome: 'Tessitura' },
  { id: 'CER', nome: 'Cerimoniale' },
  { id: 'CON', nome: 'Consumabile' },
];

const TIPO_VOCE_LABEL = Object.fromEntries(TIPO_VOCE_OPTS.map((o) => [o.id, o.nome]));

const MODAL_TABS = [
  { id: 'dati', label: 'Dati negozio' },
  { id: 'catalogo', label: 'Catalogo' },
  { id: 'cassa', label: 'Cassa' },
];

const asList = (data) => (Array.isArray(data) ? data : data?.results || []);

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

const emptyVoceDraft = () => ({
  tipo_voce: 'OGB',
  prezzo_crediti: 100,
  ref_id: '',
  quantita_residua: '',
  consegna_istanza: false,
  consumabile_nome: '',
  consumabile_livello: 1,
  non_vendibile: false,
  attivo: true,
});

const emptyBundleDraft = () => ({
  nome: '',
  descrizione: '',
  prezzo_crediti: 100,
  attivo: true,
  righe: [],
});

const refIdFromVoce = (v) => {
  if (!v) return '';
  const map = {
    OGB: v.oggetto_base,
    OGG: v.oggetto,
    ABL: v.abilita,
    INF: v.infusione,
    TES: v.tessitura,
    CER: v.cerimoniale,
    CON: v.consumabile_tessitura,
  };
  const raw = map[v.tipo_voce];
  if (raw && typeof raw === 'object') return raw.id || '';
  return raw || '';
};

const voceToDraft = (v) => ({
  tipo_voce: v.tipo_voce || 'OGB',
  prezzo_crediti: v.prezzo_crediti ?? 100,
  ref_id: refIdFromVoce(v) ? String(refIdFromVoce(v)) : '',
  quantita_residua: v.quantita_residua == null ? '' : String(v.quantita_residua),
  consegna_istanza: Boolean(v.consegna_istanza) || v.tipo_risultato === 'AUM',
  consumabile_nome: v.consumabile_nome || '',
  consumabile_livello: v.consumabile_livello || 1,
  non_vendibile: Boolean(v.non_vendibile),
  attivo: v.attivo !== false,
});

const bundleToDraft = (b) => ({
  nome: b.nome || '',
  descrizione: b.descrizione || '',
  prezzo_crediti: b.prezzo_crediti ?? 100,
  attivo: b.attivo !== false,
  righe: (b.righe || []).map((r, idx) => ({
    voce: String(r.voce),
    quantita: r.quantita || 1,
    ordine: r.ordine ?? idx,
  })),
});

const NEGOZIO_COLUMNS = [
  {
    header: 'Nome',
    key: 'nome',
    sortable: true,
    filterable: true,
    render: (row) => <span className="font-semibold text-white">{row.nome}</span>,
  },
  {
    header: 'Tipo',
    key: 'tipo_negozio',
    sortable: true,
    render: (row) => (row.tipo_negozio === 'CORP' ? 'Corporativo' : 'QR'),
  },
  {
    header: 'Attivo',
    key: 'attivo',
    sortable: true,
    render: (row) => (
      <span className={row.attivo ? 'text-emerald-400' : 'text-gray-500'}>
        {row.attivo ? 'Sì' : 'No'}
      </span>
    ),
  },
  {
    header: 'Cassa',
    key: 'saldo_crediti',
    sortable: true,
    align: 'right',
    render: (row) => (
      <span className="font-mono text-amber-300">{row.saldo_crediti ?? 0} CR</span>
    ),
  },
  {
    header: 'Voci',
    key: 'voci_count',
    sortable: true,
    getSortValue: (row) => (row.voci || []).length,
    render: (row) => (row.voci || []).length,
  },
  {
    header: 'QR',
    key: 'qr_code',
    render: (row) => (row.qr_code ? `#${row.qr_code}` : '—'),
  },
];

const NEGOZIO_FILTERS = [
  {
    key: 'tipo_negozio',
    label: 'Tipo',
    type: 'button',
    options: [
      { id: 'ALT', label: 'QR' },
      { id: 'CORP', label: 'Corporativo' },
    ],
  },
];

const entityLabel = (tipo, o) => {
  if (!o) return '';
  if (tipo === 'INF') {
    const kind = o.tipo_risultato === 'AUM' ? 'aumento' : 'ricetta';
    return `${o.nome} · ${kind}${o.livello != null ? ` · lv.${o.livello}` : ''}`;
  }
  if (tipo === 'OGG') {
    return `${o.nome}${o.tipo_oggetto ? ` · ${o.tipo_oggetto}` : ''}`;
  }
  return o.nome || String(o.id);
};

const NegozioMercanteManager = ({ onLogout }) => {
  const [negozi, setNegozi] = useState([]);
  const [selected, setSelected] = useState(null);
  const [voci, setVoci] = useState([]);
  const [bundles, setBundles] = useState([]);
  const [form, setForm] = useState(emptyNegozio());
  const [formSnapshot, setFormSnapshot] = useState(null);
  const [voceDraft, setVoceDraft] = useState(emptyVoceDraft());
  const [voceEditingId, setVoceEditingId] = useState(null);
  const [bundleDraft, setBundleDraft] = useState(emptyBundleDraft());
  const [bundleEditingId, setBundleEditingId] = useState(null);
  const [bundlePickVoceId, setBundlePickVoceId] = useState('');
  const [modalTab, setModalTab] = useState('dati');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [voceBusy, setVoceBusy] = useState(false);
  const [bundleBusy, setBundleBusy] = useState(false);
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
    infusioni: [],
    tessiture: [],
    cerimoniali: [],
    oggettiLiberi: [],
  });

  const loadNegozi = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetNegoziMercante(onLogout);
      setNegozi(asList(data));
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
      setVoci(asList(data));
    },
    [onLogout],
  );

  const loadBundles = useCallback(
    async (negozioId) => {
      if (!negozioId) {
        setBundles([]);
        return;
      }
      const data = await staffGetNegozioMercanteBundle(negozioId, onLogout);
      setBundles(asList(data));
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
      staffGetInfusioni(onLogout, { page_size: 500 }),
      staffGetTessiture(onLogout, { page_size: 500 }),
      staffGetCerimoniali(onLogout, { page_size: 500 }),
      staffGetOggettiSenzaPosizione(onLogout),
    ])
      .then(([ogb, korps, carriere, cariche, abilita, inf, tes, cer, ogg]) => {
        setLookup({
          oggettiBase: asList(ogb),
          korps: asList(korps),
          carriere: asList(carriere),
          cariche: asList(cariche),
          abilita: Array.isArray(abilita) ? abilita : [],
          infusioni: asList(inf),
          tessiture: asList(tes),
          cerimoniali: asList(cer),
          oggettiLiberi: asList(ogg),
        });
      })
      .catch(console.error);
  }, [loadNegozi, onLogout]);

  const refreshReadiness = useCallback(
    async (negozioId) => {
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
    },
    [onLogout],
  );

  const openEditor = useCallback(
    async (negozio) => {
      const nextForm = negozio?.id
        ? { ...emptyNegozio(), ...negozio }
        : emptyNegozio();
      setSelected(negozio?.id ? negozio : { id: null });
      setForm(nextForm);
      setFormSnapshot(JSON.stringify(nextForm));
      setModalTab('dati');
      setMsg('');
      setVoceDraft(emptyVoceDraft());
      setVoceEditingId(null);
      setBundleDraft(emptyBundleDraft());
      setBundleEditingId(null);
      setBundlePickVoceId('');
      if (negozio?.id) {
        await Promise.all([
          loadVoci(negozio.id),
          loadBundles(negozio.id),
          refreshReadiness(negozio.id),
        ]);
      } else {
        setVoci([]);
        setBundles([]);
        setReadiness(null);
        setMovimenti([]);
      }
    },
    [loadVoci, loadBundles, refreshReadiness],
  );

  const closeEditor = useCallback(() => {
    setSelected(null);
    setForm(emptyNegozio());
    setFormSnapshot(null);
    setVoci([]);
    setBundles([]);
    setMsg('');
  }, []);

  const isDirty = Boolean(formSnapshot && JSON.stringify(form) !== formSnapshot);

  const saveNegozio = async ({ thenCatalogo = false } = {}) => {
    const payload = {
      ...form,
      saldo_crediti: Number(form.saldo_crediti) || 0,
    };
    setSaving(true);
    try {
      let saved;
      if (selected?.id) {
        saved = await staffUpdateNegozioMercante(selected.id, payload, onLogout);
      } else {
        saved = await staffCreateNegozioMercante(payload, onLogout);
      }
      setMsg('Negozio salvato.');
      await loadNegozi();
      const id = saved?.id || selected?.id;
      if (id) {
        const list = asList(await staffGetNegoziMercante(onLogout));
        const updated = list.find((n) => String(n.id) === String(id)) || { ...saved, id };
        setSelected(updated);
        const snap = { ...emptyNegozio(), ...updated };
        setForm(snap);
        setFormSnapshot(JSON.stringify(snap));
        await Promise.all([loadVoci(id), loadBundles(id), refreshReadiness(id)]);
        if (thenCatalogo || !selected?.id) setModalTab('catalogo');
      }
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio.');
    } finally {
      setSaving(false);
    }
  };

  const deleteNegozio = async (id) => {
    await staffDeleteNegozioMercante(id, onLogout);
    if (selected?.id === id) closeEditor();
    await loadNegozi();
  };

  const pickerOptions = useMemo(() => {
    const source = {
      ABL: lookup.abilita,
      OGB: lookup.oggettiBase,
      INF: lookup.infusioni,
      TES: lookup.tessiture,
      CER: lookup.cerimoniali,
      CON: lookup.tessiture,
      OGG: lookup.oggettiLiberi,
    }[voceDraft.tipo_voce] || [];
    return source.map((o) => ({
      id: o.id,
      nome: entityLabel(voceDraft.tipo_voce, o),
    }));
  }, [lookup, voceDraft.tipo_voce]);

  const selectedInfusione = useMemo(
    () => (lookup.infusioni || []).find((i) => String(i.id) === String(voceDraft.ref_id)),
    [lookup.infusioni, voceDraft.ref_id],
  );

  const buildVocePayload = () => {
    if (!selected?.id) return null;
    const body = {
      negozio: selected.id,
      tipo_voce: voceDraft.tipo_voce,
      prezzo_crediti: Number(voceDraft.prezzo_crediti) || 0,
      attivo: voceDraft.attivo !== false,
      oggetto_base: null,
      oggetto: null,
      abilita: null,
      infusione: null,
      tessitura: null,
      cerimoniale: null,
      consumabile_tessitura: null,
    };
    const refId = voceDraft.ref_id ? String(voceDraft.ref_id).trim() : '';
    if (voceDraft.tipo_voce === 'OGB' && refId) body.oggetto_base = refId;
    if (voceDraft.tipo_voce === 'OGG' && refId) body.oggetto = refId;
    if (voceDraft.tipo_voce === 'ABL' && refId) body.abilita = refId;
    if (voceDraft.tipo_voce === 'INF' && refId) body.infusione = refId;
    if (voceDraft.tipo_voce === 'TES' && refId) body.tessitura = refId;
    if (voceDraft.tipo_voce === 'CER' && refId) body.cerimoniale = refId;
    if (voceDraft.tipo_voce === 'INF') {
      body.consegna_istanza =
        Boolean(voceDraft.consegna_istanza) || selectedInfusione?.tipo_risultato === 'AUM';
    }
    if (voceDraft.tipo_voce === 'CON') {
      if (refId) body.consumabile_tessitura = refId;
      body.consumabile_nome = voceDraft.consumabile_nome || '';
      body.consumabile_livello = Number(voceDraft.consumabile_livello) || 1;
    }
    body.quantita_residua =
      voceDraft.quantita_residua === '' ? null : Number(voceDraft.quantita_residua);
    body.non_vendibile = Boolean(voceDraft.non_vendibile);
    return body;
  };

  const saveVoce = async () => {
    if (!selected?.id) return;
    const body = buildVocePayload();
    if (!body) return;
    if (!voceDraft.ref_id && voceDraft.tipo_voce !== 'CON') {
      setMsg('Seleziona l’articolo da mettere in vendita.');
      return;
    }
    setVoceBusy(true);
    try {
      if (voceEditingId) {
        await staffUpdateNegozioMercanteVoce(voceEditingId, body, onLogout);
        setMsg('Voce aggiornata.');
      } else {
        await staffCreateNegozioMercanteVoce(body, onLogout);
        setMsg('Voce aggiunta. Puoi inserirne un’altra.');
      }
      await loadVoci(selected.id);
      await refreshReadiness(selected.id);
      await loadNegozi();
      setVoceEditingId(null);
      setVoceDraft((d) => ({
        ...emptyVoceDraft(),
        tipo_voce: d.tipo_voce,
        prezzo_crediti: d.prezzo_crediti,
        quantita_residua: d.quantita_residua,
      }));
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio voce.');
    } finally {
      setVoceBusy(false);
    }
  };

  const startEditVoce = (v) => {
    setVoceEditingId(v.id);
    setVoceDraft(voceToDraft(v));
    setMsg('');
  };

  const cancelEditVoce = () => {
    setVoceEditingId(null);
    setVoceDraft(emptyVoceDraft());
  };

  const deleteVoce = async (v) => {
    if (!window.confirm(`Rimuovere «${v.entita_nome || v.id}» dal catalogo?`)) return;
    await staffDeleteNegozioMercanteVoce(v.id, onLogout);
    if (voceEditingId === v.id) cancelEditVoce();
    await loadVoci(selected.id);
    await loadBundles(selected.id);
    await refreshReadiness(selected.id);
    await loadNegozi();
  };

  const addRigaToBundleDraft = () => {
    if (!bundlePickVoceId) return;
    if (bundleDraft.righe.some((r) => String(r.voce) === String(bundlePickVoceId))) {
      setMsg('Questa voce è già nel bundle.');
      return;
    }
    setBundleDraft({
      ...bundleDraft,
      righe: [
        ...bundleDraft.righe,
        { voce: String(bundlePickVoceId), quantita: 1, ordine: bundleDraft.righe.length },
      ],
    });
    setBundlePickVoceId('');
  };

  const saveBundle = async () => {
    if (!selected?.id) return;
    if (!bundleDraft.nome.trim()) {
      setMsg('Indica un nome per il bundle.');
      return;
    }
    if (!bundleDraft.righe.length) {
      setMsg('Aggiungi almeno una voce catalogo al bundle.');
      return;
    }
    const body = {
      negozio: selected.id,
      nome: bundleDraft.nome.trim(),
      descrizione: bundleDraft.descrizione || '',
      prezzo_crediti: Number(bundleDraft.prezzo_crediti) || 0,
      attivo: bundleDraft.attivo !== false,
      righe: bundleDraft.righe.map((r, idx) => ({
        voce: r.voce,
        quantita: Number(r.quantita) || 1,
        ordine: idx,
      })),
    };
    setBundleBusy(true);
    try {
      if (bundleEditingId) {
        await staffUpdateNegozioMercanteBundle(bundleEditingId, body, onLogout);
        setMsg('Bundle aggiornato.');
      } else {
        await staffCreateNegozioMercanteBundle(body, onLogout);
        setMsg('Bundle creato.');
      }
      await loadBundles(selected.id);
      await refreshReadiness(selected.id);
      await loadNegozi();
      setBundleEditingId(null);
      setBundleDraft(emptyBundleDraft());
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio bundle.');
    } finally {
      setBundleBusy(false);
    }
  };

  const startEditBundle = (b) => {
    setBundleEditingId(b.id);
    setBundleDraft(bundleToDraft(b));
    setMsg('');
  };

  const cancelEditBundle = () => {
    setBundleEditingId(null);
    setBundleDraft(emptyBundleDraft());
  };

  const deleteBundle = async (b) => {
    if (!window.confirm(`Eliminare il bundle «${b.nome}»?`)) return;
    await staffDeleteNegozioMercanteBundle(b.id, onLogout);
    if (bundleEditingId === b.id) cancelEditBundle();
    await loadBundles(selected.id);
    await refreshReadiness(selected.id);
    await loadNegozi();
  };

  const voceLabelById = (id) => {
    const v = voci.find((x) => String(x.id) === String(id));
    if (!v) return String(id);
    return `${v.entita_nome || '—'} (${TIPO_VOCE_LABEL[v.tipo_voce] || v.tipo_voce})`;
  };

  const onChangeTipoVoce = (tipo) => {
    setVoceDraft({
      ...voceDraft,
      tipo_voce: tipo,
      ref_id: '',
      consegna_istanza: false,
    });
  };

  const onPickRef = (id) => {
    const next = { ...voceDraft, ref_id: id || '' };
    if (voceDraft.tipo_voce === 'INF') {
      const inf = (lookup.infusioni || []).find((i) => String(i.id) === String(id));
      next.consegna_istanza = inf?.tipo_risultato === 'AUM';
    }
    setVoceDraft(next);
  };

  const handleQrScan = async (qrId, force = false) => {
    if (!selected?.id) return;
    try {
      await staffAssociaQrNegozioMercante(selected.id, qrId, onLogout, force);
      setScanningId(null);
      setPendingQrConflict(null);
      setMsg('QR associato al negozio.');
      const fresh = asList(await staffGetNegoziMercante(onLogout));
      setNegozi(fresh);
      const updated = fresh.find((n) => n.id === selected.id);
      if (updated) {
        setSelected(updated);
        setForm((f) => ({ ...f, qr_code: updated.qr_code }));
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

  const pickerPlaceholder = {
    OGB: 'Cerca oggetto base…',
    OGG: 'Cerca oggetto libero…',
    ABL: 'Cerca abilità…',
    INF: 'Cerca infusione…',
    TES: 'Cerca tessitura…',
    CER: 'Cerca cerimoniale…',
    CON: 'Cerca tessitura del consumabile…',
  }[voceDraft.tipo_voce];

  return (
    <StaffToolShell fill>
      <StaffToolHeader
        icon={<Store size={22} />}
        title="Negozi mercante"
        description="Lista negozi: apri un record per dati e catalogo."
        actions={
          <button type="button" onClick={loadNegozi} className={staffSecondaryBtnClass}>
            <RefreshCw size={16} />
            Aggiorna
          </button>
        }
      />
      <div className="flex-1 min-h-0 overflow-hidden p-4 md:p-6 flex flex-col">
        <MasterGenericList
          items={negozi}
          title="Elenco"
          loading={loading}
          persistKey="negozi-mercante"
          addLabel="Nuovo negozio"
          onAdd={() => openEditor(null)}
          onEdit={openEditor}
          onDelete={deleteNegozio}
          onRowClick={openEditor}
          columns={NEGOZIO_COLUMNS}
          filterConfig={NEGOZIO_FILTERS}
          searchPlaceholder="Cerca negozio…"
          emptyMessage="Nessun negozio. Creane uno per iniziare."
        />
      </div>

      {selected && (
        <StaffEditorModal
          title={selected.id ? `Negozio: ${form.nome || 'senza nome'}` : 'Nuovo negozio'}
          wide
          size="xl"
          saving={saving}
          isDirty={isDirty}
          onClose={closeEditor}
          onSave={() => saveNegozio({ thenCatalogo: !selected.id })}
          saveLabel={selected.id ? 'Salva dati' : 'Crea e vai al catalogo'}
        >
          <div className="flex flex-wrap gap-1 border-b border-gray-800 pb-2 -mt-1">
            {MODAL_TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setModalTab(t.id)}
                className={`px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wide ${
                  modalTab === t.id ? 'bg-amber-700 text-white' : 'bg-gray-800 text-gray-400'
                }`}
              >
                {t.label}
                {t.id === 'catalogo' ? ` (${voci.length})` : ''}
              </button>
            ))}
          </div>
          {msg && <p className="text-sm text-amber-200">{msg}</p>}

          {modalTab === 'dati' && (
            <div className="space-y-3">
              <input
                className="w-full bg-gray-950 border border-gray-600 rounded p-2"
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
                className="w-full bg-gray-950 border border-gray-600 rounded p-2 text-sm"
                placeholder="Note staff (non mostrate ai PG se c'è testo in-game)"
                rows={2}
                value={form.descrizione}
                onChange={(e) => setForm({ ...form, descrizione: e.target.value })}
              />
              <div className="grid sm:grid-cols-2 gap-3">
                <label className="block text-sm">
                  Tipo
                  <select
                    className="w-full mt-1 bg-gray-950 border border-gray-600 rounded p-2"
                    value={form.tipo_negozio}
                    onChange={(e) => setForm({ ...form, tipo_negozio: e.target.value })}
                  >
                    <option value="ALT">Alternativo (QR)</option>
                    <option value="CORP">Corporativo (tab)</option>
                  </select>
                </label>
                <label className="block text-sm">
                  Saldo cassa (CR)
                  <input
                    type="number"
                    className="w-full mt-1 bg-gray-950 border border-gray-600 rounded p-2"
                    value={form.saldo_crediti}
                    onChange={(e) => setForm({ ...form, saldo_crediti: e.target.value })}
                  />
                </label>
              </div>
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.attivo}
                    onChange={(e) => setForm({ ...form, attivo: e.target.checked })}
                  />
                  Attivo
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.incassa_acquisti_catalogo !== false}
                    onChange={(e) =>
                      setForm({ ...form, incassa_acquisti_catalogo: e.target.checked })
                    }
                  />
                  Incassa acquisti catalogo in cassa
                </label>
              </div>

              <NegozioConfigEconomiaEditor
                value={form.config_economia}
                onChange={(config_economia) => setForm({ ...form, config_economia })}
              />

              {selected?.id && readiness && (
                <div className="border border-gray-700 rounded-lg p-2 bg-gray-950/50">
                  <div className="text-xs text-gray-400 uppercase font-semibold mb-1">
                    Checklist prontezza
                  </div>
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
                        setForm((f) => ({ ...f, qr_code: null }));
                        await loadNegozi();
                      }}
                    >
                      Scollega
                    </button>
                  )}
                </div>
              )}

              {form.qr_code && (
                <StaffMinigiocoQrSection
                  qrcodeId={form.qr_code}
                  onLogout={onLogout}
                  lookup={lookup}
                />
              )}
            </div>
          )}

          {modalTab === 'catalogo' && (
            <div className="space-y-3">
              {!selected.id ? (
                <div className="rounded-lg border border-amber-800 bg-amber-950/40 p-4 text-sm text-amber-100">
                  Salva prima i dati del negozio, poi aggiungi gli articoli in vendita.
                  <button
                    type="button"
                    className="mt-3 block px-3 py-1.5 bg-amber-700 rounded font-bold"
                    onClick={() => saveNegozio({ thenCatalogo: true })}
                  >
                    Crea negozio e apri catalogo
                  </button>
                </div>
              ) : (
                <>
                  <div className="rounded-lg border border-gray-700 bg-gray-950/60 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-bold text-gray-200">
                      <Package size={16} className="text-amber-400" />
                      {voceEditingId ? 'Modifica voce' : 'Nuova voce'}
                    </div>
                    <div className="grid sm:grid-cols-2 gap-2 text-sm">
                      <select
                        value={voceDraft.tipo_voce}
                        onChange={(e) => onChangeTipoVoce(e.target.value)}
                        className="bg-gray-900 border border-gray-600 rounded p-2"
                      >
                        {TIPO_VOCE_OPTS.map((o) => (
                          <option key={o.id} value={o.id}>
                            {o.nome}
                          </option>
                        ))}
                      </select>
                      <SearchableSelect
                        options={pickerOptions}
                        value={voceDraft.ref_id || null}
                        onChange={onPickRef}
                        placeholder={pickerPlaceholder}
                        minOptionsForSearch={8}
                      />
                      <input
                        type="number"
                        placeholder="Prezzo CR"
                        className="bg-gray-900 border border-gray-600 rounded p-2"
                        value={voceDraft.prezzo_crediti}
                        onChange={(e) =>
                          setVoceDraft({ ...voceDraft, prezzo_crediti: e.target.value })
                        }
                      />
                      <input
                        placeholder="Quantità (vuoto = illimitata)"
                        className="bg-gray-900 border border-gray-600 rounded p-2"
                        value={voceDraft.quantita_residua}
                        onChange={(e) =>
                          setVoceDraft({ ...voceDraft, quantita_residua: e.target.value })
                        }
                      />
                    </div>
                    {voceDraft.tipo_voce === 'INF' && (
                      <label className="flex items-start gap-2 text-xs text-gray-300">
                        <input
                          type="checkbox"
                          className="mt-0.5"
                          checked={
                            Boolean(voceDraft.consegna_istanza) ||
                            selectedInfusione?.tipo_risultato === 'AUM'
                          }
                          disabled={selectedInfusione?.tipo_risultato === 'AUM'}
                          onChange={(e) =>
                            setVoceDraft({ ...voceDraft, consegna_istanza: e.target.checked })
                          }
                        />
                        <span>
                          Consegna istanza fisica all&apos;acquisto
                          {selectedInfusione?.tipo_risultato === 'AUM'
                            ? ' (obbligatorio: innesto/mutazione da montare).'
                            : ' (Mod/Materia). Se spento, vende la ricetta.'}
                        </span>
                      </label>
                    )}
                    {voceDraft.tipo_voce === 'CON' && (
                      <div className="grid sm:grid-cols-2 gap-2">
                        <input
                          placeholder="Nome consumabile (opz.)"
                          className="bg-gray-900 border border-gray-600 rounded p-2 text-sm"
                          value={voceDraft.consumabile_nome}
                          onChange={(e) =>
                            setVoceDraft({ ...voceDraft, consumabile_nome: e.target.value })
                          }
                        />
                        <input
                          type="number"
                          min={1}
                          placeholder="Livello/utilizzi"
                          className="bg-gray-900 border border-gray-600 rounded p-2 text-sm"
                          value={voceDraft.consumabile_livello}
                          onChange={(e) =>
                            setVoceDraft({ ...voceDraft, consumabile_livello: e.target.value })
                          }
                        />
                      </div>
                    )}
                    <label className="flex items-center gap-2 text-xs text-gray-300">
                      <input
                        type="checkbox"
                        checked={voceDraft.attivo !== false}
                        onChange={(e) =>
                          setVoceDraft({ ...voceDraft, attivo: e.target.checked })
                        }
                      />
                      Voce attiva in listino
                    </label>
                    <label className="flex items-start gap-2 text-xs text-gray-300">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={Boolean(voceDraft.non_vendibile)}
                        onChange={(e) =>
                          setVoceDraft({ ...voceDraft, non_vendibile: e.target.checked })
                        }
                      />
                      <span>
                        Non vendibile come articolo singolo (solo nei bundle)
                      </span>
                    </label>
                    <div className="flex gap-2">
                      {voceEditingId && (
                        <button
                          type="button"
                          className="px-3 py-1.5 bg-gray-700 rounded text-sm"
                          onClick={cancelEditVoce}
                        >
                          Annulla modifica
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={voceBusy}
                        onClick={saveVoce}
                        className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 rounded text-sm font-bold disabled:opacity-50"
                      >
                        {voceEditingId ? 'Salva voce' : 'Aggiungi al catalogo'}
                      </button>
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-700 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-950 text-[10px] uppercase tracking-wider text-gray-500">
                        <tr>
                          <th className="text-left px-3 py-2">Articolo</th>
                          <th className="text-left px-3 py-2">Tipo</th>
                          <th className="text-right px-3 py-2">Prezzo</th>
                          <th className="text-right px-3 py-2">Qty</th>
                          <th className="text-right px-3 py-2 w-24">Azioni</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {voci.map((v) => (
                          <tr
                            key={v.id}
                            className={`bg-gray-900/40 ${
                              voceEditingId === v.id ? 'ring-1 ring-amber-600' : ''
                            }`}
                          >
                            <td className="px-3 py-2 text-white">
                              {v.entita_nome || '—'}
                              {v.attivo === false && (
                                <span className="ml-2 text-[10px] text-gray-500">inattiva</span>
                              )}
                              {v.non_vendibile && (
                                <span className="ml-2 text-[10px] text-violet-400">
                                  solo bundle
                                </span>
                              )}
                            </td>
                            <td className="px-3 py-2 text-gray-400 text-xs">
                              {TIPO_VOCE_LABEL[v.tipo_voce] || v.tipo_voce}
                            </td>
                            <td className="px-3 py-2 text-right font-mono text-amber-300">
                              {v.prezzo_crediti} CR
                            </td>
                            <td className="px-3 py-2 text-right text-gray-400">
                              {v.quantita_residua == null ? '∞' : v.quantita_residua}
                            </td>
                            <td className="px-3 py-2">
                              <div className="flex justify-end gap-1">
                                <button
                                  type="button"
                                  title="Modifica"
                                  className="p-1.5 rounded bg-amber-600/20 text-amber-400 hover:bg-amber-600 hover:text-white"
                                  onClick={() => startEditVoce(v)}
                                >
                                  <Pencil size={14} />
                                </button>
                                <button
                                  type="button"
                                  title="Elimina"
                                  className="p-1.5 rounded bg-red-600/20 text-red-400 hover:bg-red-600 hover:text-white"
                                  onClick={() => deleteVoce(v)}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                        {voci.length === 0 && (
                          <tr>
                            <td colSpan={5} className="px-3 py-6 text-center text-gray-500 text-sm">
                              Nessun articolo. Aggiungine uno dal modulo sopra.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  <div className="rounded-lg border border-violet-900/50 bg-violet-950/20 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-bold text-violet-200">
                      <Package size={16} className="text-violet-400" />
                      {bundleEditingId ? 'Modifica bundle' : 'Nuovo bundle'}
                    </div>
                    <p className="text-[11px] text-gray-400">
                      Le componenti sono voci già in catalogo. Stock e disponibilità
                      seguono le quantità residue delle voci: il bundle si esaurisce
                      quando una componente finisce. «Non vendibile» nasconde la voce
                      dal listino singolo.
                    </p>
                    <div className="grid sm:grid-cols-2 gap-2 text-sm">
                      <input
                        placeholder="Nome bundle"
                        className="bg-gray-900 border border-gray-600 rounded p-2"
                        value={bundleDraft.nome}
                        onChange={(e) =>
                          setBundleDraft({ ...bundleDraft, nome: e.target.value })
                        }
                      />
                      <input
                        type="number"
                        placeholder="Prezzo pacchetto CR"
                        className="bg-gray-900 border border-gray-600 rounded p-2"
                        value={bundleDraft.prezzo_crediti}
                        onChange={(e) =>
                          setBundleDraft({ ...bundleDraft, prezzo_crediti: e.target.value })
                        }
                      />
                      <input
                        placeholder="Descrizione (opz.)"
                        className="bg-gray-900 border border-gray-600 rounded p-2 sm:col-span-2"
                        value={bundleDraft.descrizione}
                        onChange={(e) =>
                          setBundleDraft({ ...bundleDraft, descrizione: e.target.value })
                        }
                      />
                    </div>
                    <div className="flex flex-wrap gap-2 items-end">
                      <div className="flex-1 min-w-[12rem]">
                        <SearchableSelect
                          options={voci.map((v) => ({
                            id: v.id,
                            nome: `${v.entita_nome || '—'} · ${TIPO_VOCE_LABEL[v.tipo_voce] || v.tipo_voce}${
                              v.non_vendibile ? ' · solo bundle' : ''
                            }`,
                          }))}
                          value={bundlePickVoceId || null}
                          onChange={(id) => setBundlePickVoceId(id ? String(id) : '')}
                          placeholder="Aggiungi voce al bundle…"
                          minOptionsForSearch={6}
                        />
                      </div>
                      <button
                        type="button"
                        className="px-3 py-2 bg-violet-800 hover:bg-violet-700 rounded text-sm"
                        onClick={addRigaToBundleDraft}
                      >
                        Aggiungi
                      </button>
                    </div>
                    {bundleDraft.righe.length > 0 && (
                      <ul className="space-y-1 text-xs">
                        {bundleDraft.righe.map((r, idx) => (
                          <li
                            key={`${r.voce}-${idx}`}
                            className="flex items-center gap-2 bg-gray-900/60 rounded px-2 py-1.5"
                          >
                            <span className="flex-1 text-gray-200 truncate">
                              {voceLabelById(r.voce)}
                            </span>
                            <input
                              type="number"
                              min={1}
                              className="w-16 bg-gray-950 border border-gray-600 rounded px-1 py-0.5 text-right"
                              value={r.quantita}
                              onChange={(e) => {
                                const next = [...bundleDraft.righe];
                                next[idx] = {
                                  ...next[idx],
                                  quantita: Number(e.target.value) || 1,
                                };
                                setBundleDraft({ ...bundleDraft, righe: next });
                              }}
                              title="Quantità"
                            />
                            <button
                              type="button"
                              className="text-red-400 hover:text-red-300"
                              onClick={() =>
                                setBundleDraft({
                                  ...bundleDraft,
                                  righe: bundleDraft.righe.filter((_, i) => i !== idx),
                                })
                              }
                            >
                              <Trash2 size={14} />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                    <label className="flex items-center gap-2 text-xs text-gray-300">
                      <input
                        type="checkbox"
                        checked={bundleDraft.attivo !== false}
                        onChange={(e) =>
                          setBundleDraft({ ...bundleDraft, attivo: e.target.checked })
                        }
                      />
                      Bundle attivo
                    </label>
                    <div className="flex gap-2">
                      {bundleEditingId && (
                        <button
                          type="button"
                          className="px-3 py-1.5 bg-gray-700 rounded text-sm"
                          onClick={cancelEditBundle}
                        >
                          Annulla
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={bundleBusy}
                        onClick={saveBundle}
                        className="px-3 py-1.5 bg-violet-700 hover:bg-violet-600 rounded text-sm font-bold disabled:opacity-50"
                      >
                        {bundleEditingId ? 'Salva bundle' : 'Crea bundle'}
                      </button>
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-700 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-950 text-[10px] uppercase tracking-wider text-gray-500">
                        <tr>
                          <th className="text-left px-3 py-2">Bundle</th>
                          <th className="text-left px-3 py-2">Componenti</th>
                          <th className="text-right px-3 py-2">Prezzo</th>
                          <th className="text-right px-3 py-2 w-24">Azioni</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {bundles.map((b) => (
                          <tr
                            key={b.id}
                            className={`bg-gray-900/40 ${
                              bundleEditingId === b.id ? 'ring-1 ring-violet-600' : ''
                            }`}
                          >
                            <td className="px-3 py-2 text-white">
                              {b.nome}
                              {b.attivo === false && (
                                <span className="ml-2 text-[10px] text-gray-500">inattivo</span>
                              )}
                            </td>
                            <td className="px-3 py-2 text-gray-400 text-xs">
                              {(b.righe || [])
                                .map(
                                  (r) =>
                                    `${r.voce_nome || voceLabelById(r.voce)}×${r.quantita || 1}`,
                                )
                                .join(', ') || '—'}
                            </td>
                            <td className="px-3 py-2 text-right font-mono text-violet-300">
                              {b.prezzo_crediti} CR
                            </td>
                            <td className="px-3 py-2">
                              <div className="flex justify-end gap-1">
                                <button
                                  type="button"
                                  title="Modifica"
                                  className="p-1.5 rounded bg-violet-600/20 text-violet-400 hover:bg-violet-600 hover:text-white"
                                  onClick={() => startEditBundle(b)}
                                >
                                  <Pencil size={14} />
                                </button>
                                <button
                                  type="button"
                                  title="Elimina"
                                  className="p-1.5 rounded bg-red-600/20 text-red-400 hover:bg-red-600 hover:text-white"
                                  onClick={() => deleteBundle(b)}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                        {bundles.length === 0 && (
                          <tr>
                            <td colSpan={4} className="px-3 py-6 text-center text-gray-500 text-sm">
                              Nessun bundle. Creane uno dal modulo sopra.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {modalTab === 'cassa' && (
            <div className="space-y-2">
              {!selected.id ? (
                <p className="text-sm text-gray-400">Salva il negozio per vedere i movimenti di cassa.</p>
              ) : movimenti.length === 0 ? (
                <p className="text-sm text-gray-400">Nessun movimento registrato.</p>
              ) : (
                <ul className="text-xs space-y-1">
                  {movimenti.map((m) => (
                    <li
                      key={m.id}
                      className="flex justify-between gap-2 border-b border-gray-800 py-1 text-gray-400"
                    >
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
              )}
            </div>
          )}
        </StaffEditorModal>
      )}

      {scanningId && (
        <div className="fixed inset-0 z-[120] bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR al negozio</span>
            <button
              type="button"
              onClick={() => setScanningId(null)}
              className="px-4 py-2 bg-red-600 rounded"
            >
              Chiudi
            </button>
          </div>
          <div className="flex-1">
            <StaffQrTab onScanSuccess={(qr_id) => handleQrScan(qr_id)} onLogout={onLogout} />
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
    </StaffToolShell>
  );
};

export default NegozioMercanteManager;
