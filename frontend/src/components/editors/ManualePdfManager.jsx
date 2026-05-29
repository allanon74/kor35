import React, { useCallback, useEffect, useState, memo } from 'react';
import { ArrowLeft, BookOpen, Download, RefreshCw, Save } from 'lucide-react';
import {
  getStaffManualePdfList,
  createStaffManualePdf,
  updateStaffManualePdf,
  generateStaffManualePdf,
  getWikiManualeLatestPdfUrl,
} from '../../api';

const emptyForm = {
  slug: '',
  titolo: '',
  sottotitolo: '',
  ordine: 0,
  attivo: true,
};

const ManualePdfManager = ({ onBack, onLogout }) => {
  const [manuali, setManuali] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSlug, setSelectedSlug] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [copertinaFile, setCopertinaFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [generatingSlug, setGeneratingSlug] = useState(null);
  const [message, setMessage] = useState('');

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

  const selected = manuali.find((m) => m.slug === selectedSlug) || null;

  useEffect(() => {
    if (selected) {
      setForm({
        slug: selected.slug,
        titolo: selected.titolo,
        sottotitolo: selected.sottotitolo || '',
        ordine: selected.ordine ?? 0,
        attivo: !!selected.attivo,
      });
      setCopertinaFile(null);
    } else {
      setForm(emptyForm);
      setCopertinaFile(null);
    }
  }, [selected]);

  const buildFormData = () => {
    const fd = new FormData();
    fd.append('slug', form.slug.trim());
    fd.append('titolo', form.titolo.trim());
    fd.append('sottotitolo', form.sottotitolo || '');
    fd.append('ordine', String(form.ordine ?? 0));
    fd.append('attivo', form.attivo ? 'true' : 'false');
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
      setMessage(`PDF «${slug}» generato.`);
    } catch (e) {
      console.error(e);
      setMessage(e?.message || `Errore generazione PDF «${slug}».`);
    } finally {
      setGeneratingSlug(null);
    }
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
          <p className="text-sm text-gray-400">Crea volumi di regolamento e rigenera i PDF per la homepage.</p>
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
              onClick={() => { setSelectedSlug(null); setForm(emptyForm); }}
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
                      {m.pagine_assegnate_count ?? 0} pagine · {m.attivo ? 'Attivo' : 'Nascosto'}
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
            Visibile in homepage (manuale attivo)
          </label>

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
              <Save size={16} /> {saving ? 'Salvataggio...' : 'Salva manuale'}
            </button>
            {selected && (
              <>
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
            <p className="text-xs text-gray-500 border-t border-gray-800 pt-3">
              Assegna le pagine wiki dall’editor di ogni pagina (sezione «Pubblicazione PDF»).
              Pagine incluse: <strong>{selected.pagine_assegnate_count ?? 0}</strong>
            </p>
          )}
        </div>
      </div>

      {manuali.length > 0 && (
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <h3 className="text-xs font-black uppercase text-gray-500 mb-3">Rigenera tutti i manuali</h3>
          <div className="flex flex-wrap gap-2">
            {manuali.map((m) => (
              <button
                key={m.slug}
                type="button"
                onClick={() => handleGenerate(m.slug)}
                disabled={!!generatingSlug}
                className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-bold disabled:opacity-50"
              >
                {generatingSlug === m.slug ? '...' : m.titolo}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default memo(ManualePdfManager);
