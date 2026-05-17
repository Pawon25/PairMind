import React, { useEffect } from 'react';
import { X, FileText, Globe } from 'lucide-react';
import '../styles/CitationModal.css';

export default function CitationModal({ citation, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!citation) return null;

  const isWeb = citation.source?.startsWith('http');

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-row">
            {isWeb ? <Globe size={14} /> : <FileText size={14} />}
            <span className="modal-title">Citation Source</span>
          </div>
          <button className="modal-close" onClick={onClose}><X size={14} /></button>
        </div>

        <div className="modal-body">
          <div className="modal-field">
            <span className="modal-field-label">Source</span>
            {isWeb
              ? <a href={citation.source} target="_blank" rel="noreferrer" className="modal-link">{citation.source}</a>
              : <span className="modal-value">{citation.source}</span>
            }
          </div>
          {citation.section && (
            <div className="modal-field">
              <span className="modal-field-label">Section</span>
              <span className="modal-value">{citation.section}</span>
            </div>
          )}
          {citation.retrieved_date && (
            <div className="modal-field">
              <span className="modal-field-label">Retrieved</span>
              <span className="modal-value">{citation.retrieved_date}</span>
            </div>
          )}
          {isWeb && (
            <div className="modal-unverified">
              ⚠ Web citation — content not verified
            </div>
          )}
        </div>
      </div>
    </div>
  );
}