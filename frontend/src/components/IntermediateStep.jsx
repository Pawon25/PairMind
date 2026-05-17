import React from 'react';
import '../styles/IntermediateStep.css';

export default function IntermediateStep({ turns }) {
  const lastTurn = turns[turns.length - 1];
  const nextAgent = !lastTurn || lastTurn.agent_id === 'seller' ? 'Buyer' : 'Seller';
  const color = nextAgent === 'Buyer' ? 'blue' : 'amber';

  const messages = {
    Buyer:  ['Buyer is reviewing documents…', 'Buyer is checking market rates…', 'Buyer is formulating a counter…'],
    Seller: ['Seller is reviewing the offer…', 'Seller is running web search…', 'Seller is preparing a response…'],
  };

  const msg = messages[nextAgent][turns.length % 3];

  return (
    <div className={`intermediate intermediate-${color}`}>
      <div className="intermediate-dots">
        <span /><span /><span />
      </div>
      <span className="intermediate-text">{msg}</span>
    </div>
  );
}