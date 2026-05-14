import React, { useEffect, useRef, useState } from 'react';
import { useChatStore, useDocumentStore } from '../../store';
import { Play, Pause, Volume2, VolumeX, X, SkipBack, SkipForward } from 'lucide-react';
import { documentsApi } from '../../services/api';

export default function MediaPlayer() {
  const { activeTimestamp, setActiveTimestamp } = useChatStore();
  const { documents } = useDocumentStore();
  const audioRef = useRef<HTMLAudioElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);

  const activeDoc = activeTimestamp
    ? documents.find((d) => d.id === activeTimestamp.documentId)
    : null;

  const isVideo = activeDoc?.file_type === 'video';
  const mediaRef = isVideo ? videoRef : audioRef;

  useEffect(() => {
    if (activeTimestamp && mediaRef.current) {
      mediaRef.current.currentTime = activeTimestamp.startTime;
      mediaRef.current.play().then(() => setPlaying(true)).catch(() => {});
    }
  }, [activeTimestamp]);

  const togglePlay = () => {
    if (!mediaRef.current) return;
    if (playing) {
      mediaRef.current.pause();
      setPlaying(false);
    } else {
      mediaRef.current.play().then(() => setPlaying(true)).catch(() => {});
    }
  };

  // Apply volume via ref (volume is not a valid HTML attribute in React's type defs)
  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = muted ? 0 : volume;
    if (videoRef.current) videoRef.current.volume = muted ? 0 : volume;
  }, [muted, volume]);

  const handleTimeUpdate = () => {
    setCurrentTime(mediaRef.current?.currentTime || 0);
  };

  const handleLoadedMetadata = () => {
    setDuration(mediaRef.current?.duration || 0);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const t = parseFloat(e.target.value);
    if (mediaRef.current) mediaRef.current.currentTime = t;
    setCurrentTime(t);
  };

  const skip = (secs: number) => {
    if (!mediaRef.current) return;
    mediaRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + secs));
  };

  const close = () => {
    if (mediaRef.current) {
      mediaRef.current.pause();
      setPlaying(false);
    }
    setActiveTimestamp(null);
  };

  if (!activeDoc) return null;

  const streamUrl = documentsApi.getStreamUrl(activeDoc.id);
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div style={{
      borderTop: '1px solid var(--border)',
      background: 'var(--bg-2)',
      padding: '12px 20px',
      flexShrink: 0,
    }}>
      {/* Hidden audio/video elements */}
      <audio
        ref={audioRef}
        src={!isVideo ? streamUrl : undefined}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setPlaying(false)}
        preload="metadata"
      />
      {isVideo && (
        <video
          ref={videoRef}
          src={streamUrl}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setPlaying(false)}
          style={{ display: 'none' }}
          preload="metadata"
        />
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 12, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {activeDoc.original_filename}
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
            {activeDoc.file_type === 'audio' ? 'Audio' : 'Video'} •{' '}
            {formatTime(currentTime)} / {formatTime(duration)}
          </p>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ControlBtn onClick={() => skip(-10)}><SkipBack size={14} /></ControlBtn>
          <button onClick={togglePlay} style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, var(--accent), #a855f7)',
            border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 2px 12px rgba(124,106,247,0.3)',
          }}>
            {playing ? <Pause size={16} color="white" /> : <Play size={16} color="white" />}
          </button>
          <ControlBtn onClick={() => skip(10)}><SkipForward size={14} /></ControlBtn>
        </div>

        {/* Progress */}
        <div style={{ flex: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, position: 'relative', height: 4, background: 'var(--border)', borderRadius: 2 }}>
            <div style={{
              position: 'absolute', left: 0, top: 0, height: '100%',
              width: `${progress}%`,
              background: 'linear-gradient(90deg, var(--accent), #a855f7)',
              borderRadius: 2, transition: 'width 0.1s linear',
            }} />
            <input
              type="range" min={0} max={duration || 100} step={0.1} value={currentTime}
              onChange={handleSeek}
              style={{
                position: 'absolute', inset: 0, width: '100%', opacity: 0, cursor: 'pointer',
                height: '100%', margin: 0,
              }}
            />
          </div>
        </div>

        {/* Volume */}
        <ControlBtn onClick={() => setMuted(!muted)}>
          {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
        </ControlBtn>

        {/* Close */}
        <ControlBtn onClick={close}><X size={14} /></ControlBtn>
      </div>
    </div>
  );
}

function ControlBtn({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      width: 28, height: 28, borderRadius: 7,
      background: 'transparent', border: '1px solid var(--border)',
      cursor: 'pointer', color: 'var(--text-muted)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      {children}
    </button>
  );
}

function formatTime(s: number) {
  if (!s || isNaN(s)) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}