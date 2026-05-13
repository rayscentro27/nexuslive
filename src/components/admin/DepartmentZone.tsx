import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { WorkerAvatar } from './WorkerAvatar';
import type { DepartmentStatus } from './workforce_state_adapter';

interface Props {
  department: DepartmentStatus;
  defaultExpanded?: boolean;
}

export function DepartmentZone({ department, defaultExpanded = true }: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const activeCount = department.workers.filter(w =>
    w.state === 'active' || w.state === 'researching' || w.state === 'analyzing'
  ).length;
  const warnCount = department.workers.filter(w => w.state === 'warning' || w.state === 'offline').length;

  const headerColor = warnCount > 0 ? '#f59e0b' : department.isActive ? '#3d5af1' : '#8b8fa8';
  const headerBg = warnCount > 0 ? '#fffbeb' : department.isActive ? '#eef0fd' : '#f9fafb';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        borderRadius: 14,
        border: `1.5px solid ${warnCount > 0 ? '#fde68a' : department.isActive ? '#c7d2fe' : '#e5e7eb'}`,
        overflow: 'hidden',
        background: '#fff',
      }}
    >
      {/* Department header */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%', padding: '12px 16px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: headerBg, border: 'none', cursor: 'pointer',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 20 }}>{department.emoji}</span>
          <div style={{ textAlign: 'left' }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{department.name}</p>
            <p style={{ fontSize: 11, color: headerColor, margin: 0, fontWeight: 600 }}>
              {warnCount > 0
                ? `${warnCount} need attention`
                : activeCount > 0
                  ? `${activeCount} worker${activeCount > 1 ? 's' : ''} active`
                  : 'Standby'}
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Activity indicator */}
          {department.isActive && !warnCount && (
            <motion.div
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              style={{ width: 8, height: 8, borderRadius: '50%', background: '#3d5af1' }}
            />
          )}
          {warnCount > 0 && (
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }} />
          )}
          <div style={{ color: '#8b8fa8' }}>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </div>
      </button>

      {/* Workers grid */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            {department.workers.length === 0 ? (
              <div style={{ padding: '12px 16px', textAlign: 'center' }}>
                <p style={{ fontSize: 12, color: '#8b8fa8' }}>No live data yet — workers will appear when active.</p>
              </div>
            ) : (
              <div style={{ padding: '14px 16px', display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                {department.workers.map(worker => (
                  <WorkerAvatar key={worker.id} worker={worker} size="sm" />
                ))}
              </div>
            )}

            {/* Worker status lines */}
            <div style={{ padding: '0 16px 12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {department.workers.map(worker => (
                <div key={worker.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12 }}>{worker.emoji}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#1a1c3a', minWidth: 90 }}>{worker.label}</span>
                  <span style={{ fontSize: 11, color: '#8b8fa8' }}>—</span>
                  <span style={{ fontSize: 11, color: '#6b7280', flex: 1 }}>{worker.statusLine}</span>
                  {worker.latency != null && (
                    <span style={{ fontSize: 10, color: '#9ca3af' }}>{worker.latency}ms</span>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
