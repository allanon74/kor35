/** API Instafame / social — importa il client da ./core. */
import { fetchAuthenticated, fetchPublic } from './core';

export const socialGetPosts = (personaggioId, onLogout, page = 1, pageSize = 30, options = {}) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  if (options?.hashtag) params.set('hashtag', String(options.hashtag).replace(/^#/, ''));
  return fetchAuthenticated(`/api/social/posts/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreatePost = (formData, personaggioId, onLogout) => {
  const endpoint = `/api/social/posts/${personaggioId ? `?personaggio_id=${personaggioId}` : ''}`;
  return fetchAuthenticated(endpoint, { method: 'POST', body: formData }, onLogout);
};

export const socialToggleLike = (postId, personaggioId, onLogout) => {
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  const qs = params.toString();
  return fetchAuthenticated(
    `/api/social/posts/${postId}/like/${qs ? `?${qs}` : ''}`,
    {
      method: 'POST',
      body: personaggioId != null && personaggioId !== '' ? JSON.stringify({ personaggio_id: personaggioId }) : undefined,
    },
    onLogout
  );
};

export const socialToggleCommentLike = (postId, commentId, personaggioId, onLogout) => {
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  const qs = params.toString();
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${commentId}/like/${qs ? `?${qs}` : ''}`,
    {
      method: 'POST',
      body: personaggioId != null && personaggioId !== '' ? JSON.stringify({ personaggio_id: personaggioId }) : undefined,
    },
    onLogout
  );
};

export const socialGetComments = (postId, personaggioId, onLogout, page = 1, pageSize = 10) => {
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/posts/${postId}/comments/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateComment = (postId, testo, personaggioId, onLogout) => {
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${personaggioId ? `?personaggio_id=${personaggioId}` : ''}`,
    { method: 'POST', body: JSON.stringify({ testo }) },
    onLogout
  );
};

export const socialUpdateComment = (postId, commentId, testo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${commentId}/${qp}`,
    { method: 'PATCH', body: JSON.stringify({ testo }) },
    onLogout
  );
};

export const socialDeleteComment = (postId, commentId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${commentId}/${qp}`,
    { method: 'DELETE' },
    onLogout
  );
};

export const socialGetMyProfile = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/profile/me/${qp}`, { method: 'GET' }, onLogout);
};

function formDataHasUpload(fd) {
  for (const value of fd.values()) {
    if (value instanceof Blob) return true;
  }
  return false;
}

function formDataToPlainObject(fd) {
  const out = {};
  for (const [key, value] of fd.entries()) {
    if (value instanceof Blob) continue;
    out[key] = String(value);
  }
  return out;
}

/**
 * Aggiorna profilo InstaFame.
 * - Oggetto plain o FormData senza file → JSON PATCH (UTF-8, emoji nel nickname/descrizione).
 * - FormData con file → multipart PATCH (solo upload foto).
 */
export const socialUpdateMyProfile = (payload, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  const endpoint = `/api/social/profile/me/${qp}`;

  if (payload instanceof FormData) {
    if (formDataHasUpload(payload)) {
      return fetchAuthenticated(endpoint, { method: 'PATCH', body: payload }, onLogout);
    }
    return fetchAuthenticated(
      endpoint,
      { method: 'PATCH', body: JSON.stringify(formDataToPlainObject(payload)) },
      onLogout
    );
  }

  return fetchAuthenticated(
    endpoint,
    { method: 'PATCH', body: JSON.stringify(payload || {}) },
    onLogout
  );
};

export const socialGetKorpList = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/korp/', { method: 'GET' }, onLogout);
};

export const socialGetProfileByCharacter = (personaggioId, onLogout) => {
  return fetchAuthenticated(`/api/social/profiles/${personaggioId}/`, { method: 'GET' }, onLogout);
};

export const socialGetPublicPostBySlug = (slug) => {
  return fetchPublic(`/api/social/public/posts/${slug}/`);
};

export const socialUpdatePost = (postId, formData, onLogout) => {
  return fetchAuthenticated(`/api/social/posts/${postId}/`, { method: 'PATCH', body: formData }, onLogout);
};

export const socialDeletePost = (postId, onLogout) => {
  return fetchAuthenticated(`/api/social/posts/${postId}/`, { method: 'DELETE' }, onLogout);
};

export const socialGetStaffEventReport = (eventoId, onLogout) => {
  const qp = eventoId ? `?evento_id=${eventoId}` : '';
  return fetchAuthenticated(`/api/social/staff/event-report/${qp}`, { method: 'GET' }, onLogout);
};

export const socialGetNotifications = (personaggioId, onLogout, options = {}) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  if (options.limit) params.set('limit', String(options.limit));
  if (options.since) params.set('since', String(options.since));
  const qs = params.toString();
  return fetchAuthenticated(`/api/social/notifications/${qs ? `?${qs}` : ''}`, { method: 'GET' }, onLogout);
};

export const socialGetGroups = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${qp}`, { method: 'GET' }, onLogout);
};

export const socialCreateGroup = (payload, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${qp}`, { method: 'POST', body: JSON.stringify(payload) }, onLogout);
};

export const socialRequestJoinGroup = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/request_join/${qp}`, { method: 'POST' }, onLogout);
};

export const socialGetGroupPosts = (groupId, personaggioId, onLogout, page = 1, pageSize = 10) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateGroupPost = (groupId, formData, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/${qp}`, { method: 'POST', body: formData }, onLogout);
};

export const socialUpdateGroupPost = (groupId, postId, formData, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/${postId}/${qp}`, { method: 'PATCH', body: formData }, onLogout);
};

export const socialDeleteGroupPost = (groupId, postId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/${postId}/${qp}`, { method: 'DELETE' }, onLogout);
};

export const socialGetGroupMessages = (groupId, personaggioId, onLogout, page = 1, pageSize = 20) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/groups/${groupId}/messages/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateGroupMessage = (groupId, testo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/messages/${qp}`,
    { method: 'POST', body: JSON.stringify({ testo }) },
    onLogout
  );
};

export const socialDeleteGroupMessage = (groupId, messageId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/messages/${messageId}/${qp}`, { method: 'DELETE' }, onLogout);
};

export const socialGetGroupMembers = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/members/${qp}`, { method: 'GET' }, onLogout);
};

export const socialInviteGroupMember = (groupId, personaggioTargetId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/invite/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId }) },
    onLogout
  );
};

export const socialApproveGroupMember = (groupId, personaggioTargetId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/approve_member/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId }) },
    onLogout
  );
};

export const socialRejectGroupMember = (groupId, personaggioTargetId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/reject_member/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId }) },
    onLogout
  );
};

export const socialSetGroupMemberRole = (groupId, personaggioTargetId, ruolo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/set_member_role/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId, ruolo }) },
    onLogout
  );
};

export const socialAcceptGroupInvite = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/accept_invite/${qp}`, { method: 'POST' }, onLogout);
};

export const socialDeclineGroupInvite = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/decline_invite/${qp}`, { method: 'POST' }, onLogout);
};

export const socialLeaveGroup = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/leave/${qp}`, { method: 'POST' }, onLogout);
};

// --- SOCIAL STORIES ---
export const socialGetStories = (personaggioId, onLogout, page = 1, pageSize = 50) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/stories/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateStory = (formData, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${qp}`, { method: 'POST', body: formData }, onLogout);
};

export const socialMarkStoryViewed = (storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${storyId}/viewed/${qp}`, { method: 'POST' }, onLogout);
};

export const socialReactStory = (storyId, emoji, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/${storyId}/react/${qp}`,
    { method: 'POST', body: JSON.stringify({ emoji }) },
    onLogout
  );
};

export const socialGetStoryReplies = (storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${storyId}/replies/${qp}`, { method: 'GET' }, onLogout);
};

export const socialReplyStory = (storyId, testo, sendDm = true, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/${storyId}/replies/${qp}`,
    { method: 'POST', body: JSON.stringify({ testo, send_dm: !!sendDm }) },
    onLogout
  );
};

export const socialGetHighlights = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/highlights/${qp}`, { method: 'GET' }, onLogout);
};

export const socialCreateHighlight = (titolo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/create_highlight/${qp}`,
    { method: 'POST', body: JSON.stringify({ titolo }) },
    onLogout
  );
};

export const socialAddStoryToHighlight = (highlightId, storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/highlights/${highlightId}/add/${qp}`,
    { method: 'POST', body: JSON.stringify({ story_id: storyId }) },
    onLogout
  );
};

export const socialGetMyStoryActivity = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/my_activity/${qp}`, { method: 'GET' }, onLogout);
};

export const socialGetMyStoryHistory = (personaggioId, onLogout, includeExpired = true) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('include_expired', includeExpired ? 'true' : 'false');
  return fetchAuthenticated(`/api/social/stories/my_history/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialConvertStoryToPost = (storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${storyId}/convert_to_post/${qp}`, { method: 'POST' }, onLogout);
};

// --- Funzioni API specifiche ---

/**
 * Recupera la configurazione degli slot corporei (costanti).
 * Utile se vuoi popolarli dinamicamente, altrimenti usiamo costanti nel frontend.
 */
