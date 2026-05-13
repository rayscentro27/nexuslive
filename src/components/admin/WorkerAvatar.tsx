import React from 'react';
import { motion } from 'motion/react';
import type { WorkerStatus, WorkerState } from './workforce_state_adapter';

const STATE_COLORS: Record<WorkerState, { ring: string; glow: string; dot: string; bg: string }> = {
  active:      { ring: '#3d5af1', glow: 'rgba(61,90,241,0.3)', dot: '#22c55e', bg: '#eef0fd' },
  researching: { ring: '#7c3aed', glow: 'rgba(124,58,237,0.3)', dot: '#7c3aed', bg: '#f5f3ff' },
  analyzing:   { ring: '#0d9488', glow: 'rgba(13,148,136,0.3)', dot: '#0d9488', bg: '#f0fdfa' },
  idle:        { ring: '#d1d5db', glow: 'transparent', dot: '#d1d5db', bg: '#f9fafb' },
  warning:     { ring: '#f59e0b', glow: 'rgba(245,158,11,0.3)', dot: '#f59e0b', bg: '#fffbeb' },
  offline:     { ring: '#ef4444', glow: 'rgba(239,68,68,0.2)', dot: '#ef4444', bg: '#fef2f2' },
};

const STATE_LABELS: Record<WorkerState, string> = {
  active:      'Active',
  researching: 'Researching',
  analyzing:   'Analyzing',
  idle:        'Idle',
  warning:     'Warning',
  offline:     'Offline',
};

const PULSE_STATES: WorkerState[] = ['active', 'researching', 'analyzing'];

interface Props {
  worker: WorkerStatus;
  size?: 'sm' | 'md';
}

export function WorkerAvatar({ worker, size = 'md' }: Props) {
  const colors = STATE_COLORS[worker.state];
  const isPulsing = PULSE_STATES.includes(worker.state);
  const dim = size === 'sm' ? 44 : 56;
  const emojiSize = size === 'sm' ? 18 : 24;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      {/* Avatar circle */}
      <div style={{ position: 'relative' }}>
        {/* Pulse ring */}
        {isPulsing && (
          <motion.div
            animate={{ scale: [1, 1.4, 1], opacity: [0.6, 0, 0.6] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              position: 'absolute', inset: -4,
              borderRadius: '50%',
              background: colors.glow,
              pointerEvents: 'none',
            }}
          />
        )}

        {/* Main circle */}
        <motion.div
          animate={worker.state === 'idle' ? {} : { y: [0, -2, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut', delay: Math.random() * 2 }}
          style={{
            width: dim, height: dim, borderRadius: '50%',
            background: colors.bg,
            border: `2.5px solid ${colors.ring}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: emojiSize,
            boxShadow: isPulsing ? `0 0 16px ${colors.glow}` : 'none',
            cursor: 'default',
          }}
        >
          {worker.emoji}
        </motion.div>

        {/* Status dot */}
        <div style={{
          position: 'absolute', bottom: 2, right: 2,
          width: 10, height: 10, borderRadius: '50%',
          background: colors.dot,
          border: '2px solid #fff',
        }} />
      </div>

      {/* Label */}
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: size === 'sm' ? 10 : 11, fontWeight: 700, color: '#1a1c3a', margin: 0, whiteSpace: 'nowrap' }}>
          {worker.label}
        </p>
        <p style={{ fontSize: 9, color: '#8b8fa8', margin: 0, whiteSpace: 'nowrap', maxWidth: 64, overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {STATE_LABELS[worker.state]}
        </p>
      </div>
    </div>
  );
}
