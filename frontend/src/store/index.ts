import { create } from 'zustand';
import { authApi, documentsApi } from '../services/api';

// ── Types ──────────────────────────────────────────────

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_type: 'pdf' | 'audio' | 'video';
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  summary?: string;
  key_topics?: string[];
  duration_seconds?: number;
  timestamps?: TimestampItem[];
  chunk_count: number;
  created_at: string;
}

export interface TimestampItem {
  topic: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Array<{ document_id: string; chunk_text: string; score: number }>;
  timestamp_refs?: Array<{ document_id: string; start_time: number; end_time: number; text: string; filename: string }>;
  isStreaming?: boolean;
}

export interface User {
  id: string;
  email: string;
  username: string;
}

// ── Auth Store ─────────────────────────────────────────

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  loading: false,

login: async (username, password) => {
    set({ loading: true });
    const res = await authApi.login(username, password);
    const token = res.data.access_token;
    localStorage.setItem('access_token', token);
    try {
      const meRes = await authApi.me();
      set({ user: meRes.data, isAuthenticated: true, loading: false });
    } catch {
      set({ isAuthenticated: true, loading: false });
    }
    window.location.href = '/';
  },

  register: async (email, username, password) => {
    set({ loading: true });
    await authApi.register({ email, username, password });
    set({ loading: false });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({ user: null, isAuthenticated: false });
  },

  fetchMe: async () => {
    try {
      const res = await authApi.me();
      set({ user: res.data, isAuthenticated: true });
    } catch {
      localStorage.removeItem('access_token');
      set({ user: null, isAuthenticated: false });
    }
  },
}));

// ── Document Store ─────────────────────────────────────

interface DocumentState {
  documents: Document[];
  selectedDocumentIds: string[];
  loading: boolean;
  uploading: boolean;
  uploadProgress: number;
  fetchDocuments: () => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (id: string) => Promise<void>;
  toggleSelectDocument: (id: string) => void;
  selectAllCompleted: () => void;
  clearSelection: () => void;
  pollDocumentStatus: (id: string) => void;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  selectedDocumentIds: [],
  loading: false,
  uploading: false,
  uploadProgress: 0,

  fetchDocuments: async () => {
    set({ loading: true });
    const res = await documentsApi.list();
    set({ documents: res.data, loading: false });
  },

  uploadDocument: async (file) => {
    set({ uploading: true, uploadProgress: 0 });
    const res = await documentsApi.upload(file, (pct) => set({ uploadProgress: pct }));
    set((state) => ({
      documents: [res.data, ...state.documents],
      uploading: false,
      uploadProgress: 0,
    }));
    get().pollDocumentStatus(res.data.id);
  },

  deleteDocument: async (id) => {
    await documentsApi.delete(id);
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== id),
      selectedDocumentIds: state.selectedDocumentIds.filter((sid) => sid !== id),
    }));
  },

  toggleSelectDocument: (id) => {
    set((state) => ({
      selectedDocumentIds: state.selectedDocumentIds.includes(id)
        ? state.selectedDocumentIds.filter((sid) => sid !== id)
        : [...state.selectedDocumentIds, id],
    }));
  },

  selectAllCompleted: () => {
    const completed = get().documents.filter((d) => d.status === 'completed').map((d) => d.id);
    set({ selectedDocumentIds: completed });
  },

  clearSelection: () => set({ selectedDocumentIds: [] }),

  pollDocumentStatus: (id) => {
    const interval = setInterval(async () => {
      try {
        const res = await documentsApi.get(id);
        set((state) => ({
          documents: state.documents.map((d) => (d.id === id ? res.data : d)),
        }));
        if (['completed', 'failed'].includes(res.data.status)) {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 3000);
  },
}));

// ── Chat Store ─────────────────────────────────────────

interface ChatState {
  messages: Message[];
  conversationId: string | null;
  isStreaming: boolean;
  activeTimestamp: { documentId: string; startTime: number } | null;
  sendMessage: (documentIds: string[], content: string) => Promise<void>;
  setActiveTimestamp: (data: { documentId: string; startTime: number } | null) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  conversationId: null,
  isStreaming: false,
  activeTimestamp: null,

  sendMessage: async (documentIds, content) => {
    const userMsg: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    const streamingMsg: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    set((state) => ({
      messages: [...state.messages, userMsg, streamingMsg],
      isStreaming: true,
    }));

    try {
      const { chatApi } = await import('../services/api');
      let fullContent = '';
      let finalMsg: Partial<Message> = {};

      for await (const chunk of chatApi.stream(documentIds, content, get().conversationId || undefined)) {
        fullContent += chunk;
        set((state) => ({
          messages: state.messages.map((m, i) =>
            i === state.messages.length - 1 ? { ...m, content: fullContent } : m
          ),
        }));
      }

      // Get final response with sources via regular call for metadata
      try {
        const res = await chatApi.send(documentIds, content, get().conversationId || undefined);
        finalMsg = {
          sources: res.data.message.sources,
          timestamp_refs: res.data.message.timestamp_refs,
        };
        if (!get().conversationId) {
          set({ conversationId: res.data.conversation_id });
        }
      } catch { /* metadata fetch is best-effort */ }

      set((state) => ({
        messages: state.messages.map((m, i) =>
          i === state.messages.length - 1
            ? { ...m, content: fullContent, isStreaming: false, ...finalMsg }
            : m
        ),
        isStreaming: false,
      }));
    } catch (err) {
      set((state) => ({
        messages: state.messages.map((m, i) =>
          i === state.messages.length - 1
            ? { ...m, content: 'Sorry, something went wrong. Please try again.', isStreaming: false }
            : m
        ),
        isStreaming: false,
      }));
    }
  },

  setActiveTimestamp: (data) => set({ activeTimestamp: data }),
  clearChat: () => set({ messages: [], conversationId: null }),
}));
