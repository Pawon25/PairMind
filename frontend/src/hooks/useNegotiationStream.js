import { useState, useEffect, useRef } from 'react';
import { getStreamUrl } from '../api/index';

export function useNegotiationStream(sessionId) {
  const [turns, setTurns]               = useState([]);
  const [dealState, setDealState]       = useState(null);
  const [status, setStatus]             = useState('NEGOTIATING');
  const [summary, setSummary]           = useState(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const doneRef = useRef(false);

  useEffect(() => {
    if (!sessionId) return;

    const url = getStreamUrl(sessionId);
    console.log('[SSE] Connecting to:', url);

    const es = new EventSource(url);

    const handleParsed = (parsed) => {
      switch (parsed.type) {
        case 'turn':
          setTurns((prev) => {
            if (prev.find((t) => t.turn === parsed.turn)) return prev;
            return [...prev, parsed];
          });
          if (parsed.payload) setDealState(parsed.payload);
          setIsProcessing(true);
          break;

        case 'summary':
          setSummary(parsed);
          setStatus(parsed.outcome || 'AGREEMENT');
          setIsProcessing(false);
          break;

        case 'error':
          // Backend error mid-negotiation — stop spinner, keep turns visible
          console.error('[SSE] Backend error:', parsed.message);
          setIsProcessing(false);
          // Don't override a terminal status (AGREEMENT etc) if summary already came
          setStatus((prev) => prev === 'NEGOTIATING' ? 'ERROR' : prev);
          break;

        case 'done':
          console.log('[SSE] done received');
          doneRef.current = true;
          setIsProcessing(false);
          es.close();
          break;

        default:
          console.warn('[SSE] Unknown event type:', parsed.type);
      }
    };

    // All events come as unnamed messages from this backend
    es.onmessage = (e) => {
      console.log('[SSE] message:', e.data);
      try {
        const parsed = JSON.parse(e.data);
        handleParsed(parsed);
      } catch (err) {
        console.warn('[SSE] parse error:', err, e.data);
      }
    };

    // Also listen to named events in case backend adds them later
    es.addEventListener('turn',    (e) => { try { handleParsed(JSON.parse(e.data)); } catch (_) {} });
    es.addEventListener('summary', (e) => { try { handleParsed(JSON.parse(e.data)); } catch (_) {} });
    es.addEventListener('done',    (e) => { try { handleParsed({ type: 'done' });   } catch (_) {} });
    es.addEventListener('error',   (e) => { try { handleParsed(JSON.parse(e.data)); } catch (_) {} });

    es.onopen  = () => console.log('[SSE] opened');
    es.onerror = () => {
      if (!doneRef.current && es.readyState === EventSource.CLOSED) {
        setStatus((prev) => prev === 'NEGOTIATING' ? 'ERROR' : prev);
        setIsProcessing(false);
      }
    };

    return () => { es.close(); };
  }, [sessionId]);

  return { turns, dealState, status, summary, isProcessing };
}