import React, { useState } from 'react';
// import { BookOpen } from 'lucide-react';
import CitationModal from './CitationModal';
import '../styles/ChatBubble.css';

const MSG_TYPE_COLOR = {
  PROPOSE:   'blue',
  COUNTER:   'blue',
  ACCEPT:    'green',
  REJECT:    'red',
  WALK_AWAY: 'red',
};

// Matches: (filename.md, Section X) or [filename.md, Section X] or (https://..., retrieved ...)
const CITATION_PATTERN = /(\(|\[)([A-Za-z0-9_-]+\.(?:md|pdf|docx|txt)|https?:\/\/[^\s,)\]]+)([^)\]]*?)(\)|\])/g;
function parseRationale(text, citations, onCitationClick) {
  if (!text) return null;

  const parts = [];
  let lastIndex = 0;
  let match;

  CITATION_PATTERN.lastIndex = 0;

  while ((match = CITATION_PATTERN.exec(text)) !== null) {
    // Push plain text before this match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const fullMatch = match[0];
    const inner = match[2] + match[3]; // filename + section

    // Try to find matching citation object
    const linked = citations?.find((c) =>
      inner.includes(c.source?.split('/').pop()) ||
      inner.includes(c.source)
    );

    parts.push(
      <span
        key={match.index}
        className={`inline-citation ${linked ? 'inline-citation-linked' : ''}`}
        onClick={linked ? () => onCitationClick(linked) : undefined}
        title={linked ? 'Click to view citation' : undefined}
      >
        {match[0]}
      </span>
    );

    lastIndex = match.index + fullMatch.length;
  }

  // Push remaining plain text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

export default function ChatBubble({ turn }) {
  const [activeCitation, setActiveCitation] = useState(null);

  const isBuyer = turn.agent_id === 'buyer';
  const color   = MSG_TYPE_COLOR[turn.msg_type] || 'slate';

  const parsedRationale = parseRationale(turn.rationale, turn.citations, setActiveCitation);

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

        <p className="bubble-rationale">{parsedRationale}</p>

        {/* {turn.citations?.length > 0 && (
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
        )} */}
      </div>

      {activeCitation && (
        <CitationModal citation={activeCitation} onClose={() => setActiveCitation(null)} />
      )}
    </>
  );
}