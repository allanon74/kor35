/** API Rubriche InstaFame — percorsi relativi (compatibili edge/offline). */
import { fetchAuthenticated } from './core';

const conPersonaggio = (personaggioId, extra = {}) => {
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  Object.entries(extra).forEach(([chiave, valore]) => {
    if (valore != null && valore !== '') params.set(chiave, String(valore));
  });
  const qs = params.toString();
  return qs ? `?${qs}` : '';
};

export const getRubriche = (personaggioId, onLogout) =>
  fetchAuthenticated(`/api/social/rubriche/${conPersonaggio(personaggioId)}`, { method: 'GET' }, onLogout);

export const createRubrica = (payload, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche/${conPersonaggio(personaggioId)}`,
    { method: 'POST', body: JSON.stringify(payload) },
    onLogout
  );

export const updateRubrica = (rubricaId, payload, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche/${rubricaId}/${conPersonaggio(personaggioId)}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
    onLogout
  );

export const deleteRubrica = (rubricaId, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche/${rubricaId}/${conPersonaggio(personaggioId)}`,
    { method: 'DELETE' },
    onLogout
  );

export const getPermessiRubrica = (rubricaId, onLogout) =>
  fetchAuthenticated(`/api/social/rubriche/${rubricaId}/permessi/`, { method: 'GET' }, onLogout);

export const concediPermessoRubrica = (rubricaId, personaggioTargetId, note, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche/${rubricaId}/permessi/`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId, note: note || '' }) },
    onLogout
  );

export const revocaPermessoRubrica = (rubricaId, permessoId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche/${rubricaId}/permessi/${permessoId}/`,
    { method: 'DELETE' },
    onLogout
  );

export const sincronizzaWikiRubrica = (rubricaId, onLogout) =>
  fetchAuthenticated(`/api/social/rubriche/${rubricaId}/wiki-sync/`, { method: 'POST' }, onLogout);

export const getArticoli = (personaggioId, onLogout, options = {}) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${conPersonaggio(personaggioId, {
      rubrica: options.rubricaId,
      stato: options.stato,
      page: options.page,
      page_size: options.pageSize,
    })}`,
    { method: 'GET' },
    onLogout
  );

export const getArticolo = (articoloId, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/${conPersonaggio(personaggioId)}`,
    { method: 'GET' },
    onLogout
  );

export const createArticolo = (formData, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${conPersonaggio(personaggioId)}`,
    { method: 'POST', body: formData },
    onLogout
  );

export const updateArticolo = (articoloId, formData, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/${conPersonaggio(personaggioId)}`,
    { method: 'PATCH', body: formData },
    onLogout
  );

export const deleteArticolo = (articoloId, personaggioId, onLogout, { eliminaAnnuncio = false } = {}) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/${conPersonaggio(personaggioId, {
      elimina_annuncio: eliminaAnnuncio ? '1' : '',
    })}`,
    { method: 'DELETE' },
    onLogout
  );

export const creaPostAnnuncio = (articoloId, payload, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/post-annuncio/${conPersonaggio(personaggioId)}`,
    { method: 'POST', body: JSON.stringify(payload || {}) },
    onLogout
  );

export const eliminaPostAnnuncio = (articoloId, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/post-annuncio/${conPersonaggio(personaggioId)}`,
    { method: 'DELETE' },
    onLogout
  );

export const toggleLikeArticolo = (articoloId, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/like/${conPersonaggio(personaggioId)}`,
    { method: 'POST' },
    onLogout
  );

export const getCommentiArticolo = (articoloId, personaggioId, onLogout, page = 1, pageSize = 10) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/comments/${conPersonaggio(personaggioId, {
      page,
      page_size: pageSize,
    })}`,
    { method: 'GET' },
    onLogout
  );

export const creaCommentoArticolo = (articoloId, testo, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/comments/${conPersonaggio(personaggioId)}`,
    { method: 'POST', body: JSON.stringify({ testo }) },
    onLogout
  );

export const aggiornaCommentoArticolo = (articoloId, commentoId, testo, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/comments/${commentoId}/${conPersonaggio(personaggioId)}`,
    { method: 'PATCH', body: JSON.stringify({ testo }) },
    onLogout
  );

export const eliminaCommentoArticolo = (articoloId, commentoId, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/comments/${commentoId}/${conPersonaggio(personaggioId)}`,
    { method: 'DELETE' },
    onLogout
  );

export const toggleLikeCommentoArticolo = (articoloId, commentoId, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/social/rubriche-articoli/${articoloId}/comments/${commentoId}/like/${conPersonaggio(personaggioId)}`,
    { method: 'POST' },
    onLogout
  );
