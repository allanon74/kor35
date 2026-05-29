import React, { useCallback, useEffect, useState, memo } from 'react';
import { ArrowLeft, BookOpen, Download, RefreshCw, Save, Eye, AlertTriangle, History, Package } from 'lucide-react';
import {
  getStaffManualePdfList,
  createStaffManualePdf,
  updateStaffManualePdf,
  generateStaffManualePdf,
  getWikiManualeLatestPdfUrl,
  getStaffManualePdfAnteprimaUrl,
  getStaffManualePdfExportZipUrl,
  getWikiPdfDiagnostica,
  getWikiManualeStorico,
  startWikiManualeBatchJob,
  getWikiManualeBatchJob,
} from '../../api';
import {
  MANUALE_PDF_PRESET_OPTIONS,
  MANUALE_PDF_OVERRIDE_FIELDS,
  emptyStileOverride,
} from '../../staff/manualePdfStylePresets';

const emptyForm = {
  slug: '',
  titolo: '',
  sottotitolo: '',
  ordine: 0,
  attivo: true,
  stile_preset: 'giocatore',
};

const ManualePdfManager = ({ onBack, onLogout }) => {
  const [manuali, setManuali] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSlug, setSelectedSlug] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [stileOverride, setStileOverride] = useState(emptyStileOverride);
  const [copertinaFile, setCopertinaFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [generatingSlug, setGeneratingSlug] = useState(null);
  const [message, setMessage] = useState('');
  const [diagnostica, setDiagnostica] = useState(null);
  const [storico, setStorico] = useState([]);
  const [batchJob, setBatchJob] = useState(null);
  const [batchPolling, setBatchPolling] = useState(false);

  const loadManuali = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getStaffManualePdfList(onLogout);
      setManuali(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
      setMessage('Errore caricamento manuali PDF.');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadManuali();
  }, [loadManuali]);

  const loadDiagnostica = useCallback(async () => {
    try {
      const data = await getWikiPdfDiagnostica(onLogout);
      setDiagnostica(data);
    } catch (e) {
      console.error(e);
    }
  }, [onLogout]);

  useEffect(() => {
    loadDiagnostica();
  }, [loadDiagnostica]);

  const loadStorico = useCallback(async (slug) => {
    if (!slug) {
      setStorico([]);
      return;
    }
    try {
      const data = await getWikiManualeStorico(slug, onLogout);
      setStorico(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
      setStorico([]);
    }
  }, [onLogout]);

  const selected = manuali.find((m) => m.slug === selectedSlug) || null;

  useEffect(() => {
    if (selected) {
      setForm({
        slug: selected.slug,
        titolo: selected.titolo,
        sottotitolo: selected.sottotitolo || '',
        ordine: selected.ordine ?? 0,
        attivo: !!selected.attivo,
        stile_preset: selected.stile_preset || 'giocatore',
      });
      setStileOverride(
        selected.stile && typeof selected.stile === 'object' ? { ...selected.stile } : emptyStileOverride(),
      );
      setCopertinaFile(null);
      loadStorico(selected.slug);
    } else {
      setForm(emptyForm);
      setStileOverride(emptyStileOverride());
      setCopertinaFile(null);
      setStorico([]);
    }
  }, [selected, loadStorico]);

  useEffect(() => {
    if (!batchPolling || !batchJob?.id) return undefined;
    const terminal = ['completed', 'partial', 'failed'];
    if (terminal.includes(batchJob.status)) {
      setBatchPolling(false);
      loadManuali();
      loadDiagnostica();
      return undefined;
    }
    const t = setInterval(async () => {
      try {
        const job = await getWikiManualeBatchJob(batchJob.id, onLogout);
        setBatchJob(job);
      } catch (e) {
        console.error(e);
        setBatchPolling(false);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [batchPolling, batchJob, onLogout, loadManuali, loadDiagnostica]);

  const buildFormData = () => {
    const fd = new FormData();
    fd.append('slug', form.slug.trim());
    fd.append('titolo', form.titolo.trim());
    fd.append('sottotitolo', form.sottotitolo || '');
    fd.append('ordine', String(form.ordine ?? 0));
    fd.append('attivo', form.attivo ? 'true' : 'false');
    fd.append('stile_preset', form.stile_preset || 'giocatore');
    const overrides = Object.fromEntries(
      Object.entries(stileOverride).filter(([, v]) => v !== '' && v != null),
    );
    fd.append('stile', JSON.stringify(overrides));
    if (copertinaFile) fd.append('copertina', copertinaFile);
    return fd;
  };

  const handleSave = async () => {
    if (!form.slug.trim() || !form.titolo.trim()) {
      setMessage('Slug e titolo sono obbligatori.');
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      const fd = buildFormData();
      if (selected) {
        await updateStaffManualePdf(selected.slug, fd, onLogout);
      } else {
        await createStaffManualePdf(fd, onLogout);
      }
      await loadManuali();
      setSelectedSlug(form.slug.trim());
      setMessage('Manuale salvato.');
    } catch (e) {
      console.error(e);
      setMessage('Errore durante il salvataggio.');
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async (slug) => {
    setGeneratingSlug(slug);
    setMessage('');
    try {
      await generateStaffManualePdf(slug, onLogout);
      await loadManuali();
      if (slug === selectedSlug) loadStorico(slug);
      setMessage(`PDF «${slug}» generato.`);
    } catch (e) {
      console.error(e);
      setMessage(e?.message || `Errore generazione PDF «${slug}».`);
    } finally {
      setGeneratingSlug(null);
    }
  };

  const handleBatchGeneraTutti = async () => {
    setMessage('');
    try {
      const job = await startWikiManualeBatchJob(onLogout);
      setBatchJob(job);
      setBatchPolling(true);
      setMessage('Generazione batch avviata in background…');
    } catch (e) {
      console.error(e);
      setMessage(e?.message || 'Impossibile avviare il batch (forse già in corso).');
    }
  };

  const formatBytes = (n) => {
    if (!n) return '—';
    if (n < 1024) return `${n} B`;
    return `${(n / 1024).toFixed(1)} KB`;
  };

  const updateOverride = (key, value) => {
    setStileOverride((prev) => {
      const next = { ...prev };
      if (value === '' || value == null) {
        delete next[key];
      } else {
        next[key] = value;
      }
      return next;
    });
  };

  const renderOverrideField = (field) => {
    const val = stileOverride[field.key] ?? '';
    if (field.type === 'select') {
      const opts = field.options.map((o) =>
        typeof o === 'string' ? { value: o, label: o } : o,
      );
      return (
        <label key={field.key} className="block text-xs">
          <span className="font-bold text-gray-500">{field.label}</span>
          <select
            className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg p-2 text-sm"
            value={val}
            onChange={(e) => updateOverride(field.key, e.target.value || null)}
          >
            <option value="">— preset —</option>
            {opts.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
      );
    }
    return (
      <label key={field.key} className="block text-xs">
        <span className="font-bold text-gray-500">{field.label}</span>
        <input
          type="number"
          step={field.step || 1}
          min={field.min}
          max={field.max}
          className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg p-2 text-sm"
          value={val}
          placeholder="preset"
          onChange={(e) => {
            const v = e.target.value;
            updateOverride(field.key, v === '' ? null : Number(v));
          }}
        />
      </label>
    );
  };

  return (
    <div className="space-y-6 p-4 md:p-6 text-white">
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-2 text-gray-400 hover:text-white text-sm font-bold uppercase"
      >
        <ArrowLeft size={16} /> Torna agli strumenti
      </button>

      <div className="flex items-center gap-3">
        <BookOpen className="text-rose-400" size={28} />
        <div>
          <h2 className="text-xl font-black uppercase tracking-wide">Manuali PDF Wiki</h2>
          <p className="text-sm text-gray-400">Preset di impaginazione, anteprima HTML e generazione PDF.</p>
        </div>
      </div>

      {message && (
        <p className="text-sm text-gray-200 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">{message}</p>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-2">
          <div className="flex justify-between items-center">
            <h3 className="text-xs font-black uppercase text-gray-500">Manuali</h3>
            <button
              type="button"
              onClick={() => { setSelectedSlug(null); setForm(emptyForm); setStileOverride(emptyStileOverride()); }}
              className="text-xs font-bold text-indigo-400 hover:text-indigo-300"
            >
              + Nuovo
            </button>
          </div>
          {loading ? (
            <p className="text-gray-500 text-sm">Caricamento...</p>
          ) : (
            <ul className="space-y-2">
              {manuali.map((m) => (
                <li key={m.slug}>
                  <button
                    type="button"
                    onClick={() => setSelectedSlug(m.slug)}
                    className={`w-full text-left p-3 rounded-xl border transition-colors ${
                      selectedSlug === m.slug
                        ? 'bg-rose-900/40 border-rose-500/50'
                        : 'bg-gray-900 border-gray-800 hover:border-gray-600'
                    }`}
                  >
                    <div className="font-bold text-sm">{m.titolo}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {m.pagine_assegnate_count ?? 0} pagine · {m.stile_preset || 'giocatore'}
                    </div>
                    {m.ultimo_generato_at && (
                      <div className="text-xs text-emerald-500/80 mt-1">
                        PDF: {new Date(m.ultimo_generato_at).toLocaleString('it-IT')}
                      </div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
          <h3 className="text-sm font-black uppercase text-gray-400">
            {selected ? `Modifica: ${selected.titolo}` : 'Nuovo manuale'}
          </h3>

          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block text-xs">
              <span className="font-bold text-gray-400">Slug</span>
              <input
                className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg p-2 text-sm"
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
                disabled={!!selected}
                placeholder="es. giocatore"
              />
            </label>
            <label className="block text-xs">
              <span className="font-bold text-gray-400">Ordine</span>
              <input
                type="number"
                className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg p-2 text-sm"
                value={form.ordine}
                onChange={(e) => setForm({ ...form, ordine: parseInt(e.target.value, 10) || 0 })}
              />
            </label>
          </div>

          <label className="block text-xs">
            <span className="font-bold text-gray-400">Titolo</span>
            <input
              className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg p-2 text-sm"
              value={form.titolo}
              onChange={(e) => setForm({ ...form, titolo: e.target.value })}
            />
          </label>

          <label className="block text-xs">
            <span className="font-bold text-gray-400">Sottotitolo</span>
            <input
              className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg p-2 text-sm"
              value={form.sottotitolo}
              onChange={(e) => setForm({ ...form, sottotitolo: e.target.value })}
            />
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.attivo}
              onChange={(e) => setForm({ ...form, attivo: e.target.checked })}
            />
            Visibile in homepage
          </label>

          <label className="block text-xs">
            <span className="font-bold text-gray-400">Preset stile PDF</span>
            <select
              className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg p-2 text-sm"
              value={form.stile_preset}
              onChange={(e) => setForm({ ...form, stile_preset: e.target.value })}
            >
              {MANUALE_PDF_PRESET_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>

          <div className="border border-gray-800 rounded-lg p-3 space-y-3">
            <p className="text-xs font-black uppercase text-gray-500">Override (opzionali)</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {MANUALE_PDF_OVERRIDE_FIELDS.map(renderOverrideField)}
            </div>
            {selected?.stile_risolto && (
              <p className="text-xs text-gray-600">
                Effettivo: {selected.stile_risolto.formato}, {selected.stile_risolto.font_size_pt}pt,
                widget {selected.stile_risolto.widget_modalita}
              </p>
            )}
          </div>

          <label className="block text-xs">
            <span className="font-bold text-gray-400">Copertina PDF (opzionale)</span>
            <input
              type="file"
              accept="image/*"
              className="mt-1 w-full text-sm text-gray-400"
              onChange={(e) => setCopertinaFile(e.target.files?.[0] || null)}
            />
          </label>

          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-bold text-sm disabled:opacity-50"
            >
              <Save size={16} /> {saving ? 'Salvataggio...' : 'Salva'}
            </button>
            {selected && (
              <>
                <a
                  href={getStaffManualePdfAnteprimaUrl(selected.slug)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-sky-500/40 text-sky-300 text-sm font-bold hover:bg-sky-500/10"
                >
                  <Eye size={16} /> Anteprima HTML
                </a>
                <button
                  type="button"
                  onClick={() => handleGenerate(selected.slug)}
                  disabled={generatingSlug === selected.slug}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-700 hover:bg-rose-600 font-bold text-sm disabled:opacity-50"
                >
                  <RefreshCw size={16} className={generatingSlug === selected.slug ? 'animate-spin' : ''} />
                  {generatingSlug === selected.slug ? 'Generazione...' : 'Genera PDF'}
                </button>
                {selected.ultimo_generato_at && (
                  <a
                    href={getWikiManualeLatestPdfUrl(selected.slug)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-500/40 text-emerald-300 text-sm font-bold"
                  >
                    <Download size={16} /> Scarica PDF
                  </a>
                )}
              </>
            )}
          </div>

          {selected && (
            <>
              <p className="text-xs text-gray-500 border-t border-gray-800 pt-3">
                Pagine incluse: <strong>{selected.pagine_assegnate_count ?? 0}</strong>
              </p>
              {storico.length > 0 && (
                <div className="border border-gray-800 rounded-lg p-3 mt-2">
                  <p className="text-xs font-black uppercase text-gray-500 flex items-center gap-1 mb-2">
                    <History size={12} /> Changelog generazioni
                  </p>
                  <ul className="text-xs space-y-1 max-h-36 overflow-y-auto">
                    {storico.slice(0, 12).map((g) => (
                      <li key={g.id} className={g.success ? 'text-gray-400' : 'text-red-400'}>
                        {new Date(g.generato_at).toLocaleString('it-IT')}
                        {' — '}
                        {g.success ? `${g.capitoli_count} cap. · ${formatBytes(g.file_size_bytes)} · ${g.durata_ms}ms` : g.error_message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <h3 className="text-xs font-black uppercase text-gray-500 mb-3 flex items-center gap-2">
            <Package size={14} /> Export e batch
          </h3>
          <div className="flex flex-wrap gap-2">
            <a
              href={getStaffManualePdfExportZipUrl()}
              className="px-3 py-2 rounded-lg border border-violet-500/40 text-violet-300 text-xs font-bold hover:bg-violet-500/10"
            >
              Scarica ZIP tutti i PDF
            </a>
            <button
              type="button"
              onClick={handleBatchGeneraTutti}
              disabled={batchPolling}
              className="px-3 py-2 rounded-lg bg-amber-800 hover:bg-amber-700 text-xs font-bold disabled:opacity-50"
            >
              {batchPolling ? 'Batch in corso…' : 'Genera tutti (background)'}
            </button>
            <button
              type="button"
              onClick={loadDiagnostica}
              className="px-3 py-2 rounded-lg bg-gray-800 text-xs font-bold"
            >
              Aggiorna diagnostica
            </button>
          </div>
          {batchJob && (
            <p className="text-xs text-gray-500 mt-2">
              Job #{batchJob.id}: <strong>{batchJob.status}</strong>
              {batchJob.results?.length > 0 && (
                <span>
                  {' '}
                  ({batchJob.results.filter((r) => r.ok).length}/{batchJob.results.length} ok)
                </span>
              )}
            </p>
          )}
          <p className="text-xs text-gray-600 mt-2">
            In produzione, per cron: <code className="text-gray-500">manage.py genera_wiki_manuali_pdf --all</code>
          </p>
        </div>

        {diagnostica && (
          <div className={`border rounded-xl p-4 ${diagnostica.has_warnings ? 'border-amber-600/50 bg-amber-950/20' : 'border-gray-800 bg-gray-900/80'}`}>
            <h3 className="text-xs font-black uppercase text-gray-500 mb-2 flex items-center gap-2">
              {diagnostica.has_warnings && <AlertTriangle size={14} className="text-amber-400" />}
              Diagnostica wiki ↔ PDF
            </h3>
            <ul className="text-xs text-gray-400 space-y-1">
              <li>Incluse senza manuale: <strong>{diagnostica.incluse_senza_manuale?.length ?? 0}</strong></li>
              <li>Assegnate ma flag spento: <strong>{diagnostica.flag_incluso_ma_non_assegnato?.length ?? 0}</strong></li>
              <li>In manuale ma non pubbliche: <strong>{diagnostica.in_manuale_non_pubbliche?.length ?? 0}</strong></li>
              <li>Manuali senza pagine: <strong>{diagnostica.manuali_senza_pagine?.length ?? 0}</strong></li>
              <li>Pubbliche non incluse (suggerite): <strong>{(diagnostica.pubbliche_con_contenuto_non_incluse?.length ?? 0) + (diagnostica.pubbliche_non_incluse_oltre_limite ?? 0)}</strong></li>
            </ul>
            {diagnostica.incluse_senza_manuale?.length > 0 && (
              <p className="text-xs text-amber-300/90 mt-2">
                Es.: {diagnostica.incluse_senza_manuale.slice(0, 3).map((p) => p.titolo).join(', ')}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(ManualePdfManager);
