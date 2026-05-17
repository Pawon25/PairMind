import { useState, useEffect, useRef } from 'react';
import { getStreamUrl } from '../api/index';

/**
 * Consumes the SSE stream for a negotiation session.
 *
 * Returns:
 *   turns        — array of turn event objects
 *   dealState    — latest DealTerms payload
 *   status       — 'NEGOTIATING' | 'AGREEMENT' | 'WALK_AWAY' | 'DEADLOCK' | 'TIMEOUT' | 'ERROR'
 *   summary      — final summary object (or null)
 *   isProcessing — true while waiting for next agent turn
 */
export function useNegotiationStream(sessionId) {
  const [turns, setTurns]             = useState([]);
  const [dealState, setDealState]     = useState(null);
  const [status, setStatus]           = useState('NEGOTIATING');
  const [summary, setSummary]         = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const esRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;

    const url = getStreamUrl(sessionId);
    const es = new EventSource(url);
    esRef.current = es;

    setIsProcessing(true);

    es.addEventListener('turn', (e) => {
      const turn = JSON.parse(e.data);
      setTurns((prev) => {
        // dedup by turn number
        if (prev.find((t) => t.turn === turn.turn)) return prev;
        return [...prev, turn];
      });
      if (turn.payload) setDealState(turn.payload);
      setIsProcessing(true); // waiting for next
    });

    es.addEventListener('summary', (e) => {
      const data = JSON.parse(e.data);
      setSummary(data);
      setStatus(data.outcome || 'AGREEMENT');
      setIsProcessing(false);
    });

    es.addEventListener('done', () => {
      setIsProcessing(false);
      es.close();
    });

    es.addEventListener('error', (e) => {
      try {
        const data = JSON.parse(e.data);
        console.error('SSE error event:', data);
      } catch (_) {}
      setStatus('ERROR');
      setIsProcessing(false);
      es.close();
    });

    es.onerror = () => {
      // connection error — only flag if not already done
      setStatus((prev) => prev === 'NEGOTIATING' ? 'ERROR' : prev);
      setIsProcessing(false);
    };

    return () => { es.close(); };
  }, [sessionId]);

  return { turns, dealState, status, summary, isProcessing };
}