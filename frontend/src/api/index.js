import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL

export const ACCESS_TOKEN_KEY = 'pm_access_token';

// Attach the gate token (set by the landing page after a successful
// /auth/verify-token) to every request automatically.
axios.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// A 401 here means the token is missing/expired/exhausted - bounce back to
// the gate page rather than leaving the user stuck on a broken /app.
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      sessionStorage.removeItem(ACCESS_TOKEN_KEY);
      window.location.href = '/?expired=1';
    }
    return Promise.reject(error);
  }
);

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