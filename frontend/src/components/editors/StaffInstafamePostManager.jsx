import React, { useCallback, useEffect, useState } from 'react';
import { ArrowRightLeft, RefreshCw, Save, Search } from 'lucide-react';
import { getEventi, searchPersonaggi, socialGetKorpList } from '../../api';
import { getRubriche } from '../../api/rubriche';
import {
  staffGetContenutoInstafame,
  staffListContenutiInstafame,
  staffPatchContenutoInstafame,
  staffSpostaPostInRubrica,
} from '../../api/social';
import { useCharacter } from '../CharacterContext';
import InstafameMentionField from '../InstafameMentionField';
import {
  StaffToolPageTitle,
  StaffToolShell,
  staffMutedClass,
  staffPanelClass,
  staffPrimaryBtnClass,
  staffSecondaryBtnClass,
} from '../../staff/StaffToolShell';

const inputClass = 'w-full min-w-0 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white';

const aInputLocale = (iso) => {
  if (!iso) return '';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}T${pad(data.getHours())}:${pad(data.getMinutes())}`;
};

const daInputLocale = (valore) => {
  if (!valore) return null;
  const data = new Date(valore);
  if (Number.isNaN(data.getTime())) return null;
  return data.toISOString();
};

const normalizzaLista = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  return [];
};

const etichettaData = (iso) => {
  if (!iso) return '';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '';
  return data.toLocaleString('it-IT');
};

export default function StaffInstafamePostManager({ onLogout }) {
  const { selectedCharacterId } = useCharacter();
  const [filtri, setFiltri] = useState({
    tipo: 'tutti',
    q: '',
    utente: '',
    evento_id: '',
    korp_id: '',
    rubrica_id: '',
    hashtag: '',
  });
  const [pagina, setPagina] = useState(1);
  const [elenco, setElenco] = useState({ count: 0, results: [], troncato: false, page_size: 20 });
  const [eventi, setEventi] = useState([]);
  const [korp, setKorp] = useState([]);
  const [rubriche, setRubriche] = useState([]);
  const [caricamento, setCaricamento] = useState(false);
  const [errore, setErrore] = useState('');
  const [dettaglio, setDettaglio] = useState(null);
  const [form, setForm] = useState(null);
  const [autoreQuery, setAutoreQuery] = useState('');
  const [autori, setAutori] = useState([]);
  const [salvataggio, setSalvataggio] = useState(false);
  const [spostamento, setSpostamento] = useState({ rubrica: '', mantieni: true });
  const [messaggio, setMessaggio] = useState('');

  useEffect(() => {
    let attivo = true;
    (async () => {
      try {
        const [ev, ko, ru] = await Promise.all([
          getEventi(onLogout),
          socialGetKorpList(onLogout),
          getRubriche(selectedCharacterId, onLogout),
        ]);
        if (!attivo) return;
        setEventi(normalizzaLista(ev));
        setKorp(normalizzaLista(ko));
        setRubriche(normalizzaLista(ru));
      } catch (e) {
        if (attivo) setErrore(e?.message || 'Impossibile caricare filtri.');
      }
    })();
    return () => {
      attivo = false;
    };
  }, [onLogout, selectedCharacterId]);

  const carica = useCallback(async (paginaRichiesta = 1) => {
    setCaricamento(true);
    setErrore('');
    try {
      const dati = await staffListContenutiInstafame({ ...filtri, page: paginaRichiesta, page_size: 20 }, onLogout);
      setElenco({
        count: dati?.count || 0,
        results: Array.isArray(dati?.results) ? dati.results : [],
        troncato: !!dati?.troncato,
        page_size: dati?.page_size || 20,
      });
      setPagina(dati?.page || paginaRichiesta);
    } catch (e) {
      setErrore(e?.message || 'Ricerca non riuscita.');
    } finally {
      setCaricamento(false);
    }
  }, [filtri, onLogout]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      carica(1);
    }, 280);
    return () => window.clearTimeout(timer);
  }, [carica]);

  const aggiornaFiltro = (campo, valore) => {
    setFiltri((prec) => ({ ...prec, [campo]: valore }));
  };

  const apri = async (riga) => {
    setErrore('');
    setMessaggio('');
    try {
      const dati = await staffGetContenutoInstafame(riga.tipo, riga.id, onLogout);
      setDettaglio(dati);
      setForm(dati);
      setAutoreQuery(dati.autore_nome || '');
      setAutori([]);
      setSpostamento({ rubrica: dati.rubrica_id || rubriche[0]?.id || '', mantieni: true });
    } catch (e) {
      setErrore(e?.message || 'Impossibile aprire il contenuto.');
    }
  };

  const cercaAutori = async (testo) => {
    setAutoreQuery(testo);
    if (!testo.trim()) {
      setAutori([]);
      return;
    }
    try {
      const righe = await searchPersonaggi(testo.trim(), selectedCharacterId || '');
      setAutori(Array.isArray(righe) ? righe.slice(0, 8) : []);
    } catch {
      setAutori([]);
    }
  };

  const scegliAutore = (personaggio) => {
    setForm((prec) => ({ ...prec, autore_id: personaggio.id, autore_nome: personaggio.nome }));
    setAutoreQuery(personaggio.nome || '');
    setAutori([]);
  };

  const salva = async () => {
    if (!form || !dettaglio) return;
    setSalvataggio(true);
    setErrore('');
    setMessaggio('');
    try {
      const dataSeCambiata = (iso, input) => {
        if (!input || aInputLocale(iso) === input) return iso || null;
        return daInputLocale(input);
      };
      const payload = dettaglio.tipo === 'post'
        ? {
            autore: form.autore_id,
            titolo: form.titolo,
            testo: form.testo,
            evento_id: form.evento_id || null,
            created_at: dataSeCambiata(form.created_at, form._dataInput ?? aInputLocale(form.created_at)),
            visibilita: form.visibilita,
            korp_id: form.visibilita === 'KORP' ? form.korp_id || null : null,
          }
        : {
            autore_id: form.autore_id || null,
            firma_libera: form.firma_libera || '',
            rubrica_id: form.rubrica_id,
            stato: form.stato || form.visibilita,
            occhiello: form.occhiello || '',
            titolo: form.titolo,
            sottotitolo: form.sottotitolo || '',
            sommario: form.sommario || '',
            corpo: form.corpo || '',
            evento_id: form.evento_id || null,
            data_pubblicazione: dataSeCambiata(
              form.data_pubblicazione,
              form._dataPubblicazioneInput ?? aInputLocale(form.data_pubblicazione)
            ),
          };
      const salvato = await staffPatchContenutoInstafame(dettaglio.tipo, dettaglio.id, payload, onLogout);
      setDettaglio(salvato);
      setForm(salvato);
      setMessaggio('Contenuto aggiornato. Hashtag e citazioni sono stati riallineati.');
      await carica(pagina);
    } catch (e) {
      setErrore(e?.message || 'Salvataggio non riuscito.');
    } finally {
      setSalvataggio(false);
    }
  };

  const sposta = async () => {
    if (!dettaglio || dettaglio.tipo !== 'post') return;
    if (!spostamento.rubrica) {
      setErrore('Scegli la rubrica di destinazione.');
      return;
    }
    if (!window.confirm('Spostare questo post in un articolo della rubrica? I commenti passano all\'articolo.')) return;
    setSalvataggio(true);
    setErrore('');
    setMessaggio('');
    try {
      const esito = await staffSpostaPostInRubrica(
        dettaglio.id,
        { rubrica_id: spostamento.rubrica, mantieni_post_lancio: spostamento.mantieni, stato: 'PUBBLICATO' },
        onLogout
      );
      setMessaggio(
        esito?.post_rimosso
          ? 'Post spostato: rimosso dal feed e pubblicato come articolo.'
          : 'Post spostato: resta nel feed come lancio e i commenti sono sull\'articolo.'
      );
      if (esito?.articolo) {
        setDettaglio(esito.articolo);
        setForm(esito.articolo);
      }
      await carica(pagina);
    } catch (e) {
      setErrore(e?.message || 'Spostamento non riuscito.');
    } finally {
      setSalvataggio(false);
    }
  };

  const pagine = Math.max(1, Math.ceil((elenco.count || 0) / (elenco.page_size || 20)));
  const dataInputPost = form?._dataInput ?? aInputLocale(form?.created_at);
  const dataPubblicazione = form?._dataPubblicazioneInput ?? aInputLocale(form?.data_pubblicazione || form?.data);

  return (
    <StaffToolShell>
      <StaffToolPageTitle
        title="Post InstaFame"
        description="Filtra i post del feed e gli articoli delle rubriche, correggi autore, data, evento e testo, oppure sposta un post nel corpo di una rubrica."
      />

      <div className={`${staffPanelClass} space-y-3`}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <select className={inputClass} value={filtri.tipo} onChange={(e) => aggiornaFiltro('tipo', e.target.value)}>
            <option value="tutti">Post e articoli</option>
            <option value="post">Solo post feed</option>
            <option value="articolo">Solo articoli rubrica</option>
          </select>
          <input
            className={inputClass}
            placeholder="Testo o titolo"
            value={filtri.q}
            onChange={(e) => aggiornaFiltro('q', e.target.value)}
          />
          <input
            className={inputClass}
            placeholder="Utente, email o nome PG"
            value={filtri.utente}
            onChange={(e) => aggiornaFiltro('utente', e.target.value)}
          />
          <input
            className={inputClass}
            placeholder="#hashtag"
            value={filtri.hashtag}
            onChange={(e) => aggiornaFiltro('hashtag', e.target.value)}
          />
          <select className={inputClass} value={filtri.evento_id} onChange={(e) => aggiornaFiltro('evento_id', e.target.value)}>
            <option value="">Tutti gli eventi</option>
            {eventi.map((evento) => (
              <option key={evento.id} value={evento.id}>{evento.titolo || `Evento #${evento.id}`}</option>
            ))}
          </select>
          <select className={inputClass} value={filtri.korp_id} onChange={(e) => aggiornaFiltro('korp_id', e.target.value)}>
            <option value="">Tutte le KORP</option>
            {korp.map((riga) => (
              <option key={riga.id} value={riga.id}>{riga.nome}</option>
            ))}
          </select>
          <select className={inputClass} value={filtri.rubrica_id} onChange={(e) => aggiornaFiltro('rubrica_id', e.target.value)}>
            <option value="">Tutte le rubriche</option>
            {rubriche.map((rubrica) => (
              <option key={rubrica.id} value={rubrica.id}>{rubrica.nome}</option>
            ))}
          </select>
          <button type="button" onClick={() => carica(1)} className={staffSecondaryBtnClass}>
            <RefreshCw size={14} /> Aggiorna
          </button>
        </div>
        {elenco.troncato && (
          <p className={staffMutedClass}>Risultati limitati ai più recenti. Restringi i filtri per vedere il resto.</p>
        )}
      </div>

      {errore && <p className="text-sm text-red-200 bg-red-950/40 border border-red-500/40 rounded-lg px-3 py-2">{errore}</p>}
      {messaggio && <p className="text-sm text-emerald-100 bg-emerald-950/40 border border-emerald-500/30 rounded-lg px-3 py-2">{messaggio}</p>}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 min-w-0">
        <div className="space-y-2 min-w-0">
          {caricamento && <p className={staffMutedClass}>Caricamento…</p>}
          {!caricamento && elenco.results.length === 0 && <p className={staffMutedClass}>Nessun contenuto con questi filtri.</p>}
          {elenco.results.map((riga) => (
            <button
              key={`${riga.tipo}-${riga.id}`}
              type="button"
              onClick={() => apri(riga)}
              className={`w-full text-left rounded-xl border px-3 py-2.5 min-w-0 ${
                dettaglio && String(dettaglio.id) === String(riga.id) && dettaglio.tipo === riga.tipo
                  ? 'border-fuchsia-400/60 bg-fuchsia-950/30'
                  : 'border-gray-700 bg-gray-900/50 hover:bg-gray-800/80'
              }`}
            >
              <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-wide text-fuchsia-200/80">
                <span>{riga.tipo === 'post' ? 'Post' : 'Articolo'}</span>
                {riga.rubrica_nome && <span className="text-amber-200/80">{riga.rubrica_nome}</span>}
                {riga.visibilita && <span className="text-gray-400">{riga.visibilita}</span>}
              </div>
              <div className="font-semibold text-white truncate">{riga.titolo || 'Senza titolo'}</div>
              <p className="text-xs text-gray-400 line-clamp-2">{riga.anteprima}</p>
              <div className="text-[11px] text-gray-500 mt-1 flex flex-wrap gap-x-3 gap-y-1">
                <span>{riga.autore_nome || 'Senza autore'}</span>
                {riga.utente && <span>{riga.utente}</span>}
                {riga.evento_titolo && <span>{riga.evento_titolo}</span>}
                {riga.korp_nome && <span>{riga.korp_nome}</span>}
                <span>{etichettaData(riga.data)}</span>
              </div>
            </button>
          ))}
          {pagine > 1 && (
            <div className="flex items-center justify-between gap-2 pt-1">
              <button
                type="button"
                disabled={pagina <= 1}
                onClick={() => carica(pagina - 1)}
                className={staffSecondaryBtnClass}
              >
                Precedente
              </button>
              <span className={staffMutedClass}>{pagina} / {pagine}</span>
              <button
                type="button"
                disabled={pagina >= pagine}
                onClick={() => carica(pagina + 1)}
                className={staffSecondaryBtnClass}
              >
                Successiva
              </button>
            </div>
          )}
        </div>

        {form && dettaglio && (
          <div className={`${staffPanelClass} space-y-3 min-w-0`}>
            <div className="flex items-center gap-2 text-white font-bold">
              <Search size={16} /> {dettaglio.tipo === 'post' ? 'Modifica post' : 'Modifica articolo'}
            </div>

            <label className="block text-xs text-gray-400">
              Autore
              <input
                className={`${inputClass} mt-1`}
                value={autoreQuery}
                onChange={(e) => cercaAutori(e.target.value)}
                placeholder="Cerca personaggio"
              />
            </label>
            {autori.length > 0 && (
              <div className="rounded-lg border border-gray-700 bg-gray-950 max-h-36 overflow-auto">
                {autori.map((personaggio) => (
                  <button
                    key={personaggio.id}
                    type="button"
                    onClick={() => scegliAutore(personaggio)}
                    className="block w-full text-left px-3 py-2 text-sm hover:bg-white/10"
                  >
                    {personaggio.nome}
                  </button>
                ))}
              </div>
            )}

            {dettaglio.tipo === 'articolo' && (
              <label className="block text-xs text-gray-400">
                Firma libera (se non c'è un personaggio)
                <input
                  className={`${inputClass} mt-1`}
                  value={form.firma_libera || ''}
                  onChange={(e) => setForm((prec) => ({ ...prec, firma_libera: e.target.value }))}
                />
              </label>
            )}

            <label className="block text-xs text-gray-400">
              {dettaglio.tipo === 'post' ? 'Data del post' : 'Data di pubblicazione'}
              <input
                type="datetime-local"
                className={`${inputClass} mt-1`}
                value={dettaglio.tipo === 'post' ? dataInputPost : dataPubblicazione}
                onChange={(e) => setForm((prec) => (
                  dettaglio.tipo === 'post'
                    ? { ...prec, _dataInput: e.target.value, created_at: daInputLocale(e.target.value) }
                    : { ...prec, _dataPubblicazioneInput: e.target.value, data_pubblicazione: daInputLocale(e.target.value) }
                ))}
              />
            </label>

            <label className="block text-xs text-gray-400">
              Evento
              <select
                className={`${inputClass} mt-1`}
                value={form.evento_id || ''}
                onChange={(e) => setForm((prec) => ({ ...prec, evento_id: e.target.value }))}
              >
                <option value="">Nessun evento</option>
                {eventi.map((evento) => (
                  <option key={evento.id} value={evento.id}>{evento.titolo || `Evento #${evento.id}`}</option>
                ))}
              </select>
            </label>

            {dettaglio.tipo === 'post' ? (
              <>
                <label className="block text-xs text-gray-400">
                  Visibilità
                  <select
                    className={`${inputClass} mt-1`}
                    value={form.visibilita || 'PUB'}
                    onChange={(e) => setForm((prec) => ({ ...prec, visibilita: e.target.value }))}
                  >
                    <option value="PUB">Pubblico</option>
                    <option value="KORP">Solo KORP</option>
                  </select>
                </label>
                {form.visibilita === 'KORP' && (
                  <label className="block text-xs text-gray-400">
                    KORP
                    <select
                      className={`${inputClass} mt-1`}
                      value={form.korp_id || ''}
                      onChange={(e) => setForm((prec) => ({ ...prec, korp_id: e.target.value }))}
                    >
                      <option value="">Seleziona</option>
                      {korp.map((riga) => (
                        <option key={riga.id} value={riga.id}>{riga.nome}</option>
                      ))}
                    </select>
                  </label>
                )}
              </>
            ) : (
              <>
                <label className="block text-xs text-gray-400">
                  Rubrica
                  <select
                    className={`${inputClass} mt-1`}
                    value={form.rubrica_id || ''}
                    onChange={(e) => setForm((prec) => ({ ...prec, rubrica_id: e.target.value }))}
                  >
                    {rubriche.map((rubrica) => (
                      <option key={rubrica.id} value={rubrica.id}>{rubrica.nome}</option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs text-gray-400">
                  Stato
                  <select
                    className={`${inputClass} mt-1`}
                    value={form.stato || form.visibilita || 'PUBBLICATO'}
                    onChange={(e) => setForm((prec) => ({ ...prec, stato: e.target.value }))}
                  >
                    <option value="BOZZA">Bozza</option>
                    <option value="PUBBLICATO">Pubblicato</option>
                    <option value="ARCHIVIATO">Archiviato</option>
                  </select>
                </label>
                <label className="block text-xs text-gray-400">
                  Occhiello
                  <input
                    className={`${inputClass} mt-1`}
                    value={form.occhiello || ''}
                    onChange={(e) => setForm((prec) => ({ ...prec, occhiello: e.target.value }))}
                  />
                </label>
              </>
            )}

            <label className="block text-xs text-gray-400">
              Titolo
              <input
                className={`${inputClass} mt-1`}
                value={form.titolo || ''}
                onChange={(e) => setForm((prec) => ({ ...prec, titolo: e.target.value }))}
              />
            </label>

            {dettaglio.tipo === 'articolo' && (
              <>
                <label className="block text-xs text-gray-400">
                  Sottotitolo
                  <input
                    className={`${inputClass} mt-1`}
                    value={form.sottotitolo || ''}
                    onChange={(e) => setForm((prec) => ({ ...prec, sottotitolo: e.target.value }))}
                  />
                </label>
                <div className="text-xs text-gray-400">
                  Sommario
                  <InstafameMentionField
                    value={form.sommario || ''}
                    onChange={(sommario) => setForm((prec) => ({ ...prec, sommario }))}
                    personaggioId={selectedCharacterId}
                    rows={3}
                    showHashtags
                    className="mt-1"
                    placeholder="Sommario, con @citazioni e #hashtag"
                  />
                </div>
                <div className="text-xs text-gray-400">
                  Corpo
                  <InstafameMentionField
                    value={form.corpo || ''}
                    onChange={(corpo) => setForm((prec) => ({ ...prec, corpo }))}
                    personaggioId={selectedCharacterId}
                    rows={8}
                    showHashtags
                    className="mt-1"
                    placeholder="Testo dell'articolo. @nome cita un personaggio, #tema è un hashtag."
                  />
                </div>
              </>
            )}

            {dettaglio.tipo === 'post' && (
              <div className="text-xs text-gray-400">
                Testo
                <InstafameMentionField
                  value={form.testo || ''}
                  onChange={(testo) => setForm((prec) => ({ ...prec, testo }))}
                  personaggioId={selectedCharacterId}
                  rows={6}
                  showHashtags
                  className="mt-1"
                  placeholder="Testo del post. @ per citare, # per gli hashtag."
                />
              </div>
            )}

            {Array.isArray(form.tags) && form.tags.length > 0 && (
              <p className="text-xs text-amber-200/90">
                Citati: {form.tags.map((tag) => tag.personaggio__nome).filter(Boolean).join(', ')}
              </p>
            )}

            <button type="button" onClick={salva} disabled={salvataggio} className={staffPrimaryBtnClass}>
              <Save size={14} /> {salvataggio ? 'Salvataggio…' : 'Salva'}
            </button>

            {dettaglio.tipo === 'post' && !dettaglio.articolo_id && (
              <div className="border-t border-gray-700 pt-3 space-y-2">
                <div className="text-sm font-semibold text-white flex items-center gap-2">
                  <ArrowRightLeft size={15} /> Sposta in una rubrica
                </div>
                <p className={staffMutedClass}>
                  Il testo, l'autore, la data, l'evento e i commenti diventano un articolo. Le citazioni e gli hashtag restano nel testo.
                </p>
                <select
                  className={inputClass}
                  value={spostamento.rubrica}
                  onChange={(e) => setSpostamento((prec) => ({ ...prec, rubrica: e.target.value }))}
                >
                  <option value="">Scegli rubrica</option>
                  {rubriche.map((rubrica) => (
                    <option key={rubrica.id} value={rubrica.id}>{rubrica.nome}</option>
                  ))}
                </select>
                <label className="flex items-start gap-2 text-sm text-gray-200">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={spostamento.mantieni}
                    onChange={(e) => setSpostamento((prec) => ({ ...prec, mantieni: e.target.checked }))}
                  />
                  <span>Lascia il post nel feed come lancio dell'articolo. I commenti passano comunque all'articolo.</span>
                </label>
                <button type="button" onClick={sposta} disabled={salvataggio} className={staffSecondaryBtnClass}>
                  Sposta nella rubrica
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </StaffToolShell>
  );
}
