import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useDocumentStore, type Document } from '../../store';
import {
  Upload, FileText, Mic, Video, Trash2, CheckSquare, Square,
  Clock, CheckCircle, XCircle, Loader, ChevronDown, Tag, BookOpen
} from 'lucide-react';
import { documentsApi } from '../../services/api';

export default function DocumentPanel() {
  const {
    documents, uploading, uploadProgress,
    uploadDocument, deleteDocument,
    selectedDocumentIds, toggleSelectDocument, selectAllCompleted, clearSelection
  } = useDocumentStore();

  const onDrop = useCallback(async (accepted: File[]) => {
    for (const file of accepted) {
      await uploadDocument(file);
    }
  }, [uploadDocument]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'audio/*': ['.mp3', '.wav', '.m4a'],
      'video/*': ['.mp4', '.mov', '.avi', '.mkv'],
    },
    multiple: true,
  });

  const completedCount = documents.filter((d) => d.status === 'completed').length;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>Files</h2>
          <div style={{ display: 'flex', gap: 6 }}>
            {selectedDocumentIds.length > 0 ? (
              <button onClick={clearSelection} style={smallBtnStyle}>Clear ({selectedDocumentIds.length})</button>
            ) : completedCount > 0 ? (
              <button onClick={selectAllCompleted} style={smallBtnStyle}>Select All</button>
            ) : null}
          </div>
        </div>

        {/* Drop Zone */}
        <div {...getRootProps()} style={{
          padding: '16px', borderRadius: 10,
          border: `2px dashed ${isDragActive ? 'var(--accent)' : 'var(--border)'}`,
          background: isDragActive ? 'var(--accent-glow)' : 'var(--bg)',
          cursor: 'pointer', textAlign: 'center', transition: 'all 0.2s',
        }}>
          <input {...getInputProps()} />
          {uploading ? (
            <div>
              <div style={{ marginBottom: 8 }}>
                <Loader size={18} color="var(--accent)" style={{ animation: 'spin 1s linear infinite' }} />
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Uploading...</p>
              <div style={{ height: 4, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${uploadProgress}%`,
                  background: 'linear-gradient(90deg, var(--accent), #a855f7)',
                  borderRadius: 2, transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          ) : (
            <>
              <Upload size={20} color={isDragActive ? 'var(--accent)' : 'var(--text-dim)'} />
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                {isDragActive ? 'Drop to upload' : 'Drop files here or click to browse'}
              </p>
              <p style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                PDF, MP3, WAV, MP4, MOV
              </p>
            </>
          )}
        </div>
      </div>

      {/* Document List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
        {documents.length === 0 ? (
          <div style={{ padding: '32px 16px', textAlign: 'center' }}>
            <BookOpen size={32} color="var(--text-dim)" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>No files uploaded yet</p>
          </div>
        ) : (
          documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              isSelected={selectedDocumentIds.includes(doc.id)}
              onToggle={() => toggleSelectDocument(doc.id)}
              onDelete={() => deleteDocument(doc.id)}
            />
          ))
        )}
      </div>

      {/* Selection Bar */}
      {selectedDocumentIds.length > 0 && (
        <div style={{
          padding: '12px 16px', borderTop: '1px solid var(--border)',
          background: 'var(--accent-glow)',
          flexShrink: 0,
        }}>
          <p style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>
            {selectedDocumentIds.length} file{selectedDocumentIds.length > 1 ? 's' : ''} selected for chat
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            Questions will be answered from these documents
          </p>
        </div>
      )}
    </div>
  );
}

function DocumentCard({ doc, isSelected, onToggle, onDelete }: {
  doc: Document; isSelected: boolean; onToggle: () => void; onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const Icon = doc.file_type === 'pdf' ? FileText : doc.file_type === 'audio' ? Mic : Video;
  const iconColor = doc.file_type === 'pdf' ? '#a89af9' : doc.file_type === 'audio' ? '#34d399' : '#f97066';
  const badgeClass = `badge badge-${doc.file_type}`;
  const canSelect = doc.status === 'completed';

  return (
    <div className="animate-in" style={{
      marginBottom: 8, borderRadius: 10, overflow: 'hidden',
      border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
      background: isSelected ? 'rgba(124,106,247,0.05)' : 'var(--bg)',
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px' }}>
        {/* Checkbox */}
        <button
          onClick={canSelect ? onToggle : undefined}
          disabled={!canSelect}
          style={{ background: 'none', border: 'none', cursor: canSelect ? 'pointer' : 'default', padding: 0, flexShrink: 0 }}
        >
          {isSelected
            ? <CheckSquare size={16} color="var(--accent)" />
            : <Square size={16} color={canSelect ? 'var(--text-dim)' : 'var(--text-dim)'} />
          }
        </button>

        {/* Icon */}
        <div style={{
          width: 32, height: 32, borderRadius: 8, flexShrink: 0,
          background: `${iconColor}18`, display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <Icon size={16} color={iconColor} />
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {doc.original_filename}
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
            <StatusBadge status={doc.status} />
            {doc.duration_seconds && (
              <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                {formatDuration(doc.duration_seconds)}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
          {doc.status === 'completed' && (
            <button onClick={() => setExpanded(!expanded)} style={{ ...iconBtnStyle }}>
              <ChevronDown size={13} style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: '0.2s' }} />
            </button>
          )}
          <button onClick={onDelete} style={{ ...iconBtnStyle, color: 'var(--error)' }}>
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Expanded summary */}
      {expanded && doc.summary && (
        <div style={{
          borderTop: '1px solid var(--border)', padding: '12px',
          background: 'var(--bg-2)'
        }}>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: 8 }}>
            {doc.summary}
          </p>
          {doc.key_topics && doc.key_topics.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {doc.key_topics.map((topic) => (
                <span key={topic} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 3,
                  padding: '2px 8px', background: 'var(--bg-3)',
                  border: '1px solid var(--border)', borderRadius: 99,
                  fontSize: 11, color: 'var(--text-muted)'
                }}>
                  <Tag size={9} />
                  {topic}
                </span>
              ))}
            </div>
          )}
          {doc.timestamps && doc.timestamps.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                Topics
              </p>
              {doc.timestamps.map((ts, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '5px 0', borderBottom: i < doc.timestamps!.length - 1 ? '1px solid var(--border)' : 'none'
                }}>
                  <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, minWidth: 40 }}>
                    {formatTime(ts.start_time)}
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', flex: 1 }}>{ts.topic}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const configs = {
    pending: { icon: Clock, color: 'var(--text-dim)', label: 'Pending' },
    processing: { icon: Loader, color: 'var(--warning)', label: 'Processing' },
    completed: { icon: CheckCircle, color: 'var(--success)', label: 'Ready' },
    failed: { icon: XCircle, color: 'var(--error)', label: 'Failed' },
  } as any;
  const { icon: Icon, color, label } = configs[status] || configs.pending;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color }}>
      <Icon size={11} style={status === 'processing' ? { animation: 'spin 1s linear infinite' } : {}} />
      {label}
    </span>
  );
}

function formatDuration(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}
function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}

const smallBtnStyle: React.CSSProperties = {
  padding: '4px 10px', background: 'var(--bg)', border: '1px solid var(--border)',
  borderRadius: 6, cursor: 'pointer', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500,
};
const iconBtnStyle: React.CSSProperties = {
  padding: '4px', background: 'transparent', border: 'none', cursor: 'pointer',
  color: 'var(--text-muted)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center',
  transition: 'color 0.15s',
};
