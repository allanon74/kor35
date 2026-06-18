const STORY_TTL_MS = 24 * 60 * 60 * 1000;

/** Timestamp scadenza effettiva (fallback: created_at + 24h). */
export function storyExpiresAtMs(story) {
  if (story?.expires_at) return new Date(story.expires_at).getTime();
  if (story?.created_at) return new Date(story.created_at).getTime() + STORY_TTL_MS;
  return 0;
}

export function isStoryActive(story, nowMs = Date.now()) {
  const exp = storyExpiresAtMs(story);
  return exp > nowMs;
}
