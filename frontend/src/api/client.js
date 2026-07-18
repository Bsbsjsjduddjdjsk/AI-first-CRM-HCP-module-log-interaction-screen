import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const createInteraction = (payload) =>
  apiClient.post('/api/interactions', payload).then((r) => r.data);

export const updateInteraction = (interactionId, payload) =>
  apiClient.patch(`/api/interactions/${interactionId}`, payload).then((r) => r.data);

export const searchHcps = (query) =>
  apiClient.get('/api/hcps', { params: { q: query } }).then((r) => r.data);

export const sendChatMessage = (payload) =>
  apiClient.post('/api/chat/message', payload).then((r) => r.data);

export const confirmChatAction = (payload) =>
  apiClient.post('/api/chat/confirm', payload).then((r) => r.data);
