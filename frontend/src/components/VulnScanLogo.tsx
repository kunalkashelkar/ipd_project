import React from 'react';
import { Link } from 'react-router-dom';

export interface VulnScanLogoProps {
  variant?: 'full' | 'icon' | 'compact' | 'wordmark';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  className?: string;
  showSubtitle?: boolean;
  subtitle?: string;
  linkTo?: string;
}

const sizeMap = {
  xs: { icon: 'h-5 w-5', text: 'text-xs', sub: 'text-[9px]' },
  sm: { icon: 'h-7 w-7', text: 'text-sm', sub: 'text-[10px]' },
  md: { icon: 'h-8 w-8', text: 'text-base', sub: 'text-[11px]' },
  lg: { icon: 'h-10 w-10', text: 'text-lg', sub: 'text-xs' },
  xl: { icon: 'h-12 w-12', text: 'text-xl', sub: 'text-xs' },
  '2xl': { icon: 'h-16 w-16', text: 'text-2xl', sub: 'text-sm' },
};

export const VulnScanLogo: React.FC<VulnScanLogoProps> = ({
  variant = 'full',
  size = 'md',
  className = '',
  showSubtitle = false,
  subtitle = 'Security Intelligence',
  linkTo,
}) => {
  const currentSize = sizeMap[size] || sizeMap.md;

  const content = (
    <div className={`inline-flex items-center gap-2.5 select-none ${className}`}>
      {variant !== 'wordmark' && (
        <div className={`relative flex items-center justify-center shrink-0 ${currentSize.icon}`}>
          <img
            src="/logo.png"
            alt="VulnScan"
            className="w-full h-full object-contain filter drop-shadow-[0_2px_8px_rgba(234,88,12,0.25)] transition-transform duration-200 group-hover:scale-105"
            onError={(e) => {
              // Fallback to stylized vector emblem if image path fails
              const target = e.currentTarget;
              target.style.display = 'none';
              const parent = target.parentElement;
              if (parent && !parent.querySelector('.logo-fallback')) {
                const fallback = document.createElement('div');
                fallback.className = 'logo-fallback w-full h-full rounded-lg bg-gradient-to-br from-amber-500 via-orange-600 to-purple-800 flex items-center justify-center text-white font-bold font-mono text-xs shadow-md';
                fallback.innerText = 'V';
                parent.appendChild(fallback);
              }
            }}
          />
        </div>
      )}

      {variant !== 'icon' && (
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-1.5">
            <span
              className={`font-display font-bold tracking-tight text-foreground ${currentSize.text} leading-none`}
            >
              Vuln<span className="bg-gradient-to-r from-orange-500 via-amber-400 to-cyan-400 bg-clip-text text-transparent">Scan</span>
            </span>
          </div>
          {showSubtitle && variant === 'full' && (
            <span className={`text-muted-foreground font-mono font-medium tracking-wider uppercase mt-0.5 ${currentSize.sub}`}>
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (linkTo) {
    return (
      <Link to={linkTo} className="inline-flex group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-md">
        {content}
      </Link>
    );
  }

  return content;
};

export default VulnScanLogo;
