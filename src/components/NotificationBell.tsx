import React, { useState, useRef, useEffect } from 'react';
import { Bell, X, CheckCheck, ArrowRight, Zap, AlertCircle, MessageSquare, DollarSign, Award, TrendingUp, CreditCard } from 'lucide-react';
import { useNotifications, Notification } from '../contexts/NotificationContext';

const TYPE_META: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  action:       { icon: Zap,           color: '#3d5af1', bg: '#eef0fd' },
  system:       { icon: AlertCircle,   color: '#8b8fa8', bg: '#f7f8ff' },
  ai:           { icon: Zap,           color: '#6366f1', bg: '#ede9fe' },
  urgent:       { icon: AlertCircle,   color: '#ef4444', bg: '#fef2f2' },
  message:      { icon: MessageSquare, color: '#0ea5e9', bg: '#f0f9ff' },
  funding:      { icon: DollarSign,    color: '#22c55e', bg: '#f0fdf4' },
  grant:        { icon: Award,         color: '#f59e0b', bg: '#fffbeb' },
  trading:      { icon: TrendingUp,    color: '#8b5cf6', bg: '#f5f3ff' },
  subscription: { icon: CreditCard,    color: '#ec4899', bg: '#fdf2f8' },
};

function NotifIcon({ type }: { type: string }) {
  const meta = TYPE_META[type] ?? TYPE_META.system;
  const Icon = meta.icon;
  return (
    <div style={{
      width: 36, height: 36, borderRadius: 10,
      background: meta.bg, color: meta.color,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <Icon size={16} />
    </div>
  );
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function NotifItem({ n, onRead, onDismiss }: {
  n: Notification;
  onRead: () => void;
  onDismiss: () => void;
}) {
  const unread = !n.read_at;
  return (
    <div
      style={{
        padding: '10px 14px',
        background: unread ? '#fafbff' : 'transparent',
        borderBottom: '1px solid #f0f0f8',
        cursor: 'pointer',
        display: 'flex',
        gap: 10,
        alignItems: 'flex-start',
        transition: 'background 0.1s',
      }}
      onClick={onRead}
      onMouseEnter={e => (e.currentTarget.style.background = '#f0f4ff')}
      onMouseLeave={e => (e.currentTarget.style.background = unread ? '#fafbff' : 'transparent')}
    >
      <NotifIcon type={n.type} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <p style={{
            fontSize: 13, fontWeight: unread ? 700 : 600,
            color: '#1a1c3a', margin: 0,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{n.title}</p>
          <span style={{ fontSize: 11, color: '#8b8fa8', flexShrink: 0 }}>{timeAgo(n.created_at)}</span>
        </div>
        {n.body && (
          <p style={{ fontSize: 12, color: '#8b8fa8', margin: '2px 0 0', lineHeight: 1.4 }}>
            {n.body}
          </p>
        )}
        {n.action_url && n.action_label && (
          <span style={{ fontSize: 11, color: '#3d5af1', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 3, marginTop: 4 }}>
            {n.action_label} <ArrowRight size={10} />
          </span>
        )}
      </div>
      {unread && (
        <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#3d5af1', flexShrink: 0, marginTop: 4 }} />
      )}
      <button
        onClick={e => { e.stopPropagation(); onDismiss(); }}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8', padding: 2, flexShrink: 0 }}
      >
        <X size={12} />
      </button>
    </div>
  );
}

export function NotificationBell({ onOpenPage }: { onOpenPage?: () => void }) {
  const { notifications, unreadCount, markRead, markAllRead, dismiss } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const recent = notifications.slice(0, 10);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'relative',
          width: 40, height: 40,
          borderRadius: 12,
          background: open ? '#eef0fd' : 'rgba(255,255,255,0.7)',
          border: '1.5px solid rgba(255,255,255,0.6)',
          cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#1a1c3a',
          boxShadow: '0 2px 8px rgba(60,80,180,0.08)',
          transition: 'all 0.15s',
        }}
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <div style={{
            position: 'absolute', top: -4, right: -4,
            background: '#ef4444', color: '#fff',
            borderRadius: 10, fontSize: 10, fontWeight: 800,
            padding: '1px 5px', border: '2px solid #fff',
            minWidth: 18, textAlign: 'center',
          }}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </div>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 48, right: 0, zIndex: 500,
          width: 360,
          background: '#fff',
          borderRadius: 16,
          border: '1px solid #e8e9f2',
          boxShadow: '0 20px 60px rgba(60,80,180,0.15), 0 4px 16px rgba(0,0,0,0.06)',
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            padding: '14px 16px',
            borderBottom: '1px solid #f0f0f8',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h3 style={{ fontSize: 15, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Notifications</h3>
              {unreadCount > 0 && (
                <span style={{
                  background: '#3d5af1', color: '#fff',
                  borderRadius: 10, fontSize: 10, fontWeight: 800,
                  padding: '1px 7px',
                }}>{unreadCount}</span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: '#3d5af1', fontSize: 12, fontWeight: 700,
                    display: 'flex', alignItems: 'center', gap: 4,
                  }}
                >
                  <CheckCheck size={13} /> Mark all read
                </button>
              )}
            </div>
          </div>

          {/* List */}
          <div style={{ maxHeight: 380, overflowY: 'auto' }}>
            {recent.length === 0 ? (
              <div style={{ padding: '32px 16px', textAlign: 'center' }}>
                <Bell size={28} color="#c7d2fe" style={{ margin: '0 auto 8px' }} />
                <p style={{ fontSize: 13, color: '#8b8fa8', fontWeight: 500 }}>No notifications yet</p>
              </div>
            ) : (
              recent.map(n => (
                <NotifItem
                  key={n.id}
                  n={n}
                  onRead={() => markRead(n.id)}
                  onDismiss={() => dismiss(n.id)}
                />
              ))
            )}
          </div>

          {/* Footer */}
          {notifications.length > 10 && onOpenPage && (
            <div style={{ padding: '10px 16px', borderTop: '1px solid #f0f0f8' }}>
              <button
                onClick={() => { setOpen(false); onOpenPage(); }}
                style={{
                  width: '100%', padding: '8px 0', borderRadius: 10,
                  background: '#eef0fd', border: 'none', cursor: 'pointer',
                  fontSize: 13, fontWeight: 700, color: '#3d5af1',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                }}
              >
                View all notifications <ArrowRight size={13} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
