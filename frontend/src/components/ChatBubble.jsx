import React, { useState } from 'react';
import { BookOpen } from 'lucide-react';
import CitationModal from './CitationModal';
import '../styles/ChatBubble.css';

const MSG_TYPE_COLOR = {
  PROPOSE:   'blue',
  COUNTER:   'blue',
  ACCEPT:    'green',
  REJECT:    'red',
  WALK_AWAY: 'red',
};

export default function ChatBubble({ turn }) {
  const [activeCitation, setActiveCitation] = useState(null);

  const isBuyer = turn.agent_id === 'buyer';
  const color   = MSG_TYPE_COLOR[turn.msg_type] || 'slate';

  return (
    <>
      <div className={`bubble ${isBuyer ? 'bubble-buyer' : 'bubble-seller'}`}>
        <div className="bubble-meta">
          <span className={`bubble-agent agent-${isBuyer ? 'buyer' : 'seller'}`}>
            {isBuyer ? '🏢 Buyer' : '🏭 Seller'}
          </span>
          <span className={`badge badge-${color}`}>{turn.msg_type}</span>
          <span className="bubble-turn">Turn {turn.turn}</span>
        </div>

        {turn.payload && (
          <div className="bubble-terms">
            {turn.payload.unit_price    && <span className="term"><b>Price</b> ${turn.payload.unit_price}/unit</span>}
            {turn.payload.delivery_date && <span className="term"><b>Delivery</b> {turn.payload.delivery_date}</span>}
            {turn.payload.payment_terms && <span className="term"><b>Payment</b> {turn.payload.payment_terms}</span>}
          </div>
        )}

        <p className="bubble-rationale">{turn.rationale}</p>

        {turn.citations?.length > 0 && (
          <div className="bubble-citations">
            <BookOpen size={11} />
            {turn.citations.map((c, i) => (
              <button
                key={i}
                className="citation-chip"
                onClick={() => setActiveCitation(c)}
              >
                {c.source?.startsWith('http') ? 'Web' : c.source?.split('/').pop() || `ref ${i+1}`}
              </button>
            ))}
          </div>
        )}
      </div>

      {activeCitation && (
        <CitationModal citation={activeCitation} onClose={() => setActiveCitation(null)} />
      )}
    </>
  );
}