import axios from 'axios';

const BASE = 'http://localhost:8000';

/**
 * Upload a document with a tag.
 * Returns { doc_id }
 */
export async function uploadDocument(file, tag) {
  const form = new FormData();
  form.append('file', file);
  form.append('tag', tag);
  const { data } = await axios.post(`${BASE}/upload`, form);
  return data;
}

/**
 * Start a new negotiation session.
 * Returns { session_id }
 */
export async function startNegotiation() {
  const { data } = await axios.post(`${BASE}/negotiate`);
  return data;
}

/**
 * Get current deal state.
 * Returns NegotiationState JSON
 */
export async function getDealState(sessionId) {
  const { data } = await axios.get(`${BASE}/negotiate/${sessionId}/state`);
  return data;
}

/**
 * Get final summary after negotiation ends.
 */
export async function getSummary(sessionId) {
  const { data } = await axios.get(`${BASE}/negotiate/${sessionId}/summary`);
  return data;
}

/**
 * Returns the SSE stream URL for a session.
 */
export function getStreamUrl(sessionId) {
  return `${BASE}/negotiate/${sessionId}/stream`;
}