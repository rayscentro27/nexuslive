import React from 'react';
import { Bell, Search, Command, Activity, Globe, ChevronDown, ShieldCheck } from 'lucide-react';

export function AdminHeader() {
  return (
    <header
      className="flex items-center shrink-0 sticky top-0 z-40 bg-white border-b border-[#e8e9f2]"
      style={{ height: 56, padding: '0 20px', gap: 12 }}
    >
      {/* ADMIN PORTAL label */}
      <div className="hidden md:flex items-center gap-2 mr-2">
        <ShieldCheck size={15} style={{ color: '#1a1c3a' }} />
        <span
          style={{
            fontSize: 11,
            fontWeight: 800,
            color: '#1a1c3a',
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
          }}
        >
          Admin Portal
        </span>
        <span
          style={{
            width: 1,
            height: 16,
            background: '#e8e9f2',
            display: 'inline-block',
            marginLeft: 6,
          }}
        />
      </div>

      {/* Search */}
      <div className="relative group hidden sm:block" style={{ flex: '0 1 300px' }}>
        <Search
          size={14}
          style={{
            position: 'absolute',
            left: 10,
            top: '50%',
            transform: 'translateY(-50%)',
            color: '#8b8fa8',
          }}
        />
        <input
          type="text"
          placeholder="Search clients, logs, docs..."
          style={{
            background: '#eaebf6',
            border: '1px solid #e8e9f2',
            borderRadius: 10,
            padding: '7px 36px 7px 32px',
            fontSize: 13,
            color: '#1a1c3a',
            width: '100%',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />
        <div
          style={{
            position: 'absolute',
            right: 8,
            top: '50%',
            transform: 'translateY(-50%)',
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            background: '#ffffff',
            border: '1px solid #e8e9f2',
            borderRadius: 5,
            padding: '1px 5px',
          }}
        >
          <Command size={9} style={{ color: '#8b8fa8' }} />
          <span style={{ fontSize: 9, fontWeight: 700, color: '#8b8fa8' }}>K</span>
        </div>
      </div>

      {/* Status indicators */}
      <div className="hidden lg:flex items-center gap-5" style={{ marginLeft: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: '#22c55e',
              display: 'inline-block',
              animation: 'pulse 2s infinite',
            }}
          />
          <span style={{ fontSize: 10, fontWeight: 700, color: '#8b8fa8', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            System Live
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Activity size={13} style={{ color: '#3d5af1' }} />
          <span style={{ fontSize: 10, fontWeight: 700, color: '#8b8fa8', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            98.2% Efficiency
          </span>
        </div>
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Right controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>

        {/* Environment pill */}
        <div
          className="hidden sm:flex items-center gap-1.5"
          style={{
            background: '#eaebf6',
            border: '1px solid #e8e9f2',
            borderRadius: 8,
            padding: '5px 10px',
          }}
        >
          <Globe size={12} style={{ color: '#8b8fa8' }} />
          <span style={{ fontSize: 10, fontWeight: 700, color: '#8b8fa8', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            Production
          </span>
        </div>

        {/* Bell */}
        <button
          style={{
            background: '#eaebf6',
            border: 'none',
            borderRadius: 8,
            padding: '8px 10px',
            cursor: 'pointer',
            position: 'relative',
          }}
        >
          <Bell size={15} style={{ color: '#8b8fa8' }} />
          <span
            style={{
              position: 'absolute',
              top: 7,
              right: 7,
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: '#3d5af1',
              border: '1.5px solid #fff',
            }}
          />
        </button>

        {/* Divider */}
        <span style={{ width: 1, height: 20, background: '#e8e9f2', display: 'inline-block', margin: '0 4px' }} />

        {/* Admin user button */}
        <button
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '4px 0',
            fontFamily: 'inherit',
          }}
        >
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', lineHeight: 1 }}>Admin Root</div>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#3d5af1', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 2 }}>
              Superuser
            </div>
          </div>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #1a1c3a, #3d5af1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              fontWeight: 700,
              color: '#fff',
              flexShrink: 0,
            }}
          >
            AR
          </div>
          <ChevronDown size={14} style={{ color: '#8b8fa8' }} />
        </button>
      </div>
    </header>
  );
}
