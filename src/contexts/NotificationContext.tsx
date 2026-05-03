import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../components/AuthProvider';

export interface Notification {
  id: string;
  user_id: string;
  type: 'action' | 'system' | 'ai' | 'urgent' | 'message' | 'funding' | 'grant' | 'trading' | 'subscription';
  title: string;
  body: string | null;
  action_url: string | null;
  action_label: string | null;
  priority: number;
  read_at: string | null;
  dismissed_at: string | null;
  created_at: string;
}

interface ToastNotification extends Notification {
  toastId: string;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  toasts: ToastNotification[];
  loading: boolean;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  dismiss: (id: string) => Promise<void>;
  dismissToast: (toastId: string) => void;
  createNotification: (n: Omit<Notification, 'id' | 'user_id' | 'created_at' | 'read_at' | 'dismissed_at'>) => Promise<void>;
  refresh: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const channelRef = useRef<ReturnType<typeof supabase.channel> | null>(null);

  const unreadCount = notifications.filter(n => !n.read_at && !n.dismissed_at).length;

  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    const { data } = await supabase
      .from('notifications')
      .select('*')
      .eq('user_id', user.id)
      .is('dismissed_at', null)
      .order('created_at', { ascending: false })
      .limit(50);
    if (data) setNotifications(data as Notification[]);
    setLoading(false);
  }, [user]);

  useEffect(() => {
    if (!user) { setNotifications([]); return; }
    fetchNotifications();

    // Real-time subscription
    const channel = supabase
      .channel(`notifications:${user.id}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'notifications',
        filter: `user_id=eq.${user.id}`,
      }, (payload) => {
        const newNotif = payload.new as Notification;
        setNotifications(prev => [newNotif, ...prev]);
        // Show as toast for priority >= 2
        if (newNotif.priority >= 2) {
          const toastId = `${newNotif.id}-${Date.now()}`;
          setToasts(prev => [...prev, { ...newNotif, toastId }]);
          setTimeout(() => setToasts(prev => prev.filter(t => t.toastId !== toastId)), 5000);
        }
      })
      .subscribe();

    channelRef.current = channel;
    return () => { channel.unsubscribe(); };
  }, [user, fetchNotifications]);

  const markRead = useCallback(async (id: string) => {
    const readAt = new Date().toISOString();
    await supabase.from('notifications').update({ read_at: readAt }).eq('id', id);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read_at: readAt } : n));
  }, []);

  const markAllRead = useCallback(async () => {
    if (!user) return;
    const readAt = new Date().toISOString();
    await supabase.from('notifications').update({ read_at: readAt }).eq('user_id', user.id).is('read_at', null);
    setNotifications(prev => prev.map(n => ({ ...n, read_at: n.read_at ?? readAt })));
  }, [user]);

  const dismiss = useCallback(async (id: string) => {
    const dismissedAt = new Date().toISOString();
    await supabase.from('notifications').update({ dismissed_at: dismissedAt }).eq('id', id);
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const dismissToast = useCallback((toastId: string) => {
    setToasts(prev => prev.filter(t => t.toastId !== toastId));
  }, []);

  const createNotification = useCallback(async (
    n: Omit<Notification, 'id' | 'user_id' | 'created_at' | 'read_at' | 'dismissed_at'>
  ) => {
    if (!user) return;
    await supabase.from('notifications').insert({ ...n, user_id: user.id });
  }, [user]);

  return (
    <NotificationContext.Provider value={{
      notifications, unreadCount, toasts, loading,
      markRead, markAllRead, dismiss, dismissToast,
      createNotification, refresh: fetchNotifications,
    }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotifications must be inside NotificationProvider');
  return ctx;
}
