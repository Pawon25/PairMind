import React from 'react';
import { Loader2, CheckCircle2, XCircle, AlertTriangle, Clock } from 'lucide-react';
import '../styles/StatusBanner.css';

const CONFIG = {
  NEGOTIATING: { icon: Loader2,       label: 'Negotiating',  cls: 'negotiating', spin: true  },
  AGREEMENT:   { icon: CheckCircle2,  label: 'Agreement',    cls: 'agreement',   spin: false },
  WALK_AWAY:   { icon: XCircle,       label: 'Walk Away',    cls: 'walkaway',    spin: false },
  DEADLOCK:    { icon: AlertTriangle, label: 'Deadlock',     cls: 'deadlock',    spin: false },
  TIMEOUT:     { icon: Clock,         label: 'Timeout',      cls: 'timeout',     spin: false },
  ERROR:       { icon: AlertTriangle, label: 'Error',        cls: 'error',       spin: false },
};

export default function StatusBanner({ status }) {
  const cfg = CONFIG[status] || CONFIG.NEGOTIATING;
  const Icon = cfg.icon;

  return (
    <div className={`status-banner status-${cfg.cls}`}>
      <Icon size={14} className={cfg.spin ? 'spin' : ''} />
      <span>{cfg.label}</span>
    </div>
  );
}