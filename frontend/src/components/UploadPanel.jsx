import React, { useState, useRef } from 'react';
import { Upload, FileText, X, ArrowRight, AlertCircle } from 'lucide-react';
import { uploadDocument, startNegotiation } from '../api/index';
import '../styles/UploadPanel.css';

const TAG_OPTIONS = [
  { value: 'buyer-private',  label: 'Buyer',  color: 'blue'  },
  { value: 'seller-private', label: 'Seller', color: 'amber' },
  { value: 'shared',         label: 'Shared', color: 'slate' },
];

export default function UploadPanel({ onStart }) {
  const [files, setFiles]         = useState([]);   // { file, tag, id, uploading, error }
  const [activeTag, setActiveTag] = useState('buyer-private');
  const [dragging, setDragging]   = useState(false);
  const [starting, setStarting]   = useState(false);
  const [error, setError]         = useState(null);
  const inputRef = useRef();

  const addFiles = async (incoming) => {
    const newEntries = Array.from(incoming).map((f) => ({
      file: f,
      tag: activeTag,
      id: null,
      uploading: true,
      error: null,
      localId: crypto.randomUUID(),
    }));

    setFiles((prev) => [...prev, ...newEntries]);

    for (const entry of newEntries) {
      try {
        const { doc_id } = await uploadDocument(entry.file, entry.tag);
        setFiles((prev) =>
          prev.map((f) => f.localId === entry.localId ? { ...f, id: doc_id, uploading: false } : f)
        );
      } catch (e) {
        setFiles((prev) =>
          prev.map((f) => f.localId === entry.localId ? { ...f, uploading: false, error: 'Upload failed' } : f)
        );
      }
    }
  };

  const removeFile = (localId) =>
    setFiles((prev) => prev.filter((f) => f.localId !== localId));

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const handleStart = async () => {
    if (files.length === 0) return;
    setError(null);
    setStarting(true);
    try {
      const { session_id } = await startNegotiation();
      onStart(session_id);
    } catch (e) {
      setError('Failed to start negotiation. Is the backend running?');
      setStarting(false);
    }
  };

  const uploadedCount = files.filter((f) => f.id && !f.error).length;

  return (
    <div className="upload-page">
      <div className="upload-card">
        <div className="upload-card-header">
          <h1 className="upload-title">Upload Documents</h1>
          <p className="upload-subtitle">
            Upload private and shared documents for each agent before starting the negotiation.
          </p>
        </div>

        {/* Tag selector */}
        <div className="tag-row">
          <span className="tag-row-label">Tag as</span>
          <div className="tag-pills">
            {TAG_OPTIONS.map((t) => (
              <button
                key={t.value}
                className={`tag-pill tag-pill-${t.color} ${activeTag === t.value ? 'active' : ''}`}
                onClick={() => setActiveTag(t.value)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Drop zone */}
        <div
          className={`dropzone ${dragging ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current.click()}
        >
          <Upload size={28} strokeWidth={1.5} className="dropzone-icon" />
          <p className="dropzone-text">
            <strong>Drag & drop</strong> files here, or <strong>click to browse</strong>
          </p>
          <p className="dropzone-hint">.pdf · .md · .txt · .docx</p>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.md,.txt,.docx"
            style={{ display: 'none' }}
            onChange={(e) => addFiles(e.target.files)}
          />
        </div>

        {/* File list */}
        {files.length > 0 && (
          <ul className="file-list">
            {files.map((f) => {
              const tagMeta = TAG_OPTIONS.find((t) => t.value === f.tag);
              return (
                <li key={f.localId} className="file-item">
                  <span className={`file-dot dot-${tagMeta.color}`} />
                  <FileText size={14} className="file-icon" />
                  <span className="file-name">{f.file.name}</span>
                  <span className={`badge badge-${tagMeta.color}`}>{tagMeta.label}</span>
                  {f.uploading && <span className="file-status uploading">uploading…</span>}
                  {f.error   && <span className="file-status error">{f.error}</span>}
                  {f.id      && <span className="file-status ok">✓</span>}
                  <button
                    className="file-remove"
                    onClick={(e) => { e.stopPropagation(); removeFile(f.localId); }}
                  >
                    <X size={13} />
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {error && (
          <div className="upload-error">
            <AlertCircle size={14} /> {error}
          </div>
        )}

        {/* CTA */}
        <div className="upload-footer">
          <span className="upload-count">
            {uploadedCount} / {files.length} uploaded
          </span>
          <button
            className="btn-primary"
            onClick={handleStart}
            disabled={uploadedCount === 0 || starting}
          >
            {starting ? 'Starting…' : 'Start Negotiation'}
            {!starting && <ArrowRight size={15} />}
          </button>
        </div>
      </div>
    </div>
  );
}