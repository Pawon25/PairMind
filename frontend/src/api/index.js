import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL

/**
 * Upload a document with a tag, scoped to this browser session's corpus.
 * Returns { doc_id }
 */
export async function uploadDocument(file, tag, sessionId) {
  const form = new FormData();
  form.append('file', file);
  form.append('tag', tag);
  form.append('session_id', sessionId);
  const { data } = await axios.post(`${BASE}/upload`, form);
  return data;
}

/**
 * Start a negotiation for this session's already-uploaded documents.
 * Returns { session_id }
 */
export async function startNegotiation(sessionId) {
  const form = new FormData();
  form.append('session_id', sessionId);
  const { data } = await axios.post(`${BASE}/negotiate`, form);
  return data;
}

/**
 * Clear this session's staged/indexed documents (not the whole shared index).
 */
export async function resetSession(sessionId) {
  const form = new FormData();
  form.append('session_id', sessionId);
  await axios.post(`${BASE}/reset`, form);
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