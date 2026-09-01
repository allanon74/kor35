import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, Globe2, Newspaper, PenLine, Plus, RefreshCw, Trash2, UserPlus } from 'lucide-react';
import {
  concediPermessoRubrica,
  createRubrica,
  deleteArticolo,
  deleteRubrica,
  getArticolo,
  getArticoli,
  getPermessiRubrica,
  getRubriche,
  revocaPermessoRubrica,
  sincronizzaWikiRubrica,
  updateRubrica,
} from '../../api/rubriche';
import { getWikiMenu, searchPersonaggi } from '../../api';
import { useCharacter } from '../CharacterContext';
import ArticoloComposer from '../rubriche/ArticoloComposer';
import ArticoloRubricaCard from '../rubriche/ArticoloRubricaCard';
import {
  StaffToolPageTitle,
  StaffToolShell,
  staffDangerBtnClass,
  staffMutedClass,
  staffPanelClass,
  staffPrimaryBtnClass,
  staffSecondaryBtnClass,
} from '../../staff/StaffToolShell';
import { UiErrorState, UiLoadingState } from '../ui/AsyncState';

const rubricaVuota = () => ({
  nome: '',
  sottotitolo: '',
  descrizione: '',
  colore_accento: '#b91c1c',
  attiva: true,
  ordine: 0,
  pubblica_in_wiki: false,
  wiki_parent: '',
  wiki_titolo: '',
  wiki_ordine: 0,
  wiki_visibilita: 'AUTENTICATI',
});

const daRubrica = (rubrica) => ({
  nome: rubrica.nome || '',
  sottotitolo: rubrica.sottotitolo || '',
  descrizione: rubrica.descrizione || '',
  colore_accento: rubrica.colore_accento || '#b91c1c',
  attiva: rubrica.attiva !== false,
  ordine: rubrica.ordine || 0,
  pubblica_in_wiki: !!rubrica.pubblica_in_wiki,
  wiki_parent: rubrica.wiki_parent || '',
  wiki_titolo: rubrica.wiki_titolo || '',
  wiki_ordine: rubrica.wiki_ordine || 0,
  wiki_visibilita: rubrica.wiki_visibilita || 'AUTENTICATI',
});

/**
 * Tool staff «Rubriche»: CRUD testate e articoli, permessi di scrittura in-game
 * e configurazione della pubblicazione off-game in Wiki.
 */
export default function StaffRubricheManager({ onLogout }) {
  const { selectedCharacterId, isCampaignMaster, isAdmin } = useCharacter();
  // CRUD testate e rigenerazione wiki: solo master+ (vedi IsRubricaReadOrMaster lato API).
  const puoGestireRubriche = Boolean(isCampaignMaster || isAdmin);

  const [rubriche, setRubriche] = useState([]);
  const [pagineWiki, setPagineWiki] = useState([]);
  const [caricamento, setCaricamento] = useState(true);
  const [errore, setErrore] = useState('');
  const [messaggio, setMessaggio] = useState('');

  const [rubricaSelezionata, setRubricaSelezionata] = useState(null);
  const [form, setForm] = useState(rubricaVuota);
  const [formAperto, setFormAperto] = useState(false);
  const [salvataggio, setSalvataggio] = useState(false);

  const [permessi, setPermessi] = useState([]);
  const [ricercaPg, setRicercaPg] = useState('');
  const [risultatiPg, setRisultatiPg] = useState([]);

  const [articoli, setArticoli] = useState([]);
  const [composerAperto, setComposerAperto] = useState(false);
  const [articoloInModifica, setArticoloInModifica] = useState(null);

  const caricaRubriche = useCallback(async () => {
    setCaricamento(true);
    setErrore('');
    try {
      const righe = await getRubriche(selectedCharacterId, onLogout);
      setRubriche(Array.isArray(righe) ? righe : righe?.results || []);
    } catch (e) {
      setErrore(e?.message || 'Impossibile caricare le rubriche.');
    } finally {
      setCaricamento(false);
    }
  }, [selectedCharacterId, onLogout]);

  useEffect(() => {
    caricaRubriche();
    getWikiMenu()
      .then((righe) => setPagineWiki(Array.isArray(righe) ? righe : []))
      .catch(() => setPagineWiki([]));
  }, [caricaRubriche]);

  const caricaDettaglio = useCallback(
    async (rubrica) => {
      if (!rubrica) return;
      try {
        const [righePermessi, rispostaArticoli] = await Promise.all([
          getPermessiRubrica(rubrica.id, onLogout),
          getArticoli(selectedCharacterId, onLogout, { rubricaId: rubrica.id, pageSize: 50 }),
        ]);
        setPermessi(Array.isArray(righePermessi) ? righePermessi : []);
        setArticoli(
          Array.isArray(rispostaArticoli?.results) ? rispostaArticoli.results : rispostaArticoli || []
        );
      } catch (e) {
        setErrore(e?.message || 'Impossibile caricare il dettaglio della rubrica.');
      }
    },
    [selectedCharacterId, onLogout]
  );

  useEffect(() => {
    if (rubricaSelezionata) caricaDettaglio(rubricaSelezionata);
  }, [rubricaSelezionata, caricaDettaglio]);

  // Le pagine generate dalle rubriche non possono ospitarne altre.
  const pagineOrdinate = useMemo(
    () =>
      pagineWiki
        .filter((p) => !String(p.slug || '').startsWith('rubrica-'))
        .sort((a, b) => String(a.titolo).localeCompare(String(b.titolo))),
    [pagineWiki]
  );

  const aggiorna = (campo, valore) => setForm((prec) => ({ ...prec, [campo]: valore }));

  const salvaRubrica = async (evento) => {
    evento.preventDefault();
    if (!form.nome.trim()) {
      setErrore('Il nome della rubrica è obbligatorio.');
      return;
    }
    setSalvataggio(true);
    setErrore('');
    const payload = {
      ...form,
      wiki_parent: form.wiki_parent || null,
      ordine: Number(form.ordine) || 0,
      wiki_ordine: Number(form.wiki_ordine) || 0,
    };
    try {
      const salvata = rubricaSelezionata
        ? await updateRubrica(rubricaSelezionata.id, payload, selectedCharacterId, onLogout)
        : await createRubrica(payload, selectedCharacterId, onLogout);
      setMessaggio(`Rubrica «${salvata.nome}» salvata.`);
      setFormAperto(false);
      await caricaRubriche();
      setRubricaSelezionata(salvata);
    } catch (e) {
      setErrore(e?.message || 'Salvataggio rubrica non riuscito.');
    } finally {
      setSalvataggio(false);
    }
  };

  const eliminaRubrica = async (rubrica) => {
    if (!window.confirm(`Eliminare la rubrica «${rubrica.nome}» e tutti i suoi articoli?`)) return;
    try {
      await deleteRubrica(rubrica.id, selectedCharacterId, onLogout);
      setRubricaSelezionata(null);
      await caricaRubriche();
    } catch (e) {
      setErrore(e?.message || 'Eliminazione non riuscita.');
    }
  };

  const rigeneraWiki = async (rubrica) => {
    setMessaggio('');
    try {
      const esito = await sincronizzaWikiRubrica(rubrica.id, onLogout);
      setMessaggio(
        esito?.pubblicata
          ? `Wiki aggiornata: /regolamento/${esito.slug} (${esito.articoli} articoli).`
          : 'Rubrica rimossa dalla Wiki.'
      );
      await caricaRubriche();
    } catch (e) {
      setErrore(e?.message || 'Rigenerazione wiki non riuscita.');
    }
  };

  const cercaPersonaggio = async (testo) => {
    setRicercaPg(testo);
    if (testo.trim().length < 2) {
      setRisultatiPg([]);
      return;
    }
    try {
      const righe = await searchPersonaggi(testo.trim(), selectedCharacterId || '');
      setRisultatiPg(Array.isArray(righe) ? righe.slice(0, 8) : []);
    } catch {
      setRisultatiPg([]);
    }
  };

  const concediPermesso = async (personaggio) => {
    try {
      await concediPermessoRubrica(rubricaSelezionata.id, personaggio.id, '', onLogout);
      setRicercaPg('');
      setRisultatiPg([]);
      await caricaDettaglio(rubricaSelezionata);
    } catch (e) {
      setErrore(e?.message || 'Concessione permesso non riuscita.');
    }
  };

  const revocaPermesso = async (permesso) => {
    try {
      await revocaPermessoRubrica(rubricaSelezionata.id, permesso.id, onLogout);
      await caricaDettaglio(rubricaSelezionata);
    } catch (e) {
      setErrore(e?.message || 'Revoca permesso non riuscita.');
    }
  };

  const apriModificaArticolo = async (articolo) => {
    try {
      const dettaglio = await getArticolo(articolo.id, selectedCharacterId, onLogout);
      setArticoloInModifica(dettaglio);
      setComposerAperto(true);
    } catch (e) {
      setErrore(e?.message || "Impossibile aprire l'articolo.");
    }
  };

  const eliminaArticolo = async (articolo) => {
    if (!window.confirm(`Eliminare l'articolo «${articolo.titolo}»?`)) return;
    const eliminaAnnuncio =
      !!articolo.post_annuncio && window.confirm('Eliminare anche il post di lancio su InstaFame?');
    try {
      await deleteArticolo(articolo.id, selectedCharacterId, onLogout, { eliminaAnnuncio });
      await caricaDettaglio(rubricaSelezionata);
    } catch (e) {
      setErrore(e?.message || 'Eliminazione articolo non riuscita.');
    }
  };

  const campoClass = 'w-full bg-gray-900/80 border border-gray-700 rounded-lg px-3 py-2 text-sm';
  const etichettaClass = 'block text-[11px] uppercase tracking-wide text-gray-400 mb-1';

  if (caricamento) return <UiLoadingState message="Caricamento rubriche…" />;

  return (
    <StaffToolShell maxWidth="6xl">
      <StaffToolPageTitle
        icon={<Newspaper size={20} />}
        title="Rubriche"
        description="Testate in-game su InstaFame e pubblicazione off-game in Wiki."
        actions={
          <>
            <button
              type="button"
              className={staffSecondaryBtnClass}
              onClick={caricaRubriche}
            >
              <RefreshCw size={15} /> Aggiorna
            </button>
            {puoGestireRubriche && (
              <button
                type="button"
                className={staffPrimaryBtnClass}
                onClick={() => {
                  setRubricaSelezionata(null);
                  setForm(rubricaVuota());
                  setFormAperto(true);
                }}
              >
                <Plus size={15} /> Nuova rubrica
              </button>
            )}
          </>
        }
      />

      {errore && <UiErrorState message={errore} onRetry={caricaRubriche} />}
      {messaggio && (
        <p className="mb-3 text-sm text-emerald-300 bg-emerald-950/30 border border-emerald-600/40 rounded-lg px-3 py-2">
          {messaggio}
        </p>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="space-y-2">
          {rubriche.length === 0 && <p className={staffMutedClass}>Nessuna rubrica creata.</p>}
          {rubriche.map((rubrica) => (
            <button
              key={rubrica.id}
              type="button"
              onClick={() => {
                setRubricaSelezionata(rubrica);
                setForm(daRubrica(rubrica));
                setFormAperto(false);
                setComposerAperto(false);
              }}
              className={`w-full text-left rounded-xl border p-3 transition ${
                rubricaSelezionata?.id === rubrica.id
                  ? 'border-violet-500 bg-violet-950/30'
                  : 'border-gray-700 bg-gray-900/60 hover:border-gray-500'
              }`}
              style={{ borderLeft: `4px solid ${rubrica.colore_accento || '#b91c1c'}` }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-white truncate">{rubrica.nome}</span>
                {!rubrica.attiva && <span className="text-[10px] text-amber-300">disattiva</span>}
              </div>
              <p className="text-xs text-gray-400">
                {rubrica.articoli_count} articoli
                {rubrica.pubblica_in_wiki ? ' · in Wiki' : ''}
              </p>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2 space-y-4">
          {(formAperto || (rubricaSelezionata && formAperto)) && (
            <form onSubmit={salvaRubrica} className={`${staffPanelClass} space-y-3`}>
              <h3 className="font-bold text-white">
                {rubricaSelezionata ? 'Modifica rubrica' : 'Nuova rubrica'}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className={etichettaClass}>Nome</label>
                  <input value={form.nome} onChange={(e) => aggiorna('nome', e.target.value)} className={campoClass} />
                </div>
                <div>
                  <label className={etichettaClass}>Sottotitolo</label>
                  <input
                    value={form.sottotitolo}
                    onChange={(e) => aggiorna('sottotitolo', e.target.value)}
                    className={campoClass}
                  />
                </div>
              </div>
              <div>
                <label className={etichettaClass}>Descrizione</label>
                <textarea
                  value={form.descrizione}
                  onChange={(e) => aggiorna('descrizione', e.target.value)}
                  rows={2}
                  className={campoClass}
                />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className={etichettaClass}>Colore</label>
                  <input
                    type="color"
                    value={form.colore_accento}
                    onChange={(e) => aggiorna('colore_accento', e.target.value)}
                    className="w-full h-9 bg-gray-900 border border-gray-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className={etichettaClass}>Ordine</label>
                  <input
                    type="number"
                    value={form.ordine}
                    onChange={(e) => aggiorna('ordine', e.target.value)}
                    className={campoClass}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm mt-5">
                  <input
                    type="checkbox"
                    checked={form.attiva}
                    onChange={(e) => aggiorna('attiva', e.target.checked)}
                  />
                  Attiva
                </label>
              </div>

              <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-3 space-y-3">
                <label className="flex items-center gap-2 text-sm font-semibold text-sky-100">
                  <input
                    type="checkbox"
                    checked={form.pubblica_in_wiki}
                    onChange={(e) => aggiorna('pubblica_in_wiki', e.target.checked)}
                  />
                  <Globe2 size={15} /> Pubblica in Wiki (sola lettura, senza like e commenti)
                </label>
                {form.pubblica_in_wiki && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className={etichettaClass}>Pagina wiki genitore</label>
                      <select
                        value={form.wiki_parent || ''}
                        onChange={(e) => aggiorna('wiki_parent', e.target.value)}
                        className={campoClass}
                      >
                        <option value="">— radice del menu —</option>
                        {pagineOrdinate.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.titolo}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={etichettaClass}>Titolo in Wiki</label>
                      <input
                        value={form.wiki_titolo}
                        onChange={(e) => aggiorna('wiki_titolo', e.target.value)}
                        placeholder="Vuoto = nome rubrica"
                        className={campoClass}
                      />
                    </div>
                    <div>
                      <label className={etichettaClass}>Ordine nel menu</label>
                      <input
                        type="number"
                        value={form.wiki_ordine}
                        onChange={(e) => aggiorna('wiki_ordine', e.target.value)}
                        className={campoClass}
                      />
                    </div>
                    <div>
                      <label className={etichettaClass}>Visibilità</label>
                      <select
                        value={form.wiki_visibilita}
                        onChange={(e) => aggiorna('wiki_visibilita', e.target.value)}
                        className={campoClass}
                      >
                        <option value="AUTENTICATI">Solo utenti loggati</option>
                        <option value="PUBBLICA">Visibile a tutti</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button type="submit" disabled={salvataggio} className={staffPrimaryBtnClass}>
                  {salvataggio ? 'Salvataggio…' : 'Salva rubrica'}
                </button>
                <button type="button" onClick={() => setFormAperto(false)} className={staffSecondaryBtnClass}>
                  Annulla
                </button>
              </div>
            </form>
          )}

          {rubricaSelezionata && !formAperto && (
            <>
              <div className={`${staffPanelClass} space-y-3`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <BookOpen size={18} className="text-violet-400 shrink-0" />
                    <h3 className="font-bold text-white truncate">{rubricaSelezionata.nome}</h3>
                  </div>
                  {puoGestireRubriche && (
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className={staffSecondaryBtnClass} onClick={() => setFormAperto(true)}>
                        Modifica
                      </button>
                      <button
                        type="button"
                        className={staffSecondaryBtnClass}
                        onClick={() => rigeneraWiki(rubricaSelezionata)}
                      >
                        <Globe2 size={15} /> Rigenera Wiki
                      </button>
                      <button
                        type="button"
                        className={staffDangerBtnClass}
                        onClick={() => eliminaRubrica(rubricaSelezionata)}
                      >
                        <Trash2 size={15} /> Elimina
                      </button>
                    </div>
                  )}
                </div>
                {rubricaSelezionata.wiki_pagina_slug && (
                  <p className="text-xs text-sky-300">
                    Pagina wiki:{' '}
                    <a
                      href={`/regolamento/${rubricaSelezionata.wiki_pagina_slug}`}
                      className="underline"
                      target="_blank"
                      rel="noreferrer"
                    >
                      /regolamento/{rubricaSelezionata.wiki_pagina_slug}
                    </a>
                  </p>
                )}
              </div>

              <div className={`${staffPanelClass} space-y-3`}>
                <h4 className="font-semibold text-white flex items-center gap-2">
                  <UserPlus size={16} /> Personaggi autorizzati a scrivere
                </h4>
                <input
                  value={ricercaPg}
                  onChange={(e) => cercaPersonaggio(e.target.value)}
                  placeholder="Cerca personaggio da autorizzare…"
                  className={campoClass}
                />
                {risultatiPg.length > 0 && (
                  <ul className="rounded-lg border border-gray-700 bg-gray-900 divide-y divide-gray-800 max-h-40 overflow-auto">
                    {risultatiPg.map((p) => (
                      <li key={p.id}>
                        <button
                          type="button"
                          onClick={() => concediPermesso(p)}
                          className="w-full text-left px-2 py-1.5 text-xs hover:bg-gray-800"
                        >
                          {p.nome}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {permessi.length === 0 ? (
                  <p className={staffMutedClass}>Nessun personaggio autorizzato (solo staff può scrivere).</p>
                ) : (
                  <ul className="space-y-1">
                    {permessi.map((permesso) => (
                      <li
                        key={permesso.id}
                        className="flex items-center justify-between gap-2 text-sm bg-gray-900/60 border border-gray-700 rounded-lg px-2 py-1.5"
                      >
                        <span className="truncate">{permesso.personaggio_nome}</span>
                        <button
                          type="button"
                          onClick={() => revocaPermesso(permesso)}
                          className="text-xs text-red-300 hover:text-red-200"
                        >
                          revoca
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={`${staffPanelClass} space-y-3`}>
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-semibold text-white">Articoli ({articoli.length})</h4>
                  <button
                    type="button"
                    className={staffPrimaryBtnClass}
                    onClick={() => {
                      setArticoloInModifica(null);
                      setComposerAperto((s) => !s);
                    }}
                  >
                    <PenLine size={15} /> {composerAperto ? 'Chiudi' : 'Nuovo articolo'}
                  </button>
                </div>

                {composerAperto && (
                  <ArticoloComposer
                    rubriche={rubriche}
                    articolo={articoloInModifica}
                    rubricaPreselezionata={rubricaSelezionata.id}
                    personaggioAttivo={selectedCharacterId ? { id: selectedCharacterId } : null}
                    modalitaStaff
                    onSalvato={async (salvato) => {
                      if (salvato?.id) {
                        setArticoloInModifica(salvato);
                        setComposerAperto(true);
                      } else {
                        setComposerAperto(false);
                        setArticoloInModifica(null);
                      }
                      await caricaDettaglio(rubricaSelezionata);
                      await caricaRubriche();
                    }}
                    onAnnulla={() => {
                      setComposerAperto(false);
                      setArticoloInModifica(null);
                    }}
                    onLogout={onLogout}
                  />
                )}

                {articoli.length === 0 && <p className={staffMutedClass}>Nessun articolo.</p>}
                <div className="space-y-2">
                  {articoli.map((articolo) => (
                    <div key={articolo.id} className="space-y-1">
                      <ArticoloRubricaCard articolo={articolo} onOpen={apriModificaArticolo} />
                      <div className="flex justify-end gap-2">
                        {articolo.post_annuncio && (
                          <span className="text-[11px] text-fuchsia-300">post di lancio pubblicato</span>
                        )}
                        <button
                          type="button"
                          onClick={() => eliminaArticolo(articolo)}
                          className="text-[11px] text-red-300 hover:text-red-200"
                        >
                          elimina articolo
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </StaffToolShell>
  );
}
