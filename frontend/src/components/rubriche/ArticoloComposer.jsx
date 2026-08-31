import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ImagePlus, Megaphone, Save, Video, X } from 'lucide-react';
import RichTextEditor from '../RichTextEditor';
import { searchPersonaggi } from '../../api';
import { createArticolo, updateArticolo } from '../../api/rubriche';

const STATI = [
  { id: 'BOZZA', label: 'Bozza' },
  { id: 'PUBBLICATO', label: 'Pubblicato' },
  { id: 'ARCHIVIATO', label: 'Archiviato' },
];

const formVuoto = (rubricaId) => ({
  rubrica: rubricaId || '',
  stato: 'BOZZA',
  occhiello: '',
  titolo: '',
  sottotitolo: '',
  sommario: '',
  corpo: '',
  hero_didascalia: '',
  firma_libera: '',
  autore_personaggio: '',
});

const formDaArticolo = (articolo) => ({
  rubrica: articolo.rubrica || '',
  stato: articolo.stato || 'BOZZA',
  occhiello: articolo.occhiello || '',
  titolo: articolo.titolo || '',
  sottotitolo: articolo.sottotitolo || '',
  sommario: articolo.sommario || '',
  corpo: articolo.corpo || '',
  hero_didascalia: articolo.hero_didascalia || '',
  firma_libera: articolo.firma_libera || '',
  autore_personaggio: articolo.autore_personaggio || '',
});

/**
 * Composer articoli: usato sia nella sezione Rubriche di InstaFame sia nel tool staff.
 * In modalità staff si può scegliere il personaggio firmatario o una firma libera.
 */
export default function ArticoloComposer({
  rubriche = [],
  articolo = null,
  rubricaPreselezionata = '',
  personaggioAttivo = null,
  modalitaStaff = false,
  onSalvato,
  onAnnulla,
  onLogout,
}) {
  const [form, setForm] = useState(() =>
    articolo ? formDaArticolo(articolo) : formVuoto(rubricaPreselezionata)
  );
  const [heroFile, setHeroFile] = useState(null);
  const [galleriaFiles, setGalleriaFiles] = useState([]);
  const [videoFile, setVideoFile] = useState(null);
  const [pulisciGalleria, setPulisciGalleria] = useState(false);
  const [salvataggio, setSalvataggio] = useState(false);
  const [errore, setErrore] = useState('');

  const [annuncioAttivo, setAnnuncioAttivo] = useState(false);
  const [annuncioTesto, setAnnuncioTesto] = useState('');

  const [ricercaAutore, setRicercaAutore] = useState('');
  const [risultatiAutore, setRisultatiAutore] = useState([]);
  const [autoreScelto, setAutoreScelto] = useState(
    articolo?.autore_personaggio ? { id: articolo.autore_personaggio, nome: articolo.firma } : null
  );

  const inModifica = Boolean(articolo?.id);
  const haGiaAnnuncio = Boolean(articolo?.post_annuncio);

  useEffect(() => {
    if (articolo) setForm(formDaArticolo(articolo));
  }, [articolo]);

  const rubricheDisponibili = useMemo(
    () => rubriche.filter((r) => modalitaStaff || r.can_write),
    [rubriche, modalitaStaff]
  );

  const aggiorna = (campo, valore) => setForm((prec) => ({ ...prec, [campo]: valore }));

  const cercaAutore = useCallback(
    async (testo) => {
      setRicercaAutore(testo);
      if (testo.trim().length < 2) {
        setRisultatiAutore([]);
        return;
      }
      try {
        const righe = await searchPersonaggi(testo.trim(), personaggioAttivo?.id || '');
        setRisultatiAutore(Array.isArray(righe) ? righe.slice(0, 8) : []);
      } catch {
        setRisultatiAutore([]);
      }
    },
    [personaggioAttivo]
  );

  const salva = async (evento) => {
    evento.preventDefault();
    setErrore('');

    if (!form.rubrica) {
      setErrore('Scegli la rubrica.');
      return;
    }
    if (!form.titolo.trim()) {
      setErrore('Il titolo è obbligatorio.');
      return;
    }

    const dati = new FormData();
    dati.append('rubrica', form.rubrica);
    dati.append('stato', form.stato);
    dati.append('occhiello', form.occhiello);
    dati.append('titolo', form.titolo);
    dati.append('sottotitolo', form.sottotitolo);
    dati.append('sommario', form.sommario);
    dati.append('corpo', form.corpo);
    dati.append('hero_didascalia', form.hero_didascalia);
    dati.append('firma_libera', form.firma_libera);

    if (modalitaStaff) {
      if (autoreScelto?.id) dati.append('autore_personaggio', autoreScelto.id);
    } else if (personaggioAttivo?.id) {
      dati.append('autore_personaggio', personaggioAttivo.id);
    }

    if (heroFile) dati.append('hero_immagine', heroFile);
    if (videoFile) dati.append('video', videoFile);
    galleriaFiles.forEach((file) => dati.append('immagini', file));
    if (pulisciGalleria) dati.append('clear_immagini', '1');

    const annuncioRichiesto = annuncioAttivo && form.stato === 'PUBBLICATO' && !haGiaAnnuncio;
    const firmatarioAnnuncio = modalitaStaff ? autoreScelto?.id : personaggioAttivo?.id;
    if (annuncioRichiesto && !firmatarioAnnuncio) {
      setErrore('Il post di lancio deve essere firmato da un personaggio: selezionane uno.');
      return;
    }
    if (annuncioRichiesto) {
      dati.append('crea_post_annuncio', '1');
      if (annuncioTesto.trim()) dati.append('annuncio_testo', annuncioTesto.trim());
      dati.append('annuncio_autore_personaggio_id', firmatarioAnnuncio);
    }

    setSalvataggio(true);
    try {
      const salvato = inModifica
        ? await updateArticolo(articolo.id, dati, personaggioAttivo?.id, onLogout)
        : await createArticolo(dati, personaggioAttivo?.id, onLogout);
      onSalvato?.(salvato);
    } catch (e) {
      setErrore(e?.message || 'Salvataggio non riuscito.');
    } finally {
      setSalvataggio(false);
    }
  };

  const campoClass = 'w-full bg-gray-900/80 border border-gray-700 rounded-lg px-3 py-2 text-sm';
  const etichettaClass = 'block text-[11px] uppercase tracking-wide text-gray-400 mb-1';

  return (
    <form onSubmit={salva} className="rounded-2xl border border-indigo-500/30 bg-gray-900/70 p-3 md:p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-bold text-indigo-200">{inModifica ? 'Modifica articolo' : 'Nuovo articolo'}</h3>
        {onAnnulla && (
          <button type="button" onClick={onAnnulla} className="text-gray-400 hover:text-white" title="Chiudi">
            <X size={18} />
          </button>
        )}
      </div>

      {errore && (
        <p className="text-xs text-red-200 bg-red-950/40 border border-red-500/40 rounded-lg px-3 py-2">{errore}</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label className={etichettaClass}>Rubrica</label>
          <select
            value={form.rubrica}
            onChange={(e) => aggiorna('rubrica', e.target.value)}
            className={campoClass}
          >
            <option value="">— scegli —</option>
            {rubricheDisponibili.map((r) => (
              <option key={r.id} value={r.id}>
                {r.nome}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={etichettaClass}>Stato</label>
          <select value={form.stato} onChange={(e) => aggiorna('stato', e.target.value)} className={campoClass}>
            {STATI.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={etichettaClass}>Occhiello</label>
          <input
            value={form.occhiello}
            onChange={(e) => aggiorna('occhiello', e.target.value)}
            placeholder="Es. INCHIESTA"
            maxLength={120}
            className={campoClass}
          />
        </div>
      </div>

      <div>
        <label className={etichettaClass}>Titolo</label>
        <input
          value={form.titolo}
          onChange={(e) => aggiorna('titolo', e.target.value)}
          maxLength={200}
          className={`${campoClass} font-serif text-base`}
        />
      </div>

      <div>
        <label className={etichettaClass}>Sottotitolo</label>
        <input
          value={form.sottotitolo}
          onChange={(e) => aggiorna('sottotitolo', e.target.value)}
          maxLength={300}
          className={campoClass}
        />
      </div>

      <div>
        <label className={etichettaClass}>Sommario (occhio del lettore)</label>
        <textarea
          value={form.sommario}
          onChange={(e) => aggiorna('sommario', e.target.value)}
          rows={2}
          placeholder="Se vuoto viene generato dalle prime righe del testo."
          className={campoClass}
        />
      </div>

      <div>
        <label className={etichettaClass}>Corpo dell'articolo</label>
        <RichTextEditor
          value={form.corpo}
          onChange={(html) => aggiorna('corpo', html)}
          placeholder="Scrivi il pezzo…"
          minHeight={220}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className={etichettaClass}>
            <span className="inline-flex items-center gap-1">
              <ImagePlus size={12} /> Immagine di apertura
            </span>
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setHeroFile(e.target.files?.[0] || null)}
            className="text-xs"
          />
          <input
            value={form.hero_didascalia}
            onChange={(e) => aggiorna('hero_didascalia', e.target.value)}
            placeholder="Didascalia"
            className={`${campoClass} mt-2`}
          />
        </div>
        <div>
          <label className={etichettaClass}>
            <span className="inline-flex items-center gap-1">
              <ImagePlus size={12} /> Galleria (max 8)
            </span>
          </label>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setGalleriaFiles(Array.from(e.target.files || []))}
            className="text-xs"
          />
          {inModifica && (
            <label className="flex items-center gap-2 text-[11px] text-gray-400 mt-2">
              <input
                type="checkbox"
                checked={pulisciGalleria}
                onChange={(e) => setPulisciGalleria(e.target.checked)}
              />
              Svuota la galleria esistente
            </label>
          )}
          <label className={`${etichettaClass} mt-3`}>
            <span className="inline-flex items-center gap-1">
              <Video size={12} /> Video (alternativo alla galleria)
            </span>
          </label>
          <input
            type="file"
            accept="video/*"
            onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
            className="text-xs"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 border-t border-white/10 pt-3">
        {modalitaStaff ? (
          <div>
            <label className={etichettaClass}>Firma con un personaggio</label>
            {autoreScelto ? (
              <div className="flex items-center gap-2 text-sm">
                <span className="px-2 py-1 rounded-lg bg-fuchsia-900/40 border border-fuchsia-400/40">
                  {autoreScelto.nome || autoreScelto.id}
                </span>
                <button
                  type="button"
                  onClick={() => setAutoreScelto(null)}
                  className="text-xs text-gray-400 hover:text-white"
                >
                  rimuovi
                </button>
              </div>
            ) : (
              <>
                <input
                  value={ricercaAutore}
                  onChange={(e) => cercaAutore(e.target.value)}
                  placeholder="Cerca personaggio…"
                  className={campoClass}
                />
                {risultatiAutore.length > 0 && (
                  <ul className="mt-1 rounded-lg border border-gray-700 bg-gray-900 divide-y divide-gray-800 max-h-40 overflow-auto">
                    {risultatiAutore.map((p) => (
                      <li key={p.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setAutoreScelto({ id: p.id, nome: p.nome });
                            setRisultatiAutore([]);
                            setRicercaAutore('');
                          }}
                          className="w-full text-left px-2 py-1.5 text-xs hover:bg-gray-800"
                        >
                          {p.nome}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        ) : (
          <div>
            <label className={etichettaClass}>Firma</label>
            <p className="text-sm text-amber-100">{personaggioAttivo?.nome || 'Personaggio attivo'}</p>
          </div>
        )}

        <div>
          <label className={etichettaClass}>Firma libera (nome di penna)</label>
          <input
            value={form.firma_libera}
            onChange={(e) => aggiorna('firma_libera', e.target.value)}
            placeholder="Es. La Redazione"
            maxLength={160}
            className={campoClass}
          />
        </div>
      </div>

      {form.stato === 'PUBBLICATO' && !haGiaAnnuncio && (
        <div className="rounded-xl border border-fuchsia-400/30 bg-fuchsia-950/20 p-3 space-y-2">
          <label className="flex items-center gap-2 text-sm font-semibold text-fuchsia-100">
            <input
              type="checkbox"
              checked={annuncioAttivo}
              onChange={(e) => setAnnuncioAttivo(e.target.checked)}
            />
            <Megaphone size={15} /> Annuncia l'uscita con un post InstaFame
          </label>
          {annuncioAttivo && (
            <>
              <p className="text-[11px] text-fuchsia-200/70">
                Il post riporta anteprima e link all'articolo. Se lasci vuoto il testo viene composto da
                occhiello, titolo e sommario.
              </p>
              <textarea
                value={annuncioTesto}
                onChange={(e) => setAnnuncioTesto(e.target.value)}
                rows={2}
                placeholder="Testo del post di lancio (facoltativo)"
                className={campoClass}
              />
              {modalitaStaff && !autoreScelto && (
                <p className="text-[11px] text-amber-300">
                  Il post di lancio deve essere firmato da un personaggio: selezionane uno qui sopra.
                </p>
              )}
            </>
          )}
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={salvataggio}
          className="inline-flex items-center gap-1 px-3 py-2 rounded-xl bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-sm font-bold"
        >
          <Save size={15} /> {salvataggio ? 'Salvataggio…' : 'Salva articolo'}
        </button>
        {onAnnulla && (
          <button
            type="button"
            onClick={onAnnulla}
            className="px-3 py-2 rounded-xl bg-gray-800 border border-gray-700 hover:bg-gray-700 text-sm"
          >
            Annulla
          </button>
        )}
      </div>
    </form>
  );
}
