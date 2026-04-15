import React from 'react';
import { cn } from '../lib/utils';

interface ThreeDIconProps {
  name: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: string;
}

export function ThreeDIcon({ name, className, size = 'md', color = '#5B7CFA' }: ThreeDIconProps) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
    xl: 'w-20 h-20',
  };

  const iconSize = {
    sm: 14,
    md: 20,
    lg: 28,
    xl: 40,
  };

  // Map icon names to specific 3D SVG implementations
  const renderIcon = () => {
    switch (name) {
      case 'home':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 9.5L12 3L21 9.5V19C21 20.1046 20.1046 21 19 21H5C3.89543 21 3 20.1046 3 19V9.5Z" fill={`url(#grad-home-${color})`} />
            <path d="M9 21V12H15V21" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <defs>
              <linearGradient id={`grad-home-${color}`} x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                <stop stopColor={color} />
                <stop offset="1" stopColor={color} stopOpacity="0.6" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'rocket':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4.5 16.5C4.5 16.5 3 19.5 3 21C3 21 6 19.5 7.5 19.5" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M12 15L9 18L4.5 16.5L12 15Z" fill={color} fillOpacity="0.2" />
            <path d="M15 12L18 9L19.5 4.5L15 12Z" fill={color} fillOpacity="0.2" />
            <path d="M9 15L15 9C15 9 18.5 6.5 21 3C21 3 17.5 6.5 15 9L9 15Z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M9 15C9 15 6.5 18.5 3 21C3 21 6.5 17.5 9 15Z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="15" cy="9" r="2" fill="white" />
          </svg>
        );
      case 'messages':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 11.5C21 15.6421 16.9706 19 12 19C10.6015 19 9.28101 18.735 8.11479 18.2619L3 20L4.5 15.5C3.55551 14.3499 3 12.986 3 11.5C3 7.35786 7.02944 4 12 4C16.9706 4 21 7.35786 21 11.5Z" fill={`url(#grad-msg-${color})`} />
            <circle cx="8" cy="11.5" r="1" fill="white" />
            <circle cx="12" cy="11.5" r="1" fill="white" />
            <circle cx="16" cy="11.5" r="1" fill="white" />
            <defs>
              <linearGradient id={`grad-msg-${color}`} x1="3" y1="4" x2="21" y2="19" gradientUnits="userSpaceOnUse">
                <stop stopColor={color} />
                <stop offset="1" stopColor={color} stopOpacity="0.7" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'documents':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 2H6C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V9L13 2Z" fill={`url(#grad-doc-${color})`} />
            <path d="M13 2V9H20" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <defs>
              <linearGradient id={`grad-doc-${color}`} x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor={color} />
                <stop offset="1" stopColor={color} stopOpacity="0.7" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'funding':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="5" width="20" height="14" rx="2" fill={`url(#grad-fund-${color})`} />
            <path d="M2 10H22" stroke="white" strokeWidth="2" />
            <rect x="5" y="14" width="4" height="2" rx="1" fill="white" fillOpacity="0.5" />
            <defs>
              <linearGradient id={`grad-fund-${color}`} x1="2" y1="5" x2="22" y2="19" gradientUnits="userSpaceOnUse">
                <stop stopColor={color} />
                <stop offset="1" stopColor={color} stopOpacity="0.7" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'trading':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 17L9 11L13 15L21 7" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M21 7V13" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M21 7H15" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case 'grants':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="11" cy="11" r="8" stroke={color} strokeWidth="3" />
            <path d="M21 21L16.65 16.65" stroke={color} strokeWidth="3" strokeLinecap="round" />
            <circle cx="11" cy="11" r="3" fill={color} fillOpacity="0.2" />
          </svg>
        );
      case 'referral':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M17 21V19C17 17.9391 16.5786 16.9217 15.8284 16.1716C15.0783 15.4214 14.0609 15 13 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="9" cy="7" r="4" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M23 21V19C22.9993 18.1137 22.7044 17.2524 22.1614 16.5523C21.6184 15.8522 20.8581 15.3516 20 15.13" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M16 3.13C16.8604 3.35031 17.623 3.85071 18.1676 4.55232C18.7122 5.25392 19.0078 6.11683 19.0078 7.005C19.0078 7.89317 18.7122 8.75608 18.1676 9.45768C17.623 10.1593 16.8604 10.6597 16 10.88" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case 'account':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="12" cy="7" r="4" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case 'settings':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="3" fill={color} />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case 'credit':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M2 7C2 5.89543 2.89543 5 4 5H20C21.1046 5 22 5.89543 22 7V17C22 18.1046 21.1046 19 20 19H4C2.89543 19 2 18.1046 2 17V7Z" fill={`url(#grad-credit-${color})`} />
            <path d="M2 11H22" stroke="white" strokeWidth="2" />
            <rect x="5" y="14" width="3" height="2" rx="0.5" fill="white" fillOpacity="0.6" />
            <defs>
              <linearGradient id={`grad-credit-${color}`} x1="2" y1="5" x2="22" y2="19" gradientUnits="userSpaceOnUse">
                <stop stopColor={color} />
                <stop offset="1" stopColor={color} stopOpacity="0.7" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'shield':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 22C12 22 20 18 20 12V5L12 2L4 5V12C4 18 12 22 12 22Z" fill={`url(#grad-shield-${color})`} />
            <path d="M9 12L11 14L15 10" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <defs>
              <linearGradient id={`grad-shield-${color}`} x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor={color} />
                <stop offset="1" stopColor={color} stopOpacity="0.7" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'briefcase':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="7" width="20" height="14" rx="2" fill={`url(#grad-brief-${color})`} />
            <path d="M16 7V5C16 3.89543 15.1046 3 14 3H10C8.89543 3 8 3.89543 8 5V7" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <defs>
              <linearGradient id={`grad-brief-${color}`} x1="2" y1="7" x2="22" y2="21" gradientUnits="userSpaceOnUse">
                <stop stopColor={color} />
                <stop offset="1" stopColor={color} stopOpacity="0.7" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'search':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="11" cy="11" r="8" stroke={color} strokeWidth="3" />
            <path d="M21 21L16.65 16.65" stroke={color} strokeWidth="3" strokeLinecap="round" />
          </svg>
        );
      case 'clock':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" />
            <path d="M12 6V12L16 14" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case 'check':
        return (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#00D97E" />
            <path d="M8 12L11 15L16 9" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div 
      className={cn(
        "relative flex items-center justify-center rounded-2xl overflow-hidden transition-all duration-300",
        "bg-white/40 backdrop-blur-sm border border-white/40",
        "shadow-[0_4px_12px_rgba(0,0,0,0.05),inset_0_2px_4px_rgba(255,255,255,0.8)]",
        "hover:scale-110 hover:shadow-lg",
        sizeClasses[size],
        className
      )}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent pointer-events-none" />
      <div className="relative z-10 w-full h-full p-2">
        {renderIcon()}
      </div>
    </div>
  );
}
