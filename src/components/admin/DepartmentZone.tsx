import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, ChevronUp, Clock, AlertTriangle } from 'lucide-react';
import { WorkerAvatar } from './WorkerAvatar';
import type { DepartmentStatus } from './workforce_state_adapter';

interface Props {
  department: DepartmentStatus;
  defaultExpanded?: boolean;
}

function ActivityBar({ isActive, color = '#3d5af1' }: { isActive: boolean; color?: string }) {
  if (!isActive) return null;
  return (
    <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 16 }}>
      {[0.4, 0.7, 1, 0.6, 0.9].map((h, i) => (
        <motion.div
          key={i}
          animate={{ scaleY: [h, h * 0.4, h, h * 1.2, h] }}
          transition={{ duration: 0.8 + i * 0.15, repeat: Infinity, ease: 'easeInOut', delay: i * 0.12 }}
          style={{
            width: 2, background: color, borderRadius: 2,
            height: `${h * 100}%`, transformOrigin: 'bottom',
            opacity: 0.8,
          }}
        />
      ))}
    </div>
  );
}

export function DepartmentZone({ department, defaultExpanded = true }: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const activeCount = department.workers.filter(w =>
    w.state === 'active' || w.state === 'researching' || w.state === 'analyzing'
  ).length;
  const warnCount = department.workers.filter(w => w.state === 'warning' || w.state === 'offline').length;
  const researchingCount = department.workers.filter(w => w.state === 'researching').length;

  const headerColor = warnCount > 0 ? '#f59e0b' : department.isActive ? '#3d5af1' : '#8b8fa8';
  const headerBg = warnCount > 0 ? '#fffbeb' : department.isActive ? '#f0f1ff' : '#f9fafb';
  const borderColor = warnCount > 0 ? '#fde68a' : department.isActive ? '#c7d2fe' : '#e5e7eb';

  const statusText = warnCount > 0
    ? `${warnCount} need attention`
    : researchingCount > 0
      ? `${researchingCount} researching`
      : activeCount > 0
        ? `${activeCount} active`
        : 'Standby';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        borderRadius: 14,
        border: `1.5px solid ${borderColor}`,
        overflow: 'hidden',
        background: '#fff',
        boxShadow: department.isActive ? `0 2px 12px rgba(61,90,241,0.06)` : 'none',
      }}
    >
      {/* Department header */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%', padding: '11px 14px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: headerBg, border: 'none', cursor: 'pointer',
          transition: 'background 0.15s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: department.isActive ? 'rgba(61,90,241,0.12)' : '#f3f4f6',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 17,
            border: department.isActive ? '1px solid rgba(61,90,241,0.2)' : '1px solid #e5e7eb',
          }}>
            {department.emoji}
          </div>
          <div style={{ textAlign: 'left' }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{department.name}</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              {warnCount > 0 && <AlertTriangle size={10} color="#f59e0b" />}
              {researchingCount > 0 && !warnCount && (
                <motion.div
                  animate={{ opacity: [1, 0.4, 1] }}
                  transition={{ duration: 1.2, repeat: Infinity }}
                  style={{ width: 5, height: 5, borderRadius: '50%', background: '#7c3aed' }}
                />
              )}
              <p style={{ fontSize: 11, color: headerColor, margin: 0, fontWeight: 600 }}>
                {statusText}
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Live activity bars */}
          <ActivityBar isActive={department.isActive && !warnCount} color={researchingCount > 0 ? '#7c3aed' : '#3d5af1'} />

          {/* Worker count badge */}
          {department.workers.length > 0 && (
            <div style={{
              background: department.isActive ? 'rgba(61,90,241,0.12)' : '#f3f4f6',
              color: department.isActive ? '#3d5af1' : '#6b7280',
              borderRadius: 10, padding: '2px 8px',
              fontSize: 11, fontWeight: 700,
              border: department.isActive ? '1px solid rgba(61,90,241,0.2)' : '1px solid #e5e7eb',
            }}>
              {department.workers.length}
            </div>
          )}

          <div style={{ color: '#9ca3af' }}>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </div>
      </button>

      {/* Workers expanded panel */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            style={{ overflow: 'hidden' }}
          >
            {department.workers.length === 0 ? (
              <div style={{ padding: '10px 14px', textAlign: 'center' }}>
                <p style={{ fontSize: 12, color: '#8b8fa8', margin: 0 }}>No live data — workers appear when active.</p>
              </div>
            ) : (
              <>
                {/* Avatars row */}
                <div style={{ padding: '12px 14px 8px', display: 'flex', flexWrap: 'wrap', gap: 14 }}>
                  {department.workers.map((worker, idx) => (
                    <motion.div
                      key={worker.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                    >
                      <WorkerAvatar worker={worker} size="sm" />
                    </motion.div>
                  ))}
                </div>

                {/* Status lines */}
                <div style={{ padding: '0 14px 10px', display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {department.workers.map(worker => {
                    const isResearching = worker.state === 'researching';
                    const isWarning = worker.state === 'warning' || worker.state === 'offline';
                    return (
                      <div key={worker.id} style={{
                        display: 'flex', alignItems: 'center', gap: 7,
                        padding: '4px 8px', borderRadius: 6,
                        background: isResearching ? 'rgba(124,58,237,0.05)'
                          : isWarning ? 'rgba(245,158,11,0.05)'
                          : 'transparent',
                      }}>
                        <span style={{ fontSize: 11 }}>{worker.emoji}</span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#1a1c3a', minWidth: 88, flexShrink: 0 }}>{worker.label}</span>
                        <span style={{ fontSize: 11, color: '#d1d5db' }}>—</span>
                        <span style={{ fontSize: 11, color: '#6b7280', flex: 1 }}>{worker.statusLine}</span>
                        {worker.latency != null && (
                          <span style={{ fontSize: 10, color: '#9ca3af', flexShrink: 0 }}>{worker.latency}ms</span>
                        )}
                        {isResearching && (
                          <motion.div
                            animate={{ opacity: [1, 0.3, 1] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                            style={{ width: 4, height: 4, borderRadius: '50%', background: '#7c3aed', flexShrink: 0 }}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
