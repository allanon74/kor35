import React, { useState } from 'react';
import CardFrame from './CardFrame';

function cartaDaSnapshot(meta, cpId) {
  if (!meta) return { id: cpId, nome: 'Carta', tipo: 'PG', energia: 'MAR' };
  return {
    id: cpId,
    nome: meta.nome,
    tipo: meta.tipo,
    energia: meta.energia,
    rarita: meta.rarita,
    costo_gioco: meta.costo_gioco,
    attacco: meta.attacco,
    salute: meta.salute,
    iniziativa: meta.iniziativa,
    testo_gioco: meta.testo_gioco,
    immagine_url: meta.immagine_url,
    tags: meta.tags || [],
  };
}

function Pila({ label, count }) {
  return (
    <div className="flex h-16 w-12 flex-col items-center justify-center rounded border border-white/20 bg-black/50 text-[10px] font-bold text-gray-200">
      <span>{count ?? 0}</span>
      <span className="font-normal text-gray-400">{label}</span>
    </div>
  );
}

function SlotEroe({
  titolo,
  cpId,
  meta,
  pv,
  guscio,
  esaurito,
  leader,
  oggettoNome,
  selezionato,
  evidenziato,
  onClick,
  keywords,
  tagsGlossary,
  temaEnergie,
}) {
  return (
    <div className="flex w-[118px] flex-col items-center gap-1">
      <p className="text-[10px] uppercase tracking-wide text-gray-400">{titolo}</p>
      <button
        type="button"
        onClick={onClick}
        disabled={!onClick}
        className={`relative rounded-xl ${evidenziato ? 'ring-2 ring-amber-300' : ''} ${selezionato ? 'ring-2 ring-red-400' : ''} ${onClick ? '' : 'cursor-default'}`}
      >
        {cpId ? (
          <div className={esaurito ? 'opacity-60' : ''}>
            <CardFrame
              carta={cartaDaSnapshot(meta, cpId)}
              size="sm"
              compact
              showRules={false}
              keywords={keywords}
              tagsGlossary={tagsGlossary}
              temaEnergie={temaEnergie}
            />
          </div>
        ) : (
          <div className="flex h-[152px] w-[108px] items-center justify-center rounded-xl border border-dashed border-white/20 bg-black/30 text-[10px] text-gray-500">
            vuoto
          </div>
        )}
        {cpId && (
          <span className="absolute -right-1 -top-1 rounded bg-rose-900 px-1 text-[10px] font-black text-white">
            {pv ?? '—'}
          </span>
        )}
      </button>
      <p className="min-h-[1.6rem] text-center text-[9px] text-gray-400">
        {leader ? 'Leader · ' : ''}
        {esaurito ? 'esaurito · ' : ''}
        {guscio > 0 ? `guscio ${guscio} · ` : ''}
        {oggettoNome || ''}
      </p>
    </div>
  );
}

export default function TavoloDuello({
  duello,
  charId,
  busy,
  onAzione,
  keywords = [],
  tagsGlossary = [],
  temaEnergie,
  abilita = [],
}) {
  const [manoSel, setManoSel] = useState(null);
  const [attaccante, setAttaccante] = useState(null);

  const mioId = String(charId);
  const avversarioId = duello?.sfidante?.id === charId
    ? duello?.sfidato?.id
    : duello?.sfidante?.id;
  const mioCampo = duello?.stato_gioco?.campo?.[mioId] || {};
  const campoAvv = avversarioId
    ? (duello?.stato_gioco?.campo?.[String(avversarioId)] || {})
    : {};
  const mano = duello?.stato_gioco?.mani?.[mioId] || [];
  const carte = duello?.carte || {};
  const terra = duello?.stato_gioco?.terra_condivisa;
  const terraId = terra?.carta_posseduta_id || null;
  const mieiEroi = mioCampo.eroi || [null, null];
  const eroiAvv = campoAvv.eroi || [null, null];
  const esauriti = mioCampo.eroi_esauriti || [false, false];
  const isLeader = mioCampo.eroi_is_leader || [false, false];
  const isLeaderAvv = campoAvv.eroi_is_leader || [false, false];
  const fase = mioCampo.fase_turno || 'APE';
  const mioTurno = duello?.turno_personaggio_id === charId;
  const vitaMia = duello?.mio_ruolo === 'sfidato' ? duello.influenza_sfidato : duello.influenza_sfidante;
  const vitaAvv = duello?.mio_ruolo === 'sfidato' ? duello.influenza_sfidante : duello.influenza_sfidato;
  const nomeAvv = duello?.mio_ruolo === 'sfidante' ? duello?.sfidato?.nome : duello?.sfidante?.nome;
  const flags = mioCampo.turno_flags || {};
  const permanenteGiocato = !!flags.permanente_giocato;
  const effettoGiocato = !!flags.effetto_giocato;
  const inCombattimento = fase === 'COM';
  const inChiusura = fase === 'CHI';
  const difensore = campoAvv.difensore_slot;
  const metaMano = manoSel ? carte[manoSel] : null;

  const puoGiocare = (meta) => {
    if (!mioTurno || busy || inCombattimento || !meta) return false;
    if ((mioCampo.energia ?? 0) < (meta.costo_gioco ?? 0)) return false;
    if (meta.tipo === 'EVT') return !effettoGiocato;
    return !permanenteGiocato;
  };

  const giocaSu = (slot) => {
    if (!manoSel || !metaMano) return;
    if (metaMano.tipo === 'PG' || metaMano.tipo === 'OGG') {
      onAzione('gioca_carta', { carta_posseduta_id: manoSel, slot_eroe: slot });
    }
    setManoSel(null);
    setAttaccante(null);
  };

  const slotGiocabile = (slot) => {
    if (!puoGiocare(metaMano)) return false;
    if (metaMano.tipo === 'PG') return !mieiEroi[slot];
    if (metaMano.tipo === 'OGG') return !!mieiEroi[slot] && !(mioCampo.oggetti || {})[String(slot)];
    return false;
  };

  const attacca = (bersaglio) => {
    if (attaccante == null) return;
    const payload = { slot_eroe: attaccante };
    if (bersaglio != null) payload.bersaglio_eroe_slot = bersaglio;
    onAzione('attacca', payload);
    setAttaccante(null);
    setManoSel(null);
  };

  const puoAttaccareSlot = (slot) => (
    mioTurno && !busy && !inChiusura && mieiEroi[slot] && !esauriti[slot] && !duello.effect_pending
  );

  const passaLabel = fase === 'APE' ? 'Combattimento' : fase === 'COM' ? 'Chiusura' : 'Passa turno';

  return (
    <div className="overflow-hidden rounded-xl border border-emerald-900/60 bg-gradient-to-b from-emerald-950 via-gray-950 to-emerald-950 p-3">
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="font-bold text-white">{nomeAvv || 'Avversario'} · {vitaAvv ?? '—'} vita</span>
        <span className="text-gray-400">
          mana {campoAvv.energia ?? 0}/{campoAvv.mana_massimo ?? 3}
          {' · '}mano {campoAvv.mano_count ?? 0}
        </span>
      </div>

      <div className="mb-3 flex items-end justify-center gap-3">
        <Pila label="mazzo" count={campoAvv.mazzo_count} />
        {[0, 1].map((slot) => (
          <SlotEroe
            key={`avv-${slot}`}
            titolo={isLeaderAvv[slot] ? 'Leader' : `Eroe ${slot}`}
            cpId={eroiAvv[slot]}
            meta={carte[eroiAvv[slot]]}
            pv={(campoAvv.salute_eroi || [])[slot]}
            guscio={(campoAvv.guscio_eroi || [])[slot] || 0}
            esaurito={(campoAvv.eroi_esauriti || [])[slot]}
            leader={isLeaderAvv[slot]}
            oggettoNome={carte[(campoAvv.oggetti || {})[String(slot)]]?.nome}
            evidenziato={attaccante != null && eroiAvv[slot] && (difensore == null || difensore === slot)}
            onClick={attaccante != null && eroiAvv[slot] && (difensore == null || difensore === slot)
              ? () => attacca(slot)
              : undefined}
            keywords={keywords}
            tagsGlossary={tagsGlossary}
            temaEnergie={temaEnergie}
          />
        ))}
        <Pila label="scarto" count={campoAvv.scarto_count} />
      </div>

      <div className="mb-3 flex flex-col items-center">
        <p className="mb-1 text-[10px] uppercase tracking-wide text-emerald-200/80">Terra</p>
        <button
          type="button"
          disabled={!slotGiocabileTerra(metaMano, permanenteGiocato, puoGiocare)}
          onClick={() => {
            if (metaMano?.tipo === 'LUO') {
              onAzione('gioca_carta', { carta_posseduta_id: manoSel });
              setManoSel(null);
            }
          }}
          className={`rounded-xl ${metaMano?.tipo === 'LUO' && puoGiocare(metaMano) ? 'ring-2 ring-amber-300' : ''}`}
        >
          {terraId ? (
            <CardFrame
              carta={cartaDaSnapshot(carte[terraId], terraId)}
              size="sm"
              compact
              showRules={false}
              keywords={keywords}
              tagsGlossary={tagsGlossary}
              temaEnergie={temaEnergie}
            />
          ) : (
            <div className="flex h-[152px] w-[108px] items-center justify-center rounded-xl border border-dashed border-emerald-800/70 text-[10px] text-emerald-200/50">
              nessuna terra
            </div>
          )}
        </button>
      </div>

      <div className="mb-2 flex items-center justify-between text-xs">
        <span className={mioTurno ? 'font-bold text-amber-200' : 'text-gray-400'}>
          {mioTurno ? 'Tuo turno' : 'Turno avversario'} · {mioCampo.fase_turno_label || 'Apertura'}
          {mioCampo.turno_numero ? ` · turno ${mioCampo.turno_numero}` : ''}
        </span>
        <span className="font-bold text-white">Tu · {vitaMia ?? '—'} vita · mana {mioCampo.energia ?? 0}/{mioCampo.mana_massimo ?? 3}</span>
      </div>
      {(mioCampo.bonus_leader || []).length > 0 && (
        <p className="mb-2 text-center text-[10px] text-amber-200/90">{mioCampo.bonus_leader.join(' · ')}</p>
      )}

      <div className="mb-3 flex items-end justify-center gap-3">
        <Pila label="mazzo" count={mioCampo.mazzo_count} />
        {[0, 1].map((slot) => (
          <SlotEroe
            key={`mio-${slot}`}
            titolo={isLeader[slot] ? 'Leader' : `Eroe ${slot}`}
            cpId={mieiEroi[slot]}
            meta={carte[mieiEroi[slot]]}
            pv={(mioCampo.salute_eroi || [])[slot]}
            guscio={(mioCampo.guscio_eroi || [])[slot] || 0}
            esaurito={esauriti[slot]}
            leader={isLeader[slot]}
            oggettoNome={carte[(mioCampo.oggetti || {})[String(slot)]]?.nome}
            selezionato={attaccante === slot}
            evidenziato={slotGiocabile(slot)}
            onClick={() => {
              if (slotGiocabile(slot)) {
                giocaSu(slot);
                return;
              }
              if (puoAttaccareSlot(slot)) {
                setManoSel(null);
                setAttaccante(attaccante === slot ? null : slot);
              }
            }}
            keywords={keywords}
            tagsGlossary={tagsGlossary}
            temaEnergie={temaEnergie}
          />
        ))}
        <Pila label="scarto" count={mioCampo.scarto_count} />
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {mano.map((cpId) => {
          const meta = carte[cpId];
          const attiva = manoSel === cpId;
          return (
            <button
              key={cpId}
              type="button"
              disabled={busy || !mioTurno}
              onClick={() => {
                setAttaccante(null);
                setManoSel(attiva ? null : cpId);
              }}
              className={`shrink-0 rounded-xl ${attiva ? 'ring-2 ring-amber-300' : ''} ${!puoGiocare(meta) ? 'opacity-70' : ''}`}
            >
              <CardFrame
                carta={cartaDaSnapshot(meta, cpId)}
                size="sm"
                showRules={false}
                keywords={keywords}
                tagsGlossary={tagsGlossary}
                temaEnergie={temaEnergie}
              />
            </button>
          );
        })}
        {mano.length === 0 && <p className="text-xs text-gray-500">Mano vuota</p>}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
        {metaMano?.tipo === 'EVT' && puoGiocare(metaMano) && (
          <button
            type="button"
            className="rounded bg-indigo-800 px-2 py-1 font-bold"
            onClick={() => {
              onAzione('gioca_carta', { carta_posseduta_id: manoSel });
              setManoSel(null);
            }}
          >
            Gioca effetto
          </button>
        )}
        {attaccante != null && difensore == null && (
          <button
            type="button"
            className="rounded bg-red-900 px-2 py-1 font-bold"
            onClick={() => attacca(null)}
          >
            Attacca i punti vita
          </button>
        )}
        {mioTurno && (
          <button
            type="button"
            disabled={busy}
            className="rounded bg-gray-700 px-2 py-1"
            onClick={() => onAzione('passa')}
          >
            {passaLabel}
          </button>
        )}
        {mioTurno && !inChiusura && abilita.map((ab) => (
          <button
            key={`${ab.cpId}-${ab.index}-${ab.codice}`}
            type="button"
            disabled={busy}
            className="rounded bg-violet-900 px-2 py-1"
            onClick={() => onAzione('attiva_abilita', {
              carta_posseduta_id: ab.cpId,
              script_index: ab.index,
              script_codice: ab.codice || undefined,
            })}
          >
            {ab.nome}
          </button>
        ))}
        <span className="text-gray-500">
          {manoSel ? 'Scegli lo slot illuminato.' : attaccante != null ? 'Scegli il bersaglio.' : 'Tocca una carta in mano o un tuo eroe.'}
        </span>
      </div>
    </div>
  );
}

function slotGiocabileTerra(meta, permanenteGiocato, puoGiocare) {
  return meta?.tipo === 'LUO' && !permanenteGiocato && puoGiocare(meta);
}
