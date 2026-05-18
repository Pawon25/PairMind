import React, { useEffect, useRef } from 'react';
import { useNegotiationStream } from '../hooks/useNegotiationStream';

import StatusBanner from './StatusBanner';
import ChatBubble from './ChatBubble';
import DealStatePanel from './DealStatePanel';
import IntermediateStep from './IntermediateStep';
import '../styles/NegotiateView.css';

export default function NegotiateView({ sessionId }) {
  const { turns, dealState, status, summary, isProcessing } = useNegotiationStream(sessionId);
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns, isProcessing]);

  return (
    <div className="neg-layout">
      <div className="neg-topbar">
        <div className="neg-topbar-left">
          <span className="neg-session">Session <code>{sessionId?.slice(0,8)}</code></span>
        </div>
        <StatusBanner status={status} />
      </div>

      <div className="neg-body">
        <div className="neg-feed">
          {turns.length === 0 && !isProcessing && (
            <div className="neg-empty">Negotiation starting…</div>
          )}
          {turns.map((turn) => (
            <ChatBubble key={turn.turn} turn={turn} />
          ))}
          {isProcessing && <IntermediateStep turns={turns} />}
          <div ref={bottomRef} />
        </div>

        <aside className="neg-sidebar">
          <DealStatePanel
            dealState={dealState}
            turnCount={turns.length}
            summary={summary}
          />
        </aside>
      </div>
    </div>
  );
}