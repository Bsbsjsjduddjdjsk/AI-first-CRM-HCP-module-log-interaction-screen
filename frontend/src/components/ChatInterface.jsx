import React, { useRef, useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage, confirmDraft, resetChat } from '../store/chatSlice';

export default function ChatInterface() {
  const dispatch = useDispatch();
  const { messages, pendingPreview, requiresConfirmation, status } = useSelector((s) => s.chat);
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pendingPreview]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    dispatch(sendMessage(input.trim()));
    setInput('');
  };

  return (
    <div className="chat-window">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ color: '#656b7a', fontSize: 14 }}>
            Try: "Met Dr. Sharma today, discussed CardioX dosing, she wants a sample drop next week."
          </div>
        )}
        {messages.map((m, idx) => (
          <div key={idx} className={`chat-bubble ${m.role === 'user' ? 'user' : 'agent'}`}>
            {m.content}
          </div>
        ))}

        {pendingPreview && requiresConfirmation && (
          <div className="confirm-card">
            <strong>Review before saving:</strong>
            <pre>{JSON.stringify(pendingPreview, null, 2)}</pre>
            <div className="confirm-actions">
              <button
                className="btn-primary"
                onClick={() => dispatch(confirmDraft({ approved: true }))}
              >
                Confirm &amp; Save
              </button>
              <button
                className="btn-secondary"
                onClick={() => dispatch(confirmDraft({ approved: false }))}
              >
                Discard
              </button>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe the interaction, or ask to edit/check history..."
          disabled={status === 'loading'}
        />
        <button type="submit" className="btn-primary" disabled={status === 'loading'}>
          Send
        </button>
        <button type="button" className="btn-secondary" onClick={() => dispatch(resetChat())}>
          New
        </button>
      </form>
    </div>
  );
}
