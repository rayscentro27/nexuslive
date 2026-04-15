import React from 'react';
import { cn } from '../lib/utils';

export type BotType = 'advisor' | 'dashboard' | 'setup' | 'funding' | 'trading' | 'grants' | 'referral';

interface BotAvatarProps {
  type: BotType;
  className?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

export const botConfig = {
  advisor: {
    name: 'Advisor',
    role: 'Capital Strategist',
    color: 'bg-blue-100',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=advisor&backgroundColor=b6e3f4',
    description: 'Expert guidance for your business journey.',
  },
  dashboard: {
    name: 'Dashboard Bot',
    role: 'Command Center',
    color: 'bg-blue-50',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=dashboard&backgroundColor=b6e3f4',
    description: 'Your central brain for all things Nexus.',
  },
  setup: {
    name: 'Setup Bot',
    role: 'Business Formation',
    color: 'bg-green-50',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=setup&backgroundColor=c1f4b6',
    description: 'Helping you build a solid business foundation.',
  },
  funding: {
    name: 'Funding Bot',
    role: 'Capital Strategist',
    color: 'bg-blue-50',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=funding&backgroundColor=b6e3f4',
    description: 'Unlocking capital opportunities for your growth.',
  },
  trading: {
    name: 'Trading Bot',
    role: 'Strategy & Signals',
    color: 'bg-indigo-50',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=trading&backgroundColor=b6e3f4',
    description: 'Smart signals and market strategies.',
  },
  grants: {
    name: 'Grants Bot',
    role: 'Grant Discovery',
    color: 'bg-purple-50',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=grants&backgroundColor=b6e3f4',
    description: 'Finding non-dilutive funding for your mission.',
  },
  referral: {
    name: 'Referral Bot',
    role: 'Growth & Rewards',
    color: 'bg-emerald-50',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=referral&backgroundColor=b6e3f4',
    description: 'Expanding the Nexus network together.',
  },
};

export function BotAvatar({ type, className, size = 'md' }: BotAvatarProps) {
  const config = botConfig[type];
  
  const sizeClasses = {
    xs: 'w-6 h-6 rounded-md',
    sm: 'w-8 h-8 rounded-lg',
    md: 'w-12 h-12 rounded-xl',
    lg: 'w-20 h-20 rounded-2xl',
    xl: 'w-32 h-32 rounded-[2rem]',
    '2xl': 'w-48 h-48 rounded-[3rem]',
  };

  return (
    <div className={cn(
      "relative shrink-0 overflow-hidden shadow-sm transition-all duration-300 hover:scale-105",
      config.color,
      sizeClasses[size],
      className
    )}>
      <img 
        src={config.avatar} 
        alt={config.name} 
        className="w-full h-full object-cover"
        referrerPolicy="no-referrer"
      />
    </div>
  );
}
