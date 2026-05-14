import React, { useEffect, useRef, useState } from 'react';
import { useChatStore, useDocumentStore } from '../../store';
import { Send, Bot, User, Play, Trash2, FileText, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function ChatPanel() {
  const { messages, isStreaming, sendMessage, clearChat } = useChatStore();
  const { selectedDocumentIds } = useDocumentStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isStreaming || selectedDocumentIds.length === 0) return;
    setInput('');
    await sendMessage(selectedDocumentIds, text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '14px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexShrink: 0, background: 'var(--bg-2)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <MessageSquare size={16} color="var(--accent)" />
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>Chat</span>
          {selectedDocumentIds.length > 0 && (
            <span style={{
              fontSize: 11, padding: '2px 8px',
              background: 'var(--accent-glow)', color: 'var(--accent)',
              borderRadius: 99, fontWeight: 600,
            }}>
              {selectedDocumentIds.length} file{selectedDocumentIds.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
        {messages.length > 0 && (
          <button onClick={clearChat} style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px',
            background: 'transparent', border: '1px solid var(--border)',
            borderRadius: 7, cursor: 'pointer', color: 'var(--text-muted)', fontSize: 12,
          }}>
            <Trash2 size={12} /> Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
        {messages.length === 0 ? (
          <EmptyState hasSelection={selectedDocumentIds.length > 0} />
        ) : (
          messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '14px 20px', borderTop: '1px solid var(--border)',
        background: 'var(--bg-2)', flexShrink: 0,
      }}>
        {selectedDocumentIds.length === 0 && (
          <p style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 8, textAlign: 'center' }}>
            ← Select documents from the left panel to start chatting
          </p>
        )}
        <div style={{
          display: 'flex', gap: 10, alignItems: 'flex-end',
          background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 12, padding: '8px 12px',
          transition: 'border-color 0.2s',
        }}
          onFocus={() => {}}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={selectedDocumentIds.length > 0 ? 'Ask a question about your documents...' : 'Select documents first'}
            disabled={selectedDocumentIds.length === 0 || isStreaming}
            rows={1}
            style={{
              flex: 1, background: 'transparent', border: 'none', outline: 'none',
              color: 'var(--text)', fontFamily: 'var(--font-body)', fontSize: 14,
              resize: 'none', maxHeight: 120, lineHeight: 1.5,
              cursor: selectedDocumentIds.length === 0 ? 'not-allowed' : 'text',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming || selectedDocumentIds.length === 0}
            style={{
              width: 34, height: 34, borderRadius: 9,
              background: input.trim() && !isStreaming && selectedDocumentIds.length > 0
                ? 'linear-gradient(135deg, var(--accent), #a855f7)'
                : 'var(--bg-3)',
              border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.2s', flexShrink: 0,
            }}
          >
            {isStreaming
              ? <span className="spinner" style={{ width: 14, height: 14 }} />
              : <Send size={14} color={input.trim() && selectedDocumentIds.length > 0 ? 'white' : 'var(--text-dim)'} />
            }
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: any }) {
  const { setActiveTimestamp } = useChatStore();
  const isUser = message.role === 'user';

  return (
    <div className="animate-in" style={{
      marginBottom: 20, display: 'flex', gap: 10,
      flexDirection: isUser ? 'row-reverse' : 'row',
    }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: 10, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: isUser
          ? 'linear-gradient(135deg, #f97066, #fb923c)'
          : 'linear-gradient(135deg, var(--accent), #a855f7)',
        boxShadow: isUser ? 'none' : '0 2px 12px rgba(124,106,247,0.25)',
      }}>
        {isUser ? <User size={15} color="white" /> : <Bot size={15} color="white" />}
      </div>

      <div style={{ maxWidth: '75%', minWidth: 0 }}>
        {/* Message content */}
        <div style={{
          padding: '10px 14px', borderRadius: isUser ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
          background: isUser ? 'var(--bg-3)' : 'var(--bg-2)',
          border: '1px solid var(--border)',
          fontSize: 14, lineHeight: 1.65,
        }}>
          {message.isStreaming && message.content === '' ? (
            <div style={{ display: 'flex', gap: 4, padding: '2px 0' }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)',
                  animation: `blink 1.2s ease ${i * 0.2}s infinite`
                }} />
              ))}
            </div>
          ) : (
            <>
              <div style={{ color: 'var(--text)' }}>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              {message.isStreaming && <span className="cursor-blink" />}
            </>
          )}
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {message.sources.slice(0, 3).map((src: any, i: number) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px',
                background: 'var(--bg)', border: '1px solid var(--border)',
                borderRadius: 99, fontSize: 11, color: 'var(--text-muted)',
              }}>
                <FileText size={10} />
                <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {src.document_id}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Timestamp refs */}
        {!isUser && message.timestamp_refs && message.timestamp_refs.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <p style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>Jump to relevant section:</p>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {message.timestamp_refs.map((ref: any, i: number) => (
                <button
                  key={i}
                  onClick={() => setActiveTimestamp({ documentId: ref.document_id, startTime: ref.start_time })}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px',
                    background: 'rgba(52, 211, 153, 0.08)', border: '1px solid rgba(52,211,153,0.3)',
                    borderRadius: 8, cursor: 'pointer', fontSize: 12, color: '#34d399',
                    fontWeight: 500,
                  }}
                >
                  <Play size={11} />
                  {formatTime(ref.start_time)}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ hasSelection }: { hasSelection: boolean }) {
  const suggestions = [
    'Summarize the key points',
    'What are the main conclusions?',
    'List the important dates mentioned',
    'Explain the main topic in simple terms',
  ];
  const { sendMessage, } = useChatStore();
  const { selectedDocumentIds } = useDocumentStore();

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
      <div style={{
        width: 56, height: 56, borderRadius: 16, marginBottom: 16,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'linear-gradient(135deg, var(--accent), #a855f7)',
        boxShadow: '0 8px 32px rgba(124,106,247,0.25)',
      }}>
        <Bot size={26} color="white" />
      </div>
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, marginBottom: 8 }}>
        Ready to Answer
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', marginBottom: 24, maxWidth: 280, lineHeight: 1.6 }}>
        {hasSelection ? 'Ask anything about your selected documents' : 'Select documents on the left to start a conversation'}
      </p>
      {hasSelection && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', maxWidth: 320 }}>
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => sendMessage(selectedDocumentIds, s)}
              style={{
                padding: '9px 14px', background: 'var(--bg-2)',
                border: '1px solid var(--border)', borderRadius: 9,
                cursor: 'pointer', color: 'var(--text-muted)', fontSize: 13, textAlign: 'left',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
                e.currentTarget.style.color = 'var(--text)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.color = 'var(--text-muted)';
              }}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}
