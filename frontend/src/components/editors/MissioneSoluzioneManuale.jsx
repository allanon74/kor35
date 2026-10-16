import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  assegnaMissioneRisoluzione,
  getEventiOpzioni,
  getMissioni,
  getMissioniEventoAttivo,
  getMissioniEventoPartecipanti,
} from '../../api';
import { LabeledField, staffInputClass } from '../../staff/StaffCrudUi';
import SearchableSelect from './SearchableSelect';

const formatPremio = (crediti, prestigio) => {
  const cr = Number(crediti || 0).toLocaleString('it-IT');
  const pr = Number(prestigio || 0).toLocaleString('it-IT');
  return `${cr} crediti e ${pr} prestigio`;
};

/**
 * Accredito staff di una task: sceglie task e personaggio dell'evento
 * e segna la soluzione, che assegna i premi. Con un evento in corso
 * l'evento è implicito; se è chiuso lo staff sceglie quale accreditare.
 */
export default function MissioneSoluzioneManuale({ onLogout }) {
  const [booting, setBooting] = useState(true);
  const [eventoVivo, setEventoVivo] = useState(null);
  const [eventiChiusi, setEventiChiusi] = useState([]);
  const [eventoId, setEventoId] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [partecipanti, setPartecipanti] = useState([]);
  const [missioneId, setMissioneId] = useState(null);
  const [personaggioId, setPersonaggioId] = useState(null);
  const [nota, setNota] = useState('');
  const [loadingDettaglio, setLoadingDettaglio] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [esito, setEsito] = useState('');

  useEffect(() => {
    let cancel = false;
    (async () => {
      setBooting(true);
      setError('');
      try {
        const attivo = await getMissioniEventoAttivo(null, onLogout);
        if (cancel) return;
        if (attivo?.attivo && attivo.id) {
          setEventoVivo({ id: Number(attivo.id), titolo: attivo.titolo || `Evento #${attivo.id}` });
          setEventoId(Number(attivo.id));
          setEventiChiusi([]);
          return;
        }
        setEventoVivo(null);
        setEventoId(null);
        const opzioni = await getEventiOpzioni(onLogout);
        if (cancel) return;
        const rows = (Array.isArray(opzioni) ? opzioni : opzioni?.results || [])
          .filter((ev) => ev?.chiuso)
          .map((ev) => ({ id: ev.id, nome: ev.titolo || `Evento #${ev.id}` }));
        setEventiChiusi(rows);
      } catch (err) {
        if (!cancel) setError(err?.message || 'Impossibile leggere lo stato dell\'evento');
      } finally {
        if (!cancel) setBooting(false);
      }
    })();
    return () => { cancel = true; };
  }, [onLogout]);

  const caricaEvento = useCallback(async (id) => {
    if (!id) {
      setTasks([]);
      setPartecipanti([]);
      return;
    }
    setLoadingDettaglio(true);
    setError('');
    setEsito('');
    try {
      const [missioni, iscritti] = await Promise.all([
        getMissioni({ evento: id, attiva: '1' }, onLogout),
        getMissioniEventoPartecipanti(id, onLogout),
      ]);
      const rows = Array.isArray(missioni) ? missioni : missioni?.results || [];
      setTasks(rows.map((row) => ({
        id: row.id,
        nome: row.titolo || 'Task',
        reward_crediti: row.reward_crediti,
        reward_prestigio: row.reward_prestigio,
        premio_solo_primo: !!row.premio_solo_primo,
        esclusiva: !!row.esclusiva,
        korp_nome: row.korp_nome || '',
      })));
      setPartecipanti(
        (iscritti?.partecipanti || []).map((pg) => ({
          id: pg.id,
          nome: pg.nome || `Personaggio #${pg.id}`,
        })),
      );
    } catch (err) {
      setTasks([]);
      setPartecipanti([]);
      setError(err?.message || 'Impossibile caricare task e personaggi');
    } finally {
      setLoadingDettaglio(false);
    }
  }, [onLogout]);

  useEffect(() => {
    setMissioneId(null);
    setPersonaggioId(null);
    setNota('');
    caricaEvento(eventoId);
  }, [eventoId, caricaEvento]);

  const taskScelta = useMemo(
    () => tasks.find((row) => String(row.id) === String(missioneId)) || null,
    [tasks, missioneId],
  );

  const accredita = async () => {
    if (!eventoId || !missioneId || !personaggioId) {
      setError('Scegli task e personaggio.');
      return;
    }
    setSaving(true);
    setError('');
    setEsito('');
    try {
      const data = await assegnaMissioneRisoluzione({
        missione_id: missioneId,
        evento_id: Number(eventoId),
        personaggio_id: Number(personaggioId),
        note: nota.trim(),
      }, onLogout);
      const nome = data?.personaggio_nome
        || partecipanti.find((pg) => String(pg.id) === String(personaggioId))?.nome
        || 'personaggio';
      setEsito(
        `Soluzione accreditata a ${nome}: ${formatPremio(data?.reward_crediti, data?.reward_prestigio)}.`,
      );
      setPersonaggioId(null);
      setNota('');
    } catch (err) {
      setError(err?.message || 'Accredito non riuscito');
    } finally {
      setSaving(false);
    }
  };

  if (booting) {
    return <p className="text-sm text-gray-500">Caricamento evento…</p>;
  }

  return (
    <section className="w-full min-w-0 max-w-xl space-y-4">
      <div>
        <h2 className="text-sm font-black uppercase tracking-wide text-white">Soluzione manuale</h2>
        <p className="mt-1 text-sm text-gray-400">
          Segna la task come risolta per un personaggio dell&apos;evento. Il premio viene accreditato subito.
        </p>
      </div>

      {eventoVivo ? (
        <p className="rounded-lg border border-lime-900/60 bg-lime-950/30 px-3 py-2 text-sm text-lime-100">
          Evento in corso: <span className="font-semibold">{eventoVivo.titolo}</span>
        </p>
      ) : (
        <LabeledField
          label="Evento da accreditare"
          hint="Nessun evento è in corso. Scegli un evento già chiuso."
        >
          <SearchableSelect
            options={eventiChiusi}
            value={eventoId}
            onChange={(id) => setEventoId(id)}
            placeholder={eventiChiusi.length ? 'Seleziona evento' : 'Nessun evento chiuso'}
            disabled={!eventiChiusi.length}
          />
        </LabeledField>
      )}

      <LabeledField label="Task" hint="Solo le task accese nel catalogo e per l'evento scelto.">
        <SearchableSelect
          options={tasks}
          value={missioneId}
          onChange={(id) => setMissioneId(id)}
          placeholder={eventoId ? 'Seleziona task' : 'Prima scegli l\'evento'}
          disabled={!eventoId || loadingDettaglio}
        />
      </LabeledField>

      <LabeledField label="Personaggio" hint="Solo i personaggi iscritti a questo evento.">
        <SearchableSelect
          options={partecipanti}
          value={personaggioId}
          onChange={(id) => setPersonaggioId(id)}
          placeholder={eventoId ? 'Seleziona personaggio' : 'Prima scegli l\'evento'}
          disabled={!eventoId || loadingDettaglio}
        />
      </LabeledField>

      {taskScelta ? (
        <p className="text-xs leading-relaxed text-gray-400">
          Premio base: {formatPremio(taskScelta.reward_crediti, taskScelta.reward_prestigio)}.
          Il fattore KORP del personaggio si applica al salvataggio.
          {taskScelta.premio_solo_primo ? ' Premio solo al primo.' : ''}
          {taskScelta.esclusiva ? ` Esclusiva${taskScelta.korp_nome ? ` ${taskScelta.korp_nome}` : ''}.` : ''}
        </p>
      ) : null}

      <LabeledField label="Soluzione" hint="Facoltativa. Resta sulla risoluzione come nota dello staff.">
        <textarea
          className={`${staffInputClass()} min-h-24`}
          rows={3}
          value={nota}
          onChange={(e) => setNota(e.target.value)}
          placeholder="Cosa ha compiuto il personaggio"
        />
      </LabeledField>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      {esito ? <p className="text-sm text-lime-300">{esito}</p> : null}

      <button
        type="button"
        onClick={accredita}
        disabled={saving || !eventoId || !missioneId || !personaggioId}
        className="min-h-11 w-full rounded-lg bg-violet-700 px-4 text-sm font-bold text-white hover:bg-violet-600 disabled:opacity-40 sm:w-auto"
      >
        {saving ? 'Accredito…' : 'Accredita soluzione'}
      </button>
    </section>
  );
}
