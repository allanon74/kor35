/** Dati finti per controllare il layout 800×480 senza backend (`?preview=layout`). */

const COLORI = [
  ['c0', '0C2', 'Rosso', 3, 2],
  ['c1', '0C4', 'Blu', 2, 4],
  ['c2', '0C5', 'Giallo', 1, 5],
  ['c3', '0C3', 'Verde', 4, 3],
];

export const PREVIEW_COMPATTATORE = {
  abilitato: true,
  operativo: true,
  operazione_disponibile: true,
  quantico_abilitato: true,
  quantico_disponibile: true,
  energia_accumulata: 6,
  energia_soglia_operazione: 9,
  livello_energia: 2,
  puo_energizzare_minimo: true,
  nave_ferma: true,
  sintesi_carburante: {
    formula: { eta_base: 0.42, eta_per_livello: 0.07 },
    carburante_attuale: 640,
    carburante_massimo: 1000,
  },
  stiva: {
    righe: COLORI.map(([id, sigla, nome, qty, indice]) => ({
      mattone_id: id,
      indice_componente: indice,
      nome,
      colore_id: id,
      colore_nome: nome,
      colore_sigla: sigla,
      quantita: qty,
    })),
    coppie_opposite: [
      {
        id: 'p1',
        colore_a: { id: 'c0', nome: 'Rosso', sigla: '0C2', quantita: 3 },
        colore_b: { id: 'c2', nome: 'Giallo', sigla: '0C5', quantita: 1 },
        tick_coesistenza: 4,
        tick_coesistenza_max: 5,
        entrambi_presenti: true,
      },
      {
        id: 'p2',
        colore_a: { id: 'c1', nome: 'Blu', sigla: '0C4', quantita: 2 },
        colore_b: { id: 'c3', nome: 'Verde', sigla: '0C3', quantita: 4 },
        tick_coesistenza: 1,
        tick_coesistenza_max: 5,
        entrambi_presenti: true,
      },
    ],
  },
};

export const PREVIEW_SCIENTIFICA = {
  abilitato: true,
  sessione_attiva: true,
  evento_pending: true,
  defcon: 2,
  spettrografia: {
    evento_nome: 'Velo ionico',
    evento_descrizione: 'Distorsione di campo sul quadrante prodiero.',
    firma_spettrale: [
      { gruppo: 'Ionico', intensita: 72, colore: '#42a5f5' },
      { gruppo: 'Termico', intensita: 41, colore: '#ff8a65' },
      { gruppo: 'Esotico', intensita: 18, colore: '#ce93d8' },
    ],
    rischio_ca: {
      livello: 'elevato',
      etichetta: 'Rischio elevato',
      descrizione: 'Una soluzione parziale non chiude l’evento.',
    },
    stato_soluzione: {
      etichetta: 'Aperto',
      descrizione: 'Nessun codice confermato.',
    },
    cronometro: { ticks_rimanenti: 6, secondi_fino_prossima_valutazione: 18 },
    scan_profondo: null,
  },
  scan_profondo: {
    abilitato: true,
    disponibile: true,
    scans_rimanenti_volo: 2,
    stiva: {
      righe: COLORI.map(([id, sigla, nome, qty, indice]) => ({
        mattone_id: id,
        indice_componente: indice,
        nome,
        colore_sigla: sigla,
        quantita: qty,
      })),
    },
  },
  matrice: {
    coerenza: 42,
    coerenza_cap: 100,
    carica_intervento: 70,
    carica_intervento_soglia: 100,
    carica_pronta: false,
    energia_esotici_per_tick: 3,
    risonanza_tripla: false,
    esotici_alimentano_coerenza: true,
    nuclei: [
      { codice: 'R', nome: 'Temporale', online: true, livello: 2, energia_per_tick: 1, fase: 1 },
      { codice: 'S', nome: 'Dimensionale', online: true, livello: 1, energia_per_tick: 1, fase: 0 },
      { codice: 'T', nome: 'Paradossi', online: false, livello: 0, energia_per_tick: 0, fase: 2 },
    ],
  },
  interventi: {
    abilitati: true,
    interventi_rimanenti_volo: 2,
    catalogo: [
      {
        tipo: 'smorzamento',
        label: 'Smorzamento',
        descrizione: 'Riduce la deriva del fenomeno corrente.',
        coerenza: 20,
        componenti: 0,
        disponibile: true,
        motivo_indisponibile: '',
      },
      {
        tipo: 'campione',
        label: 'Campione di campo',
        descrizione: 'Consuma un componente per stabilizzare la firma.',
        coerenza: 10,
        componenti: 1,
        disponibile: true,
        motivo_indisponibile: '',
      },
    ],
  },
};

export const PREVIEW_STATION = {
  ingegneria: {
    id: 'ingegneria',
    nome: 'Console Ingegneria',
    enabled: true,
    login_required: true,
    sigla: '0IN',
    requisito: '0IN > 0',
    screen: 'compattatore',
  },
  scientifica: {
    id: 'scientifica',
    nome: 'Console Scientifica',
    enabled: true,
    login_required: true,
    sigla: '0SC',
    requisito: '0SC > 0',
    screen: 'scientifica',
  },
  comunicazioni: {
    id: 'comunicazioni',
    nome: 'Console Comunicazioni',
    enabled: true,
    login_required: true,
    sigla: '0CO',
    requisito: '0CO > 0',
    screen: 'comunicazioni',
  },
};
