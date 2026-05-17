import React from 'react';
import '../styles/Stepper.css';

const steps = [
  { n: 1, label: 'Upload Documents' },
  { n: 2, label: 'Negotiate' },
];

export default function Stepper({ currentStep }) {
  return (
    <div className="stepper">
      {steps.map((s, i) => {
        const done = currentStep > s.n;
        const active = currentStep === s.n;
        return (
          <React.Fragment key={s.n}>
            <div className={`step ${active ? 'active' : ''} ${done ? 'done' : ''}`}>
              <div className="step-circle">
                {done ? '✓' : s.n}
              </div>
              <span className="step-label">{s.label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`step-connector ${done ? 'done' : ''}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}