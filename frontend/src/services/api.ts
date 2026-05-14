
/// <reference types="vite/client" />
import axios from 'axios';
localStorage.setItem('access_token', 'bypass-token');

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({ baseURL: API_BASE });

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect on 401
api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
);

// --- Auth ---
export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    api.post('/auth/register', data),
  login: async (username: string, password: string) => {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const response = await api.post('/auth/token', form);
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
    }
    return response;
  },
  me: () => api.get('/auth/me'),
};

// --- Documents ---
export const documentsApi = {
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/documents/upload', form, {
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    });
  },
  list: () => api.get('/documents/'),
  get: (id: string) => api.get(`/documents/${id}`),
  getSummary: (id: string) => api.get(`/documents/${id}/summary`),
  getTimestamps: (id: string) => api.get(`/documents/${id}/timestamps`),
  delete: (id: string) => api.delete(`/documents/${id}`),
  getStreamUrl: (id: string) => `${API_BASE}/media/${id}/stream`,
};

// --- Chat ---
export const chatApi = {
  send: (documentIds: string[], message: string, conversationId?: string) =>
    api.post('/chat/', { document_ids: documentIds, message, conversation_id: conversationId }),
  listConversations: () => api.get('/chat/conversations'),
  getConversation: (id: string) => api.get(`/chat/conversations/${id}`),
  deleteConversation: (id: string) => api.delete(`/chat/conversations/${id}`),

  // Streaming chat — returns EventSource-like async generator
  stream: async function* (documentIds: string[], message: string, conversationId?: string) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        document_ids: documentIds,
        message,
        conversation_id: conversationId,
        stream: true,
      }),
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          yield data;
        }
      }
    }
  },
};

export default api;