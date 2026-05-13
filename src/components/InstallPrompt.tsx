import { useState, useEffect } from 'react';
import { useAnalytics } from '../hooks/useAnalytics';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export default function InstallPrompt() {
  const { emit } = useAnalytics();
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      const dismissed = sessionStorage.getItem('pwa-install-dismissed');
      if (!dismissed) setVisible(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') emit('app_installed', { event_name: 'pwa_installed', feature: 'dashboard' });
    if (outcome === 'dismissed') sessionStorage.setItem('pwa-install-dismissed', '1');
    setVisible(false);
    setDeferredPrompt(null);
  };

  const handleDismiss = () => {
    sessionStorage.setItem('pwa-install-dismissed', '1');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="banner"
      aria-label="Install Nexus app"
      style={{
        position: 'fixed',
        bottom: '1rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9999,
        background: '#1E293B',
        border: '1px solid #334155',
        borderRadius: '12px',
        padding: '0.875rem 1.25rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.875rem',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        maxWidth: '360px',
        width: 'calc(100vw - 2rem)',
      }}
    >
      <img src="/icons/icon-192.png" alt="Nexus" style={{ width: 40, height: 40, borderRadius: 8, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: '#F1F5F9', fontWeight: 600, fontSize: '0.875rem' }}>Install Nexus</div>
        <div style={{ color: '#94A3B8', fontSize: '0.75rem', marginTop: 2 }}>Add to your home screen for quick access</div>
      </div>
      <button
        onClick={handleInstall}
        style={{
          background: '#6366F1',
          color: '#fff',
          border: 'none',
          borderRadius: 8,
          padding: '0.5rem 0.875rem',
          fontSize: '0.8125rem',
          fontWeight: 600,
          cursor: 'pointer',
          flexShrink: 0,
        }}
      >
        Install
      </button>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss install prompt"
        style={{
          background: 'transparent',
          border: 'none',
          color: '#64748B',
          cursor: 'pointer',
          padding: '0.25rem',
          fontSize: '1.125rem',
          lineHeight: 1,
          flexShrink: 0,
        }}
      >
        ×
      </button>
    </div>
  );
}
