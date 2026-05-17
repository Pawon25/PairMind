import React, { useState } from 'react';
import Stepper from './components/Stepper';
import UploadPanel from './components/UploadPanel';
import NegotiateView from './components/NegotiateView';
import './App.css';

export default function App() {
  const [step, setStep] = useState(1);
  const [sessionId, setSessionId] = useState(null);

  const handleNegotiationStart = (id) => {
    setSessionId(id);
    setStep(2);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">PairMind</span>
        </div>
        <Stepper currentStep={step} />
      </header>

      <main className="app-main">
        {step === 1 && (
          <UploadPanel onStart={handleNegotiationStart} />
        )}
        {step === 2 && sessionId && (
          <NegotiateView sessionId={sessionId} />
        )}
      </main>
    </div>
  );
}