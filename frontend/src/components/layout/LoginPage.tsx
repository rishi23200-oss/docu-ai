import React, { useState } from 'react';
import { useAuthStore } from '../../store';
import { FileText, Mic, Video, Sparkles, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [form, setForm] = useState({ email: '', username: '', password: '' });
  const [error, setError] = useState('');
  const { login, register, loading } = useAuthStore();

  const handleSubmit = async () => {
    setError('');
    try {
      if (mode === 'login') {
        await login(form.username, form.password);
      } else {
        await register(form.email, form.username, form.password);
        // After successful registration, switch to login tab
        setMode('login');
        setError('');
        setForm({ ...form, password: '' });
        alert('Account created! Please sign in.');
      }
    } catch (err: any) {
      console.error('Auth error:', err);
      const detail = err?.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join(', '));
      } else {
        setError(detail || err?.message || 'Something went wrong. Check console.');
      }
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', padding: '24px', position: 'relative', overflow: 'hidden'
    }}>
      {/* Background decoration */}
      <div style={{
        position: 'absolute', top: '10%', left: '5%', width: 400, height: 400,
        background: 'radial-gradient(circle, rgba(124,106,247,0.08) 0%, transparent 70%)',
        pointerEvents: 'none'
      }} />
      <div style={{
        position: 'absolute', bottom: '10%', right: '5%', width: 300, height: 300,
        background: 'radial-gradient(circle, rgba(249,112,102,0.06) 0%, transparent 70%)',
        pointerEvents: 'none'
      }} />

      <div style={{ width: '100%', maxWidth: 440, position: 'relative', zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 56, height: 56, borderRadius: 16,
            background: 'linear-gradient(135deg, var(--accent), #a855f7)',
            marginBottom: 16, boxShadow: '0 8px 32px rgba(124,106,247,0.3)'
          }}>
            <Sparkles size={28} color="white" />
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px' }}>
            DocuAI
          </h1>
          <p style={{ color: 'var(--text-muted)', marginTop: 6, fontSize: 14 }}>
            Ask questions from your documents, audio & video
          </p>
        </div>

        {/* Feature pills */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 32 }}>
          {[
            { icon: FileText, label: 'PDFs', color: '#a89af9' },
            { icon: Mic, label: 'Audio', color: '#34d399' },
            { icon: Video, label: 'Video', color: '#f97066' },
          ].map(({ icon: Icon, label, color }) => (
            <div key={label} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
              background: 'var(--bg-2)', border: '1px solid var(--border)',
              borderRadius: 99, fontSize: 12, fontWeight: 500
            }}>
              <Icon size={13} color={color} />
              <span style={{ color: 'var(--text-muted)' }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--bg-2)', border: '1px solid var(--border)',
          borderRadius: 20, padding: 32, boxShadow: 'var(--shadow)'
        }}>
          {/* Tabs */}
          <div style={{
            display: 'flex', background: 'var(--bg)', borderRadius: 10,
            padding: 4, marginBottom: 28
          }}>
            {(['login', 'register'] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)} style={{
                flex: 1, padding: '8px 0', borderRadius: 7, border: 'none', cursor: 'pointer',
                fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 500,
                transition: 'all 0.2s',
                background: mode === m ? 'var(--bg-3)' : 'transparent',
                color: mode === m ? 'var(--text)' : 'var(--text-muted)',
                boxShadow: mode === m ? '0 1px 4px rgba(0,0,0,0.3)' : 'none',
              }}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          {/* Fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {mode === 'register' && (
              <Input label="Email" type="email" value={form.email}
                onChange={(v) => setForm({ ...form, email: v })} />
            )}
            <Input label={mode === 'login' ? 'Email or Username' : 'Username'}
              value={form.username} onChange={(v) => setForm({ ...form, username: v })} />
            <Input label="Password" type="password" value={form.password}
              onChange={(v) => setForm({ ...form, password: v })} />
          </div>

          {error && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, marginTop: 16,
              padding: '10px 14px', background: 'rgba(248,113,113,0.1)',
              border: '1px solid rgba(248,113,113,0.3)', borderRadius: 8,
              color: 'var(--error)', fontSize: 13
            }}>
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          <button onClick={handleSubmit} disabled={loading} style={{
            width: '100%', marginTop: 20, padding: '12px 0',
            background: 'linear-gradient(135deg, var(--accent), #a855f7)',
            color: 'white', border: 'none', borderRadius: 10, cursor: loading ? 'not-allowed' : 'pointer',
            fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, letterSpacing: '0.02em',
            opacity: loading ? 0.7 : 1, transition: 'all 0.2s',
            boxShadow: loading ? 'none' : '0 4px 20px rgba(124,106,247,0.35)',
          }}>
            {loading ? <span className="spinner" /> : (mode === 'login' ? 'Sign In' : 'Create Account')}
          </button>
        </div>
      </div>
    </div>
  );
}

function Input({ label, type = 'text', value, onChange }: {
  label: string; type?: string; value: string; onChange: (v: string) => void;
}) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLElement).closest('div')?.parentElement?.querySelector('button')?.click()}
        style={{
          width: '100%', padding: '10px 14px', background: 'var(--bg)',
          border: '1px solid var(--border)', borderRadius: 8,
          color: 'var(--text)', fontFamily: 'var(--font-body)', fontSize: 14, outline: 'none',
          transition: 'border-color 0.2s',
        }}
        onFocus={(e) => e.target.style.borderColor = 'var(--accent)'}
        onBlur={(e) => e.target.style.borderColor = 'var(--border)'}
      />
    </div>
  );
}