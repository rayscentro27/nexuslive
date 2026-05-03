import React from 'react';
import { X, ArrowRight, AlertCircle, Zap, MessageSquare, DollarSign, Award, TrendingUp } from 'lucide-react';
import { useNotifications } from '../contexts/NotificationContext';

const TYPE_CONFIG: Record<string, { icon: React.ElementType; border: string; iconColor: string }> = {
  urgent:       { icon: AlertCircle,   border: '#ef4444', iconColor: '#ef4444' },
  action:       { icon: Zap,           border: '#3d5af1', iconColor: '#3d5af1' },
  message:      { icon: MessageSquare, border: '#0ea5e9', iconColor: '#0ea5e9' },
  funding:      { icon: DollarSign,    border: '#22c55e', iconColor: '#22c55e' },
  grant:        { icon: Award,         border: '#f59e0b', iconColor: '#f59e0b' },
  trading:      { icon: TrendingUp,    border: '#8b5cf6', iconColor: '#8b5cf6' },
  ai:           { icon: Zap,           border: '#6366f1', iconColor: '#6366f1' },
  system:       { icon: AlertCircle,   border: '#8b8fa8', iconColor: '#8b8fa8' },
  subscription: { icon: AlertCircle,   border: '#ec4899', iconColor: '#ec4899' },
};

export function NotificationToasts() {
  const { toasts, dismissToast } = useNotifications();

  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed', top: 80, right: 16, zIndex: 1000,
      display: 'flex', flexDirection: 'column', gap: 10,
      maxWidth: 340,
      pointerEvents: 'none',
    }}>
      {toasts.map(toast => {
        const cfg = TYPE_CONFIG[toast.type] ?? TYPE_CONFIG.system;
        const Icon = cfg.icon;
        return (
          <div
            key={toast.toastId}
            style={{
              background: '#fff',
              borderRadius: 14,
              border: `1px solid ${cfg.border}30`,
              borderLeft: `3px solid ${cfg.border}`,
              boxShadow: '0 8px 32px rgba(60,80,180,0.12), 0 2px 8px rgba(0,0,0,0.06)',
              padding: '12px 14px',
              display: 'flex', gap: 10, alignItems: 'flex-start',
              pointerEvents: 'all',
              animation: 'slideInRight 0.3s ease-out',
            }}
          >
            <div style={{ color: cfg.iconColor, flexShrink: 0, marginTop: 1 }}>
              <Icon size={16} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{toast.title}</p>
              {toast.body && (
                <p style={{ fontSize: 12, color: '#8b8fa8', margin: '2px 0 0', lineHeight: 1.4 }}>{toast.body}</p>
              )}
              {toast.action_url && toast.action_label && (
                <span style={{ fontSize: 11, color: '#3d5af1', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 3, marginTop: 4 }}>
                  {toast.action_label} <ArrowRight size={10} />
                </span>
              )}
            </div>
            <button
              onClick={() => dismissToast(toast.toastId)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8', padding: 2, flexShrink: 0 }}
            >
              <X size={13} />
            </button>
          </div>
        );
      })}
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
