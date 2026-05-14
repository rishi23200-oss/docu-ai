import React, { useEffect, useState } from 'react';
import { useDocumentStore, useAuthStore } from '../../store';
import { LogOut, Sparkles, MessageSquare, FolderOpen } from 'lucide-react';
import DocumentPanel from '../upload/DocumentPanel';
import ChatPanel from '../chat/ChatPanel';
import MediaPlayer from '../media/MediaPlayer';

export default function Dashboard() {
  const { fetchDocuments } = useDocumentStore();
  const { user, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'chat' | 'docs'>('docs');

  useEffect(() => { fetchDocuments(); }, []);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Top Bar */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', height: 56,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-2)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'linear-gradient(135deg, var(--accent), #a855f7)',
          }}>
            <Sparkles size={15} color="white" />
          </div>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 18 }}>DocuAI</span>
        </div>

        {/* Mobile tabs */}
        <div style={{ display: 'flex', gap: 4 }} className="mobile-tabs">
          {[
            { id: 'docs', icon: FolderOpen, label: 'Files' },
            { id: 'chat', icon: MessageSquare, label: 'Chat' },
          ].map(({ id, icon: Icon, label }) => (
            <button key={id} onClick={() => setActiveTab(id as any)} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
              background: activeTab === id ? 'var(--bg-3)' : 'transparent',
              border: '1px solid', borderColor: activeTab === id ? 'var(--border-light)' : 'transparent',
              borderRadius: 8, cursor: 'pointer',
              color: activeTab === id ? 'var(--text)' : 'var(--text-muted)', fontSize: 13, fontWeight: 500,
            }}>
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {user && (
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              {user.username}
            </span>
          )}
          <button onClick={logout} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px',
            background: 'transparent', border: '1px solid var(--border)',
            borderRadius: 7, cursor: 'pointer', color: 'var(--text-muted)', fontSize: 13,
          }}>
            <LogOut size={13} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left: Documents */}
        <div style={{
          width: 340, flexShrink: 0,
          borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
          background: 'var(--bg-2)',
        }}>
          <DocumentPanel />
        </div>

        {/* Right: Chat + Media Player */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <ChatPanel />
          </div>
          <MediaPlayer />
        </div>
      </div>
    </div>
  );
}
