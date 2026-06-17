import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from './useTheme';

/** Compact dark/light toggle. Default dark; persists to localStorage. */
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';
  return (
    <button
      onClick={toggle}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label="Toggle theme"
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all"
      style={{
        background: 'var(--nexus-surface)',
        border: '1px solid var(--nexus-border)',
        color: 'var(--nexus-text-muted)',
      }}
    >
      {isDark ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
      <span className="hidden sm:inline">{isDark ? 'Dark' : 'Light'}</span>
    </button>
  );
}
