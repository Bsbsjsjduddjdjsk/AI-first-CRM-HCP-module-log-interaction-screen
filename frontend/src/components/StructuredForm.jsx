import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  updateField,
  addProduct,
  removeProduct,
  submitInteraction,
  searchHcpOptions,
  resetForm,
} from '../store/interactionSlice';

export default function StructuredForm() {
  const dispatch = useDispatch();
  const { form, hcpOptions, submitStatus, lastResult, error } = useSelector((s) => s.interaction);
  const [productInput, setProductInput] = useState('');

  useEffect(() => {
    if (form.hcp_name && form.hcp_name.length > 1) {
      const timeout = setTimeout(() => dispatch(searchHcpOptions(form.hcp_name)), 300);
      return () => clearTimeout(timeout);
    }
  }, [form.hcp_name, dispatch]);

  const handleChange = (field) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    dispatch(updateField({ field, value }));
  };

  const handleSelectHcp = (hcp) => {
    dispatch(updateField({ field: 'hcp_id', value: hcp.id }));
    dispatch(updateField({ field: 'hcp_name', value: hcp.full_name }));
  };

  const handleAddProduct = () => {
    if (productInput.trim()) {
      dispatch(addProduct({ product_name: productInput.trim() }));
      setProductInput('');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    dispatch(
      submitInteraction({
        ...form,
        occurred_at: new Date(form.occurred_at).toISOString(),
        duration_minutes: Number(form.duration_minutes) || null,
      })
    );
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="field">
        <label>HCP Name</label>
        <input
          type="text"
          value={form.hcp_name}
          onChange={handleChange('hcp_name')}
          placeholder="Start typing an HCP name..."
          autoComplete="off"
          required
        />
        {hcpOptions.length > 0 && form.hcp_id === '' && (
          <div style={{ fontSize: 12, color: '#656b7a' }}>
            {hcpOptions.map((h) => (
              <div
                key={h.id}
                style={{ padding: '4px 0', cursor: 'pointer' }}
                onClick={() => handleSelectHcp(h)}
              >
                {h.full_name} — {h.specialty}, {h.institution}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="field-row">
        <div className="field">
          <label>Interaction Type</label>
          <select value={form.interaction_type} onChange={handleChange('interaction_type')}>
            <option value="visit">Visit</option>
            <option value="call">Call</option>
            <option value="email">Email</option>
            <option value="event">Event</option>
            <option value="virtual_meeting">Virtual Meeting</option>
          </select>
        </div>
        <div className="field">
          <label>Date &amp; Time</label>
          <input
            type="datetime-local"
            value={form.occurred_at}
            onChange={handleChange('occurred_at')}
            required
          />
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Duration (minutes)</label>
          <input type="number" value={form.duration_minutes} onChange={handleChange('duration_minutes')} />
        </div>
        <div className="field">
          <label>HCP Sentiment</label>
          <select value={form.hcp_sentiment} onChange={handleChange('hcp_sentiment')}>
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
          </select>
        </div>
      </div>

      <div className="field">
        <label>Products Discussed</label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={productInput}
            onChange={(e) => setProductInput(e.target.value)}
            placeholder="e.g., CardioX"
          />
          <button type="button" className="btn-secondary" onClick={handleAddProduct}>
            Add
          </button>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
          {form.products_discussed.map((p, idx) => (
            <span key={idx} className="badge logged">
              {p.product_name}{' '}
              <span style={{ cursor: 'pointer' }} onClick={() => dispatch(removeProduct(idx))}>
                ×
              </span>
            </span>
          ))}
        </div>
      </div>

      <div className="field">
        <label>Key Discussion Points</label>
        <textarea
          rows={4}
          value={form.key_discussion_points}
          onChange={handleChange('key_discussion_points')}
          placeholder="Summarize what was discussed..."
        />
      </div>

      <div className="field">
        <label>
          <input
            type="checkbox"
            checked={form.follow_up_needed}
            onChange={handleChange('follow_up_needed')}
            style={{ marginRight: 6 }}
          />
          Follow-up needed
        </label>
        {form.follow_up_needed && (
          <input
            type="text"
            placeholder="Follow-up notes (e.g., 'sample drop next week')"
            value={form.follow_up_notes}
            onChange={handleChange('follow_up_notes')}
          />
        )}
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
        <button type="submit" className="btn-primary" disabled={submitStatus === 'loading'}>
          {submitStatus === 'loading' ? 'Saving...' : 'Log Interaction'}
        </button>
        <button type="button" className="btn-secondary" onClick={() => dispatch(resetForm())}>
          Clear
        </button>
      </div>

      {submitStatus === 'succeeded' && (
        <div className="confirm-card" style={{ borderColor: '#1f9d55', background: '#e4f7ea' }}>
          Interaction logged successfully (ID: {lastResult?.interaction_id}).
        </div>
      )}
      {submitStatus === 'failed' && (
        <div className="confirm-card" style={{ borderColor: '#d64545', background: '#fdecec' }}>
          {error?.detail?.message || error?.message || 'Something went wrong. Please check the HCP name and try again.'}
        </div>
      )}
    </form>
  );
}
