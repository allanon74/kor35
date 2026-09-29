import React, { useState, useEffect, useCallback, memo } from 'react';
import { StaffToolShell, StaffToolSubnav } from '../../staff/StaffToolShell';
import { StaffModalTabs } from '../../staff/StaffCrudUi';
import StaffEditorModal from './StaffEditorModal';
import StaffQrTab from '../StaffQrTab';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import StaffQrBadge from './StaffQrBadge';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import StaffMinigiocoPageToolbar from './StaffMinigiocoPageToolbar';
import StaffMinigiocoUsaDefaultToggle from './StaffMinigiocoUsaDefaultToggle';
import RichTextEditor from '../RichTextEditor';
import useStaffMinigiocoQr from '../../hooks/useStaffMinigiocoQr';
import { useStaffQrAssociation } from '../../hooks/useStaffQrAssociation';
import { useRequisitiAccessoLookup } from '../../hooks/useRequisitiAccessoLookup';
import RequisitiListaEditor, { RequisitiGruppoEditor } from './RequisitiAccessoEditor';
import {
  applyDefaultMinigiocoToQr,
  MINIGIOCO_PAGE_KEYS,
  patchStaffListMinigiocoDefault,
  unwrapStaffList,
} from '../../utils/staffMinigiocoDefaults';
import {
  staffAssociaQrSerieQr,
  staffAssociaQrTrappola,
  staffGetManifesti,
  staffCreateManifesto,
  staffUpdateManifesto,
  staffDeleteManifesto,
  staffGetSerieCollezioni,
  staffCreateSerieCollezione,
  staffUpdateSerieCollezione,
  staffDeleteSerieCollezione,
  staffUploadSerieImmagini,
  staffDeleteSerieImmagine,
  staffGetSerieStato,
  staffResetSerieCollezione,
  staffGetSerieQr,
  staffCreateSerieQr,
  staffGetTrappole,
  staffCreateTrappola,
  staffUpdateTrappola,
  staffDeleteTrappola,
  getEventi,
  resolveMediaUrl,
} from '../../api';

const TABS = [
  { id: 'manifesti', label: 'Manifesti' },
  { id: 'serie', label: 'Serie' },
  { id: 'trappole', label: 'Trappole' },
];

const emptyCondizioni = () => ({ operator: 'AND', requisiti: [] });

const ManifestoManager = ({ onBack, onLogout }) => {
  const { openMinigioco, minigiocoModal } = useStaffMinigiocoQr(onLogout);
  const { lookup, loading: lookupLoading } = useRequisitiAccessoLookup(onLogout);
  const [tab, setTab] = useState('manifesti');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [scanningId, setScanningId] = useState(null);
  const [scanningKind, setScanningKind] = useState('manifesto'); // manifesto | serie | trappola
  const [msg, setMsg] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [modalTab, setModalTab] = useState('dati');
  const [serieEditing, setSerieEditing] = useState(null);
  const [trappolaEditing, setTrappolaEditing] = useState(null);
  const [serieQrEditing, setSerieQrEditing] = useState(null);
  const [seriePendingFiles, setSeriePendingFiles] = useState([]);
  const [serieImgBusy, setSerieImgBusy] = useState(false);

  const [serieList, setSerieList] = useState([]);
  const [serieForm, setSerieForm] = useState({
    id: null,
    nome: '',
    totale: 30,
    descrizione: '',
    ammetti_duplicati: false,
    eventi: [],
    immagini: [],
  });
  const [serieQrList, setSerieQrList] = useState([]);
  const [serieQrForm, setSerieQrForm] = useState({ nome: '', testo: '', serie: '' });
  const [eventiOptions, setEventiOptions] = useState([]);
  const [serieStato, setSerieStato] = useState(null);
  const [serieStatoLoading, setSerieStatoLoading] = useState(false);
  const [confirmResetSerie, setConfirmResetSerie] = useState(null);
  const [trappole, setTrappole] = useState([]);
  const [trappolaForm, setTrappolaForm] = useState({ id: null, nome: '', testo: '', durata_secondi: 60 });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetManifesti(onLogout);
      setItems(unwrapStaffList(data));
    } catch (e) {
      setMsg(e.message || 'Errore caricamento manifesti');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  const loadSerieTrappole = useCallback(async () => {
    try {
      const [serie, sqr, traps, eventi] = await Promise.all([
        staffGetSerieCollezioni(onLogout),
        staffGetSerieQr(onLogout),
        staffGetTrappole(onLogout),
        getEventi(onLogout).catch(() => []),
      ]);
      setSerieList(Array.isArray(serie) ? serie : serie?.results || []);
      setSerieQrList(Array.isArray(sqr) ? sqr : sqr?.results || []);
      setTrappole(Array.isArray(traps) ? traps : traps?.results || []);
      const evList = Array.isArray(eventi) ? eventi : eventi?.results || [];
      setEventiOptions(evList);
    } catch (e) {
      setMsg(e.message || 'Errore caricamento serie/trappole');
    }
  }, [onLogout]);

  const {
    pendingQrConflict,
    conflictLoading,
    handleQrScan,
    confirmConflict,
    cancelConflict,
  } = useStaffQrAssociation({ onLogout, onReload: load });

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (tab === 'serie' || tab === 'trappole') {
      loadSerieTrappole();
    }
  }, [tab, loadSerieTrappole]);

  const manifestoPayload = (editingRow) => {
    const hasNewAudio = editingRow.audio_file instanceof File;
    const hasNewVideo = editingRow.video_file instanceof File;
    const hasNewImmagine = editingRow.immagine_file instanceof File;
    const clearAudio = Boolean(editingRow.clear_audio_file);
    const clearVideo = Boolean(editingRow.clear_video_file);
    const clearImmagine = Boolean(editingRow.clear_immagine_file);
    const useMultipart =
      hasNewAudio || hasNewVideo || hasNewImmagine || clearAudio || clearVideo || clearImmagine;

    if (!useMultipart) {
      return {
        nome: editingRow.nome,
        testo: editingRow.testo || '',
        requisiti_lettura: Array.isArray(editingRow.requisiti_lettura)
          ? editingRow.requisiti_lettura
          : [],
        testo_condizionato: editingRow.testo_condizionato || '',
        condizioni_testo: editingRow.condizioni_testo || emptyCondizioni(),
      };
    }

    const fd = new FormData();
    fd.append('nome', editingRow.nome || '');
    fd.append('testo', editingRow.testo || '');
    fd.append(
      'requisiti_lettura',
      JSON.stringify(
        Array.isArray(editingRow.requisiti_lettura) ? editingRow.requisiti_lettura : [],
      ),
    );
    fd.append('testo_condizionato', editingRow.testo_condizionato || '');
    fd.append(
      'condizioni_testo',
      JSON.stringify(editingRow.condizioni_testo || emptyCondizioni()),
    );
    if (hasNewAudio) fd.append('audio_file', editingRow.audio_file);
    if (hasNewVideo) fd.append('video_file', editingRow.video_file);
    if (hasNewImmagine) fd.append('immagine_file', editingRow.immagine_file);
    if (clearAudio) fd.append('clear_audio_file', 'true');
    if (clearVideo) fd.append('clear_video_file', 'true');
    if (clearImmagine) fd.append('clear_immagine_file', 'true');
    return fd;
  };

  const save = async () => {
    if (!editing?.nome?.trim()) {
      setMsg('Il nome è obbligatorio');
      return;
    }
    try {
      const payload = manifestoPayload(editing);
      if (editing.id) {
        await staffUpdateManifesto(editing.id, payload, onLogout);
      } else {
        await staffCreateManifesto(payload, onLogout);
      }
      setEditing(null);
      setMsg('Salvato.');
      load();
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio');
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Eliminare questo manifesto?')) return;
    try {
      await staffDeleteManifesto(id, onLogout);
      load();
    } catch (e) {
      setMsg(e.message || 'Errore eliminazione');
    }
  };

  const startScan = (avistaId, kind) => {
    setScanningId(avistaId);
    setScanningKind(kind);
  };

  const renderManifesti = () => (
    <>
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Manifesti (QR)</h2>
            <button
              type="button"
              className="px-3 py-2 bg-indigo-600 rounded text-sm"
              onClick={() => {
                setModalTab('dati');
                setEditing({
                  nome: '',
                  testo: '',
                  requisiti_lettura: [],
                  testo_condizionato: '',
                  condizioni_testo: emptyCondizioni(),
                  audio_url: null,
                  video_url: null,
                  immagine_url: null,
                  audio_file: null,
                  video_file: null,
                  immagine_file: null,
                  clear_audio_file: false,
                  clear_video_file: false,
                  clear_immagine_file: false,
                });
              }}
            >
              Nuovo
            </button>
          </div>
          <p className="text-xs text-gray-500">
            I manifesto collegati ai sottosistemi nave (gancio pilota) non compaiono qui:
            gestiscili da Pilotaggio.
          </p>
          <StaffMinigiocoPageToolbar
            pageKey={MINIGIOCO_PAGE_KEYS.manifesti}
            pageLabel="Manifesti"
            onLogout={onLogout}
          />
          {loading ? (
            <p className="text-gray-400">Caricamento…</p>
          ) : (
            <ul className="divide-y divide-gray-700 border border-gray-700 rounded-lg">
              {items.map((m) => (
                <li key={m.id} className="flex justify-between items-center p-3 hover:bg-gray-800/50 gap-2">
                  <div className="flex items-start gap-2 min-w-0 flex-1">
                    <StaffQrBadge hasQr={m.has_qrcode} />
                    <div className="min-w-0">
                      <div className="font-semibold">{m.nome}</div>
                      <div className="text-[10px] text-gray-500">id {m.id}</div>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center justify-end">
                    <StaffMinigiocoUsaDefaultToggle
                      qrcodeId={m.qrcode_id}
                      usaDefault={m.minigioco_usa_default}
                      pageKey={MINIGIOCO_PAGE_KEYS.manifesti}
                      onLogout={onLogout}
                      compact
                      onChange={(val) => patchStaffListMinigiocoDefault(setItems, m.id, val)}
                    />
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-gray-700 rounded"
                      onClick={() => {
                        setModalTab('dati');
                        setEditing({
                          ...m,
                          requisiti_lettura: Array.isArray(m.requisiti_lettura)
                            ? m.requisiti_lettura
                            : [],
                          testo_condizionato: m.testo_condizionato || '',
                          condizioni_testo:
                            m.condizioni_testo && typeof m.condizioni_testo === 'object'
                              ? m.condizioni_testo
                              : emptyCondizioni(),
                          audio_file: null,
                          video_file: null,
                          clear_audio_file: false,
                          clear_video_file: false,
                        });
                      }}
                    >
                      Modifica
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-indigo-800 rounded"
                      onClick={() => openMinigioco(m.qrcode_id, m.nome)}
                      disabled={!m.qrcode_id}
                      title={m.qrcode_id ? 'Configura minigioco QR' : 'Associa prima un QR'}
                    >
                      Minigioco
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-violet-800 rounded"
                      onClick={() => startScan(m.id, 'manifesto')}
                    >
                      Associa QR
                    </button>
                    <button type="button" className="text-xs px-2 py-1 bg-red-900 rounded" onClick={() => remove(m.id)}>
                      Elimina
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

      {editing && (
        <StaffEditorModal
          title={editing.id ? `Manifesto: ${editing.nome || 'senza nome'}` : 'Nuovo manifesto'}
          size="lg"
          onClose={() => setEditing(null)}
          onSave={save}
          saveLabel="Salva"
        >
          <StaffModalTabs
            tabs={[
              { id: 'dati', label: 'Dati manifesto' },
              { id: 'minigioco', label: 'Minigioco' },
            ]}
            active={modalTab}
            onChange={setModalTab}
          />
          {modalTab === 'dati' && (
          <div className="space-y-4">
          <label className="block text-sm">
            Nome
            <input
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
              value={editing.nome}
              onChange={(e) => setEditing({ ...editing, nome: e.target.value })}
            />
          </label>
          <RichTextEditor
            label="Contenuto base"
            value={editing.testo || ''}
            onChange={(testo) => setEditing({ ...editing, testo })}
            minHeight={160}
          />
          <div className="border border-amber-900/40 rounded-lg p-3 space-y-3 bg-amber-950/20">
            <div className="text-xs uppercase text-amber-300 font-semibold">
              Media alla scansione (opzionale)
            </div>
            <p className="text-xs text-gray-400">
              Immagine, audio e/o video mostrati sul telefono dopo la scansione (oltre o al posto del testo).
              Formati consigliati: jpg/png, mp3/m4a e mp4 compresso. Le immagini vengono sottoscalate
              dal server. I file viaggiano con{' '}
              <code className="text-amber-200/80">make sync-media</code>, non nel JSON di sync.
            </p>
            <label className="block text-sm">
              Immagine
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif"
                className="mt-1 block w-full text-sm text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-amber-800 file:text-amber-50"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null;
                  setEditing({
                    ...editing,
                    immagine_file: file,
                    clear_immagine_file: false,
                  });
                }}
              />
            </label>
            {(editing.immagine_url || editing.immagine_file instanceof File) && !editing.clear_immagine_file && (
              <div className="flex items-center justify-between gap-2 text-xs text-amber-100/90 bg-black/20 rounded px-2 py-1.5">
                <div className="flex items-center gap-2 min-w-0">
                  {editing.immagine_file instanceof File ? (
                    <span className="truncate">{editing.immagine_file.name}</span>
                  ) : (
                    <>
                      {editing.immagine_url ? (
                        <img
                          src={resolveMediaUrl(editing.immagine_url)}
                          alt=""
                          className="h-12 w-12 object-cover rounded border border-amber-800/50"
                        />
                      ) : null}
                      <span className="truncate">Immagine già caricata</span>
                    </>
                  )}
                </div>
                <button
                  type="button"
                  className="shrink-0 text-red-300 hover:text-red-200"
                  onClick={() =>
                    setEditing({
                      ...editing,
                      immagine_file: null,
                      clear_immagine_file: true,
                      immagine_url: null,
                    })
                  }
                >
                  Rimuovi
                </button>
              </div>
            )}
            <label className="block text-sm">
              Audio
              <input
                type="file"
                accept="audio/mpeg,audio/mp4,audio/aac,audio/ogg,audio/wav,audio/opus,.mp3,.m4a,.aac,.ogg,.wav,.opus"
                className="mt-1 block w-full text-sm text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-amber-800 file:text-amber-50"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null;
                  setEditing({
                    ...editing,
                    audio_file: file,
                    clear_audio_file: false,
                  });
                }}
              />
            </label>
            {(editing.audio_url || editing.audio_file instanceof File) && !editing.clear_audio_file && (
              <div className="flex items-center justify-between gap-2 text-xs text-amber-100/90 bg-black/20 rounded px-2 py-1.5">
                <span className="truncate">
                  {editing.audio_file instanceof File
                    ? editing.audio_file.name
                    : 'Audio già caricato'}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-red-300 hover:text-red-200"
                  onClick={() =>
                    setEditing({
                      ...editing,
                      audio_file: null,
                      clear_audio_file: true,
                      audio_url: null,
                    })
                  }
                >
                  Rimuovi
                </button>
              </div>
            )}
            <label className="block text-sm">
              Video
              <input
                type="file"
                accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov,.m4v"
                className="mt-1 block w-full text-sm text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-amber-800 file:text-amber-50"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null;
                  setEditing({
                    ...editing,
                    video_file: file,
                    clear_video_file: false,
                  });
                }}
              />
            </label>
            {(editing.video_url || editing.video_file instanceof File) && !editing.clear_video_file && (
              <div className="flex items-center justify-between gap-2 text-xs text-amber-100/90 bg-black/20 rounded px-2 py-1.5">
                <span className="truncate">
                  {editing.video_file instanceof File
                    ? editing.video_file.name
                    : 'Video già caricato'}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-red-300 hover:text-red-200"
                  onClick={() =>
                    setEditing({
                      ...editing,
                      video_file: null,
                      clear_video_file: true,
                      video_url: null,
                    })
                  }
                >
                  Rimuovi
                </button>
              </div>
            )}
          </div>
          <div className="space-y-2">
            <div className="text-xs uppercase text-gray-400 font-semibold">
              Requisiti lettura (gate: senza = tutti leggono)
            </div>
            <RequisitiListaEditor
              requisiti={editing.requisiti_lettura || []}
              onChange={(requisiti_lettura) => setEditing({ ...editing, requisiti_lettura })}
              lookup={lookup}
              lookupLoading={lookupLoading}
            />
          </div>
          <div className="border border-indigo-900/50 rounded-lg p-3 space-y-3 bg-indigo-950/20">
            <div className="text-xs uppercase text-indigo-300 font-semibold">
              Testo condizionale (mostrato in aggiunta se le condizioni sono OK)
            </div>
            <RequisitiGruppoEditor
              value={editing.condizioni_testo || emptyCondizioni()}
              onChange={(condizioni_testo) => setEditing({ ...editing, condizioni_testo })}
              lookup={lookup}
              label="Condizioni AND/OR"
              defaultOperator="AND"
            />
            <RichTextEditor
              label="Contenuto condizionale"
              value={editing.testo_condizionato || ''}
              onChange={(testo_condizionato) => setEditing({ ...editing, testo_condizionato })}
              placeholder="Visibile solo se le condizioni sopra sono soddisfatte"
              minHeight={120}
            />
          </div>
          </div>
          )}
          {modalTab === 'minigioco' && (
            <div>
              {!editing.id || !editing.qrcode_id ? (
                <p className="text-sm text-gray-400">
                  Salva il manifesto e associa un QR dalla lista per configurare il minigioco.
                </p>
              ) : (
                <StaffMinigiocoQrSection qrcodeId={editing.qrcode_id} onLogout={onLogout} />
              )}
            </div>
          )}
        </StaffEditorModal>
      )}
    </>
  );

  const openSerieEditor = (serie = null) => {
    setSeriePendingFiles([]);
    if (serie) {
      setSerieForm({
        id: serie.id,
        nome: serie.nome || '',
        totale: serie.totale || 1,
        descrizione: serie.descrizione || '',
        ammetti_duplicati: Boolean(serie.ammetti_duplicati),
        eventi: Array.isArray(serie.eventi) ? serie.eventi.map((x) => Number(x)) : [],
        immagini: Array.isArray(serie.immagini) ? serie.immagini : [],
      });
    } else {
      setSerieForm({
        id: null,
        nome: '',
        totale: 30,
        descrizione: '',
        ammetti_duplicati: false,
        eventi: [],
        immagini: [],
      });
    }
    setSerieEditing(true);
  };

  const refreshSerieFormFromList = async (serieId) => {
    const serie = await staffGetSerieCollezioni(onLogout);
    const list = Array.isArray(serie) ? serie : serie?.results || [];
    setSerieList(list);
    const updated = list.find((s) => String(s.id) === String(serieId));
    if (updated) {
      setSerieForm((f) => ({
        ...f,
        id: updated.id,
        nome: updated.nome || '',
        totale: updated.totale || 1,
        descrizione: updated.descrizione || '',
        ammetti_duplicati: Boolean(updated.ammetti_duplicati),
        eventi: Array.isArray(updated.eventi) ? updated.eventi.map((x) => Number(x)) : [],
        immagini: Array.isArray(updated.immagini) ? updated.immagini : [],
      }));
    }
    return list;
  };

  const openSerieStato = async (serie) => {
    setSerieStato({ serie_id: serie.id, serie_nome: serie.nome, loading: true });
    setSerieStatoLoading(true);
    try {
      const data = await staffGetSerieStato(serie.id, onLogout);
      setSerieStato(data);
    } catch (e) {
      setMsg(e.message || 'Errore caricamento stato serie');
      setSerieStato(null);
    } finally {
      setSerieStatoLoading(false);
    }
  };

  const renderSerie = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-2">
        <h2 className="text-xl font-bold">Serie (inventario collezione)</h2>
        <button
          type="button"
          className="px-3 py-2 bg-indigo-600 rounded text-sm"
          onClick={() => openSerieEditor(null)}
        >
          Nuova serie
        </button>
      </div>
      <p className="text-sm text-gray-400">
        I pezzi («Nome X di N») vanno nell&apos;inventario serie del PG (non nello zaino).
        Senza «ammetti duplicati» ogni indice esce una sola volta e ogni QR assegna al massimo un pezzo.
        Opzionale: collega uno o più eventi — a evento chiuso i pezzi spariscono dall&apos;inventario serie giocatore.
        Immagini: fino a N; ordine alfabetico se N esatte, altrimenti random con ripetizioni.
      </p>
      <ul className="space-y-2">
        {serieList.map((s) => (
          <li key={s.id} className="flex items-center justify-between bg-gray-800/40 px-3 py-2 rounded text-sm gap-2 flex-wrap">
            <div className="min-w-0 flex-1">
              <div className="font-semibold">{s.nome}</div>
              <div className="text-xs text-gray-400">
                Assegnati {s.pezzi_assegnati}/{s.totale}
                {s.ammetti_duplicati
                  ? ' · duplicati OK'
                  : ` · restano ${s.pezzi_rimanenti ?? 0}`}
                {typeof s.immagini_count === 'number' ? ` · img ${s.immagini_count}` : ''}
                {Array.isArray(s.eventi_dettaglio) && s.eventi_dettaglio.length
                  ? ` · eventi: ${s.eventi_dettaglio.map((e) => e.titolo).join(', ')}`
                  : ''}
              </div>
            </div>
            <button
              type="button"
              className="text-xs px-2 py-1 bg-violet-800 rounded"
              onClick={() => openSerieStato(s)}
            >
              Stato
            </button>
            <button
              type="button"
              className="text-xs px-2 py-1 bg-gray-700 rounded"
              onClick={() => openSerieEditor(s)}
            >
              Modifica
            </button>
            <button
              type="button"
              className="text-amber-300 text-xs"
              onClick={() => setConfirmResetSerie(s)}
            >
              Reset
            </button>
            <button
              type="button"
              className="text-red-400 text-xs"
              onClick={() => setConfirmDelete({ type: 'serie', id: s.id, label: s.nome })}
            >
              Elimina
            </button>
          </li>
        ))}
      </ul>

      <div className="flex justify-between items-center gap-2 mt-4">
        <h3 className="font-bold text-amber-300">QR Serie standalone</h3>
        <button
          type="button"
          className="px-3 py-1.5 bg-indigo-600 rounded text-sm"
          onClick={() => {
            setSerieQrForm({ nome: '', testo: '', serie: '' });
            setSerieQrEditing(true);
          }}
        >
          Nuovo QR serie
        </button>
      </div>
      <ul className="space-y-2">
        {serieQrList.map((row) => (
          <li key={row.id} className="flex items-center gap-2 bg-gray-800/40 px-3 py-2 rounded text-sm">
            <span className="font-semibold flex-1">{row.nome}</span>
            <span className="text-xs text-gray-400">{row.serie_nome}</span>
            <StaffQrBadge hasQr={row.has_qrcode} />
            <button
              type="button"
              className="text-xs px-2 py-1 bg-violet-800 rounded"
              onClick={() => startScan(row.id, 'serie')}
            >
              Associa QR
            </button>
          </li>
        ))}
      </ul>
    </div>
  );

  const renderTrappole = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-2">
        <h2 className="text-xl font-bold">Trappole (QR)</h2>
        <button
          type="button"
          className="px-3 py-2 bg-indigo-600 rounded text-sm"
          onClick={() => {
            setTrappolaForm({ id: null, nome: '', testo: '', durata_secondi: 60 });
            setTrappolaEditing(true);
          }}
        >
          Nuova trappola
        </button>
      </div>
      <p className="text-sm text-gray-400">
        Alla scansione mostra un testo e, se impostata una durata, avvia un timer personale evidente. Usabile anche come effetto nei pool randomici.
      </p>
      <ul className="space-y-2">
        {trappole.map((t) => (
          <li key={t.id} className="flex items-center gap-2 bg-gray-800/40 px-3 py-2 rounded text-sm">
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{t.nome}</div>
              <div className="text-xs text-gray-400">
                {t.durata_secondi ? `Timer ${t.durata_secondi}s` : 'Solo testo'}
              </div>
            </div>
            <StaffQrBadge hasQr={t.has_qrcode} />
            <button
              type="button"
              className="text-xs px-2 py-1 bg-gray-700 rounded"
              onClick={() => {
                setTrappolaForm({
                  id: t.id,
                  nome: t.nome || '',
                  testo: t.testo || '',
                  durata_secondi: t.durata_secondi ?? '',
                });
                setTrappolaEditing(true);
              }}
            >
              Modifica
            </button>
            <button
              type="button"
              className="text-xs px-2 py-1 bg-violet-800 rounded"
              onClick={() => startScan(t.id, 'trappola')}
            >
              Associa QR
            </button>
            <button
              type="button"
              className="text-red-400 text-xs"
              onClick={() => setConfirmDelete({ type: 'trappola', id: t.id, label: t.nome })}
            >
              Elimina
            </button>
          </li>
        ))}
      </ul>
    </div>
  );

  const scanTitle =
    scanningKind === 'serie' ? 'Associa QR a serie' : scanningKind === 'trappola' ? 'Associa QR a trappola' : 'Associa QR a manifesto';

  return (
    <StaffToolShell maxWidth="4xl" className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">QR — Manifesti / Serie / Trappole</h1>
        <StaffToolSubnav
          tabs={TABS}
          active={tab}
          onChange={(id) => {
            setTab(id);
            setEditing(null);
            setMsg('');
          }}
          className="mt-3"
        />
      </div>

      {msg && (
        <div className="text-xs text-amber-200 border border-amber-800/40 rounded px-2 py-1">{msg}</div>
      )}

      {tab === 'manifesti' && renderManifesti()}
      {tab === 'serie' && renderSerie()}
      {tab === 'trappole' && renderTrappole()}

      {serieEditing && (
        <StaffEditorModal
          title={serieForm.id ? `Serie: ${serieForm.nome || 'senza nome'}` : 'Nuova serie'}
          size="lg"
          onClose={() => {
            setSerieEditing(null);
            setSeriePendingFiles([]);
          }}
          onSave={async () => {
            if (!serieForm.nome?.trim()) {
              setMsg('Il nome della serie è obbligatorio');
              return;
            }
            try {
              const payload = {
                nome: serieForm.nome,
                totale: Number(serieForm.totale) || 1,
                descrizione: serieForm.descrizione || '',
                ammetti_duplicati: Boolean(serieForm.ammetti_duplicati),
                eventi: Array.isArray(serieForm.eventi) ? serieForm.eventi : [],
              };
              let serieId = serieForm.id;
              if (serieId) {
                await staffUpdateSerieCollezione(serieId, payload, onLogout);
              } else {
                const created = await staffCreateSerieCollezione(payload, onLogout);
                serieId = created?.id;
              }
              if (serieId && seriePendingFiles.length > 0) {
                const fd = new FormData();
                seriePendingFiles.forEach((file) => fd.append('immagini', file));
                await staffUploadSerieImmagini(serieId, fd, onLogout);
              }
              setSeriePendingFiles([]);
              setSerieEditing(null);
              setMsg(serieForm.id ? 'Serie aggiornata.' : 'Serie creata.');
              await loadSerieTrappole();
            } catch (e) {
              setMsg(e.message || 'Errore salvataggio serie');
            }
          }}
          saveLabel={serieForm.id ? 'Salva' : 'Crea serie'}
        >
          <div className="space-y-3">
            <input
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
              placeholder="Nome serie (es. Pecora)"
              value={serieForm.nome}
              onChange={(e) => setSerieForm((f) => ({ ...f, nome: e.target.value }))}
            />
            <input
              type="number"
              min={1}
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
              placeholder="Totale N"
              value={serieForm.totale}
              onChange={(e) => setSerieForm((f) => ({ ...f, totale: Number(e.target.value) }))}
            />
            <input
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
              placeholder="Descrizione"
              value={serieForm.descrizione}
              onChange={(e) => setSerieForm((f) => ({ ...f, descrizione: e.target.value }))}
            />
            <label className="flex items-start gap-2 text-sm text-gray-200 cursor-pointer">
              <input
                type="checkbox"
                className="mt-1"
                checked={Boolean(serieForm.ammetti_duplicati)}
                onChange={(e) => setSerieForm((f) => ({ ...f, ammetti_duplicati: e.target.checked }))}
              />
              <span>
                Ammetti duplicati
                <span className="block text-xs text-gray-500">
                  Se attivo, lo stesso indice può uscire più volte e lo stesso QR può essere
                  riscosso da personaggi diversi (una volta ciascuno).
                </span>
              </span>
            </label>
            <div>
              <div className="text-xs uppercase text-gray-400 font-semibold mb-1">Eventi (opzionale)</div>
              <select
                multiple
                className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm min-h-[6rem]"
                value={(serieForm.eventi || []).map(String)}
                onChange={(e) => {
                  const selected = Array.from(e.target.selectedOptions).map((o) => Number(o.value));
                  setSerieForm((f) => ({ ...f, eventi: selected }));
                }}
              >
                {eventiOptions.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.titolo}
                    {ev.ended_at ? ' (chiuso)' : ''}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-gray-500 mt-1">
                Ctrl/Cmd+click per selezione multipla. Se colleghi eventi, i pezzi spariscono
                dall&apos;inventario serie giocatore quando tutti gli eventi sono chiusi.
              </p>
            </div>
            <div className="border border-violet-900/40 rounded-lg p-3 space-y-2 bg-violet-950/20">
              <div className="text-xs uppercase text-violet-300 font-semibold">
                Immagini pezzi (opzionale)
              </div>
              <p className="text-xs text-gray-400">
                Massimo {Number(serieForm.totale) || 0} immagini (pari al totale della serie).
                Se ne carichi esattamente N, ogni pezzo riceve un&apos;immagine diversa in ordine
                alfabetico sul nome file; se ne carichi meno, le ripetizioni sono random.
                Le immagini vengono sottoscalate dal server.
              </p>
              {(serieForm.immagini || []).length > 0 && (
                <ul className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {serieForm.immagini.map((img) => (
                    <li key={img.id} className="relative group">
                      <img
                        src={resolveMediaUrl(img.url)}
                        alt={img.nome_file_originale || ''}
                        className="h-20 w-full object-cover rounded border border-violet-800/40"
                      />
                      <div className="text-[10px] text-gray-400 truncate mt-0.5">
                        {img.nome_file_originale || 'img'}
                      </div>
                      {serieForm.id && (
                        <button
                          type="button"
                          disabled={serieImgBusy}
                          className="absolute top-1 right-1 text-[10px] px-1.5 py-0.5 rounded bg-black/70 text-red-300 opacity-90 hover:opacity-100"
                          onClick={async () => {
                            try {
                              setSerieImgBusy(true);
                              await staffDeleteSerieImmagine(serieForm.id, img.id, onLogout);
                              await refreshSerieFormFromList(serieForm.id);
                            } catch (e) {
                              setMsg(e.message || 'Errore eliminazione immagine');
                            } finally {
                              setSerieImgBusy(false);
                            }
                          }}
                        >
                          ✕
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {(() => {
                const remainingSlots = Math.max(
                  0,
                  (Number(serieForm.totale) || 0)
                    - (serieForm.immagini?.length || 0)
                    - seriePendingFiles.length,
                );
                return (
                  <>
                    <label className="block text-sm">
                      Aggiungi immagini
                      <input
                        type="file"
                        multiple
                        accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif"
                        disabled={remainingSlots < 1}
                        className="mt-1 block w-full text-sm text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-violet-800 file:text-violet-50"
                        onChange={(e) => {
                          const picked = Array.from(e.target.files || []);
                          if (!picked.length) return;
                          setSeriePendingFiles((prev) => {
                            const room = Math.max(
                              0,
                              (Number(serieForm.totale) || 0)
                                - (serieForm.immagini?.length || 0)
                                - prev.length,
                            );
                            return [...prev, ...picked.slice(0, room)];
                          });
                          e.target.value = '';
                        }}
                      />
                    </label>
                    {seriePendingFiles.length > 0 && (
                      <div className="text-xs text-violet-100/90 bg-black/20 rounded px-2 py-1.5 space-y-1">
                        <div className="flex justify-between gap-2">
                          <span>{seriePendingFiles.length} file in coda al salvataggio</span>
                          <button
                            type="button"
                            className="text-red-300"
                            onClick={() => setSeriePendingFiles([])}
                          >
                            Svuota coda
                          </button>
                        </div>
                        <ul className="truncate text-gray-400">
                          {seriePendingFiles.map((f) => (
                            <li key={`${f.name}-${f.size}`}>{f.name}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <p className="text-[11px] text-gray-500">
                      Slot liberi: {remainingSlots} / totale {Number(serieForm.totale) || 0}
                      {serieForm.id
                        ? ` · già caricate ${serieForm.immagini?.length || 0}`
                        : ' · salva la serie per caricare'}
                    </p>
                  </>
                );
              })()}
            </div>
          </div>
        </StaffEditorModal>
      )}

      {serieQrEditing && (
        <StaffEditorModal
          title="Nuovo QR serie"
          onClose={() => setSerieQrEditing(null)}
          onSave={async () => {
            try {
              await staffCreateSerieQr(serieQrForm, onLogout);
              setSerieQrForm({ nome: '', testo: '', serie: '' });
              setSerieQrEditing(null);
              setMsg('QR Serie creato.');
              await loadSerieTrappole();
            } catch (e) {
              setMsg(e.message || 'Errore creazione QR Serie');
            }
          }}
          saveLabel="Crea QR"
        >
          <div className="space-y-3">
            <input
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
              placeholder="Nome QR"
              value={serieQrForm.nome}
              onChange={(e) => setSerieQrForm((f) => ({ ...f, nome: e.target.value }))}
            />
            <select
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
              value={serieQrForm.serie}
              onChange={(e) => setSerieQrForm((f) => ({ ...f, serie: e.target.value }))}
            >
              <option value="">Serie…</option>
              {serieList.map((s) => (
                <option key={s.id} value={s.id}>{s.nome}</option>
              ))}
            </select>
          </div>
        </StaffEditorModal>
      )}

      {trappolaEditing && (
        <StaffEditorModal
          title={trappolaForm.id ? `Trappola: ${trappolaForm.nome || 'senza nome'}` : 'Nuova trappola'}
          size="lg"
          onClose={() => setTrappolaEditing(null)}
          onSave={async () => {
            if (!trappolaForm.nome?.trim()) {
              setMsg('Il nome della trappola è obbligatorio');
              return;
            }
            try {
              const payload = {
                nome: trappolaForm.nome,
                testo: trappolaForm.testo || '',
                durata_secondi:
                  trappolaForm.durata_secondi === '' || trappolaForm.durata_secondi == null
                    ? null
                    : Number(trappolaForm.durata_secondi),
              };
              if (trappolaForm.id) {
                await staffUpdateTrappola(trappolaForm.id, payload, onLogout);
                setMsg('Trappola aggiornata.');
              } else {
                await staffCreateTrappola(payload, onLogout);
                setMsg('Trappola creata.');
              }
              setTrappolaForm({ id: null, nome: '', testo: '', durata_secondi: 60 });
              setTrappolaEditing(null);
              await loadSerieTrappole();
            } catch (e) {
              setMsg(e.message || 'Errore salvataggio trappola');
            }
          }}
          saveLabel="Salva"
        >
          <div className="space-y-3">
            <label className="block text-sm">
              Nome
              <input
                className="w-full mt-1 bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
                placeholder="Nome"
                value={trappolaForm.nome}
                onChange={(e) => setTrappolaForm((f) => ({ ...f, nome: e.target.value }))}
              />
            </label>
            <RichTextEditor
              label="Testo"
              value={trappolaForm.testo || ''}
              onChange={(testo) => setTrappolaForm((f) => ({ ...f, testo }))}
              minHeight={140}
            />
            <label className="block text-sm">
              Durata timer (secondi, vuoto = solo testo)
              <input
                type="number"
                min={0}
                className="w-full mt-1 bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
                placeholder="Durata s (vuoto = solo testo)"
                value={trappolaForm.durata_secondi}
                onChange={(e) => setTrappolaForm((f) => ({ ...f, durata_secondi: e.target.value }))}
              />
            </label>
          </div>
        </StaffEditorModal>
      )}

      {scanningId && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">{scanTitle}</span>
            <button type="button" onClick={() => setScanningId(null)} className="px-4 py-2 bg-red-600 rounded">
              Chiudi
            </button>
          </div>
          <div className="flex-1">
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                if (scanningKind === 'manifesto') {
                  const res = await handleQrScan(scanningId, qr_id, {
                    closeScan: () => setScanningId(null),
                    onMessage: setMsg,
                  });
                  if (res?.ok) {
                    await applyDefaultMinigiocoToQr(MINIGIOCO_PAGE_KEYS.manifesti, qr_id, onLogout);
                  }
                } else {
                  try {
                    const assoc =
                      scanningKind === 'serie'
                        ? staffAssociaQrSerieQr
                        : staffAssociaQrTrappola;
                    await assoc(scanningId, qr_id, onLogout);
                    setScanningId(null);
                    setMsg('QR associato.');
                    await loadSerieTrappole();
                  } catch (e) {
                    setMsg(e.message || 'Associazione QR fallita');
                  }
                }
              }}
              onLogout={onLogout}
            />
          </div>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingQrConflict)}
        title="QR già associato"
        message=""
        confirmLabel="Sostituisci associazione"
        confirmTone="warning"
        loading={conflictLoading}
        onCancel={cancelConflict}
        onConfirm={async () => {
          const qrId = pendingQrConflict?.qrId;
          await confirmConflict(setMsg);
          if (qrId) {
            await applyDefaultMinigiocoToQr(MINIGIOCO_PAGE_KEYS.manifesti, qrId, onLogout);
          }
        }}
      >
        {pendingQrConflict?.errorData ? (
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questo manifesto" />
        ) : null}
      </ConfirmDialog>

      <ConfirmDialog
        open={!!confirmDelete}
        title="Conferma eliminazione"
        message={confirmDelete ? `Eliminare «${confirmDelete.label}»?` : ''}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={async () => {
          const c = confirmDelete;
          setConfirmDelete(null);
          if (!c) return;
          try {
            if (c.type === 'serie') {
              await staffDeleteSerieCollezione(c.id, onLogout);
            } else if (c.type === 'trappola') {
              await staffDeleteTrappola(c.id, onLogout);
            }
            await loadSerieTrappole();
            setMsg('Eliminato.');
          } catch (e) {
            setMsg(e.message || 'Eliminazione fallita');
          }
        }}
      />

      <ConfirmDialog
        open={!!confirmResetSerie}
        title="Reset serie"
        message={
          confirmResetSerie
            ? `Sei sicuro di voler resettare la serie «${confirmResetSerie.nome}»? Tutti gli elementi negli inventari verranno rimossi e la consegna ripartirà da zero.`
            : ''
        }
        confirmLabel="Resetta serie"
        confirmTone="danger"
        onCancel={() => setConfirmResetSerie(null)}
        onConfirm={async () => {
          const s = confirmResetSerie;
          setConfirmResetSerie(null);
          if (!s) return;
          try {
            const res = await staffResetSerieCollezione(s.id, onLogout);
            setMsg(res?.messaggio || 'Serie resettata.');
            await loadSerieTrappole();
            if (serieStato?.serie_id === s.id) {
              await openSerieStato(s);
            }
          } catch (e) {
            setMsg(e.message || 'Reset fallito');
          }
        }}
      />

      {(serieStato || serieStatoLoading) && (
        <StaffEditorModal
          title={
            serieStatoLoading
              ? 'Stato serie…'
              : `Stato: ${serieStato?.serie_nome || 'Serie'}`
          }
          size="lg"
          onClose={() => setSerieStato(null)}
          showSave={false}
        >
          {serieStatoLoading || !serieStato || serieStato.loading ? (
            <p className="text-sm text-gray-400">Caricamento…</p>
          ) : (
            <div className="space-y-3 text-sm">
              <p className="text-gray-300">
                Assegnati <strong>{serieStato.pezzi_assegnati}</strong>
                {serieStato.ammetti_duplicati
                  ? ' (duplicati ammessi)'
                  : ` / ${serieStato.totale} · restano ${serieStato.pezzi_rimanenti}`}
              </p>
              {(serieStato.per_personaggio || []).length === 0 ? (
                <p className="text-gray-500 italic">Nessun pezzo in inventario.</p>
              ) : (
                <ul className="space-y-2 max-h-[50vh] overflow-y-auto">
                  {serieStato.per_personaggio.map((pg) => (
                    <li key={pg.personaggio_id} className="bg-gray-800/50 rounded px-3 py-2">
                      <div className="font-semibold text-violet-200">
                        {pg.personaggio_nome || `#${pg.personaggio_id}`}
                        <span className="text-xs text-gray-400 font-normal ml-2">
                          {pg.count} pezz{pg.count === 1 ? 'o' : 'i'}
                        </span>
                      </div>
                      <ul className="mt-1 text-xs text-gray-400 space-y-0.5">
                        {(pg.pezzi || []).map((p) => (
                          <li key={p.id}>
                            {p.etichetta}
                            {p.qr_code_id ? ` · QR ${p.qr_code_id}` : ''}
                          </li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                className="px-3 py-1.5 text-xs rounded bg-amber-800 text-amber-50"
                onClick={() =>
                  setConfirmResetSerie({
                    id: serieStato.serie_id,
                    nome: serieStato.serie_nome,
                  })
                }
              >
                Reset serie…
              </button>
            </div>
          )}
        </StaffEditorModal>
      )}

      {minigiocoModal}
    </StaffToolShell>
  );
};

export default memo(ManifestoManager);
