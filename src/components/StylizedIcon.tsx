import React from 'react';
import { cn } from '../lib/utils';

interface StylizedIconProps {
  name: 'gift' | 'card' | 'star-trophy' | 'cup' | 'scroll' | 'award';
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function StylizedIcon({ name, className, size = 'md' }: StylizedIconProps) {
  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-20 h-20',
    lg: 'w-32 h-32',
    xl: 'w-48 h-48',
  };

  const renderIcon = () => {
    switch (name) {
      case 'gift':
        return (
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Shadow */}
            <rect x="25" y="35" width="60" height="50" rx="8" fill="black" fillOpacity="0.1" transform="translate(4, 4)" />
            {/* Box Body */}
            <rect x="20" y="30" width="60" height="55" rx="10" fill="#9F7AEA" />
            <rect x="20" y="30" width="60" height="15" rx="10" fill="#B794F4" />
            {/* Ribbon Vertical */}
            <rect x="45" y="30" width="10" height="55" fill="#F6AD55" />
            {/* Ribbon Horizontal */}
            <rect x="20" y="50" width="60" height="8" fill="#F6AD55" />
            {/* Bow */}
            <path d="M50 30C40 20 30 20 35 30C40 40 50 30 50 30Z" fill="#F6AD55" stroke="#DD6B20" strokeWidth="1" />
            <path d="M50 30C60 20 70 20 65 30C60 40 50 30 50 30Z" fill="#F6AD55" stroke="#DD6B20" strokeWidth="1" />
            {/* Medal */}
            <circle cx="50" cy="50" r="12" fill="#FBBF24" stroke="#D97706" strokeWidth="2" />
            <path d="M50 42L53 48H59L54 52L56 58L50 54L44 58L46 52L41 48H47L50 42Z" fill="white" />
            {/* Highlights */}
            <rect x="25" y="35" width="10" height="4" rx="2" fill="white" fillOpacity="0.3" />
          </svg>
        );
      case 'card':
        return (
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Shadow */}
            <rect x="15" y="35" width="70" height="45" rx="8" fill="black" fillOpacity="0.1" transform="translate(4, 4)" />
            {/* Card Body */}
            <rect x="15" y="30" width="70" height="45" rx="10" fill="#9F7AEA" />
            <rect x="15" y="30" width="70" height="10" rx="10" fill="#B794F4" />
            {/* Ribbon */}
            <rect x="35" y="30" width="8" height="45" fill="#FBBF24" />
            <rect x="15" y="45" width="70" height="6" fill="#FBBF24" />
            {/* Bow */}
            <path d="M39 48C35 40 30 40 33 48C36 56 39 48 39 48Z" fill="#FBBF24" />
            <path d="M39 48C43 40 48 40 45 48C42 56 39 48 39 48Z" fill="#FBBF24" />
            {/* Numbers/Details */}
            <rect x="65" y="60" width="12" height="4" rx="2" fill="white" fillOpacity="0.5" />
            <circle cx="68" cy="62" r="1.5" fill="white" />
            <circle cx="74" cy="62" r="1.5" fill="white" />
            {/* Highlights */}
            <rect x="20" y="35" width="15" height="3" rx="1.5" fill="white" fillOpacity="0.3" />
          </svg>
        );
      case 'star-trophy':
        return (
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Shadow */}
            <rect x="30" y="75" width="40" height="12" rx="4" fill="black" fillOpacity="0.1" transform="translate(4, 4)" />
            {/* Base */}
            <rect x="30" y="75" width="40" height="12" rx="6" fill="#805AD5" />
            <rect x="35" y="77" width="30" height="4" rx="2" fill="#FBBF24" />
            {/* Stem */}
            <rect x="46" y="55" width="8" height="20" fill="#FBBF24" />
            {/* Star */}
            <path d="M50 15L58 35H78L62 48L68 68L50 55L32 68L38 48L22 35H42L50 15Z" fill="#FBBF24" stroke="#D97706" strokeWidth="2" />
            {/* Highlights */}
            <path d="M50 20L54 32H65L56 40L59 52L50 45L41 52L44 40L35 32H46L50 20Z" fill="white" fillOpacity="0.3" />
          </svg>
        );
      case 'cup':
        return (
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Shadow */}
            <rect x="30" y="80" width="40" height="12" rx="4" fill="black" fillOpacity="0.1" transform="translate(4, 4)" />
            {/* Base */}
            <rect x="30" y="80" width="40" height="12" rx="6" fill="#805AD5" />
            <rect x="35" y="72" width="30" height="8" rx="4" fill="#B794F4" />
            {/* Cup */}
            <path d="M35 35C35 35 35 65 50 65C65 65 65 35 65 35H35Z" fill="#E2E8F0" stroke="#CBD5E0" strokeWidth="2" />
            {/* Handles */}
            <path d="M35 40C30 40 25 45 25 50C25 55 30 60 35 60" stroke="#CBD5E0" strokeWidth="3" fill="none" />
            <path d="M65 40C70 40 75 45 75 50C75 55 70 60 65 60" stroke="#CBD5E0" strokeWidth="3" fill="none" />
            {/* Star on Cup */}
            <path d="M50 40L53 46H59L54 50L56 56L50 52L44 56L46 50L41 46H47L50 40Z" fill="#FBBF24" />
            {/* Highlights */}
            <path d="M40 40C40 40 40 55 50 55" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.5" />
          </svg>
        );
      case 'scroll':
        return (
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Shadow */}
            <rect x="25" y="45" width="50" height="25" rx="4" fill="black" fillOpacity="0.1" transform="translate(4, 4)" />
            {/* Scroll Body */}
            <rect x="25" y="45" width="50" height="25" rx="10" fill="#EDF2F7" />
            <circle cx="25" cy="57.5" r="12.5" fill="#E2E8F0" />
            <circle cx="75" cy="57.5" r="12.5" fill="#E2E8F0" />
            {/* Ribbon */}
            <path d="M45 55L40 75L50 70L60 75L55 55" fill="#F6AD55" />
            {/* Seal */}
            <circle cx="50" cy="55" r="10" fill="#FBBF24" stroke="#D97706" strokeWidth="2" />
            <path d="M50 48L52 53H57L53 56L54 61L50 58L46 61L47 56L43 53H48L50 48Z" fill="white" />
          </svg>
        );
      case 'award':
        return (
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Shadow */}
            <rect x="35" y="80" width="30" height="10" rx="4" fill="black" fillOpacity="0.1" transform="translate(4, 4)" />
            {/* Base */}
            <rect x="35" y="80" width="30" height="10" rx="4" fill="#805AD5" />
            {/* Plaque */}
            <path d="M40 30L35 75H65L60 30H40Z" fill="#EDF2F7" stroke="#CBD5E0" strokeWidth="2" />
            <path d="M40 30L60 30L65 40L35 40L40 30Z" fill="white" opacity="0.5" />
            {/* Star */}
            <path d="M50 45L54 52H62L56 57L58 65L50 60L42 65L44 57L38 52H46L50 45Z" fill="#FBBF24" />
            {/* Details */}
            <rect x="45" y="68" width="10" height="2" rx="1" fill="#CBD5E0" />
            <rect x="47" y="72" width="6" height="2" rx="1" fill="#CBD5E0" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className={cn("relative flex items-center justify-center", sizeClasses[size], className)}>
      {renderIcon()}
    </div>
  );
}
