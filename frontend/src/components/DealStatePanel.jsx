import React from 'react';
import { DollarSign, Package, Calendar, CreditCard, Shield } from 'lucide-react';
import '../styles/DealStatePanel.css';

const Row = ({ icon: Icon, label, value, highlight }) => (
  <div className={`ds-row ${highlight ? 'ds-row-highlight' : ''}`}>
    <Icon size={13} className="ds-icon" />
    <span className="ds-label">{label}</span>
    <span className="ds-value">{value ?? '—'}</span>
  </div>
);

export default function DealStatePanel({ dealState, turnCount, summary }) {
  return (
    <div className="ds-panel">
      <div className="ds-header">
        <span className="ds-title">Deal State</span>
        {turnCount != null && (
          <span className="ds-turn">Turn {turnCount}</span>
        )}
      </div>

      <div className="ds-body">
        {dealState ? (
          <>
            <Row icon={DollarSign} label="Price"    value={dealState.unit_price    ? `$${dealState.unit_price}/unit` : null} highlight />
            <Row icon={Package}    label="Quantity"  value={dealState.quantity      ? `${dealState.quantity} units`   : null} />
            <Row icon={Calendar}   label="Delivery"  value={dealState.delivery_date} />
            <Row icon={CreditCard} label="Payment"   value={dealState.payment_terms} />
            <Row icon={Shield}     label="Warranty"  value={dealState.warranty_years ? `${dealState.warranty_years} yr` : null} />
          </>
        ) : (
          <p className="ds-empty">Waiting for first proposal…</p>
        )}
      </div>

      {summary && (
        <div className="ds-summary">
          <div className="ds-summary-label">Final Outcome</div>
          <div className="ds-summary-outcome">{summary.outcome}</div>
          {summary.turn_count    && <div className="ds-summary-stat">{summary.turn_count} turns</div>}
          {summary.duration_seconds && <div className="ds-summary-stat">{Math.round(summary.duration_seconds)}s</div>}
        </div>
      )}
    </div>
  );
}