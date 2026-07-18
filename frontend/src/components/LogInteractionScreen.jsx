import React, { useState } from 'react';
import StructuredForm from './StructuredForm';
import ChatInterface from './ChatInterface';

export default function LogInteractionScreen() {
  const [mode, setMode] = useState('form'); // 'form' | 'chat'

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>Log HCP Interaction</h1>
        <div className="mode-toggle">
          <button
            className={mode === 'form' ? 'active' : ''}
            onClick={() => setMode('form')}
          >
            Structured Form
          </button>
          <button
            className={mode === 'chat' ? 'active' : ''}
            onClick={() => setMode('chat')}
          >
            Chat
          </button>
        </div>
      </div>

      <div className="card">
        {mode === 'form' ? <StructuredForm /> : <ChatInterface />}
      </div>
    </div>
  );
}
