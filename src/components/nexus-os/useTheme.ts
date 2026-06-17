/**
 * useTheme — Nexus OS theme (dark default + light), persisted in localStorage.
 * Applies data-nexus-theme to <html> so CSS token blocks switch. Layout is
 * identical between themes — only color tokens change.
 */
import { useCallback, useEffect, useState } from 'react';

export type NexusTheme = 'dark' | 'light';
const KEY = 'nexus-os-theme';

function readSaved(): NexusTheme {
  if (typeof window === 'undefined') return 'dark';
  const saved = window.localStorage.getItem(KEY);
  return saved === 'light' ? 'light' : 'dark'; // default dark
}

function apply(theme: NexusTheme) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-nexus-theme', theme);
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<NexusTheme>(readSaved);

  useEffect(() => { apply(theme); }, [theme]);

  const setTheme = useCallback((t: NexusTheme) => {
    setThemeState(t);
    try { window.localStorage.setItem(KEY, t); } catch { /* ignore */ }
    apply(t);
  }, []);

  const toggle = useCallback(() => {
    setThemeState(prev => {
      const next = prev === 'dark' ? 'light' : 'dark';
      try { window.localStorage.setItem(KEY, next); } catch { /* ignore */ }
      apply(next);
      return next;
    });
  }, []);

  return { theme, setTheme, toggle };
}
