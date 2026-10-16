import React from 'react';

export interface PrismaticGlassButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  label?: string;
  icon?: React.ReactNode;
  variant?: 'prismatic' | 'turquoise' | 'dark';
  size?: 'sm' | 'md' | 'lg' | 'full';
  className?: string;
  withDottedGrid?: boolean;
}

/**
 * Prismatic Refractive Liquid Glass Button
 * Features:
 * - Dynamic animated specular streak with mix-blend-mode: screen
 * - Caustic conic-gradient border ring with mask cutout
 * - 3D tactile tilt on active (rotate3d)
 * - Directional liquid blur shadow with masked exclusion
 * - Fully responsive & mobile-friendly touch ergonomics
 */
export const PrismaticGlassButton: React.FC<PrismaticGlassButtonProps> = ({
  label = 'Generate',
  icon,
  variant = 'prismatic',
  size = 'md',
  className = '',
  withDottedGrid = false,
  children,
  disabled = false,
  onClick,
  ...props
}) => {
  return (
    <div
      className={`prismatic-wrap ${size === 'full' ? 'w-full' : ''} ${
        size === 'sm'
          ? 'size-sm'
          : size === 'md'
          ? 'size-md'
          : size === 'lg'
          ? 'size-lg'
          : 'size-full'
      } ${className}`}
    >
      {withDottedGrid && (
        <svg
          style={{ position: 'absolute', width: '100%', height: '100%', zIndex: 0 }}
          width="100%"
          height="100%"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <defs>
            <pattern id="dottedGrid" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1" fill="rgba(0,0,0,0.12)" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#dottedGrid)" />
        </svg>
      )}

      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className={`prismatic-btn ${variant === 'turquoise' ? 'variant-turquoise' : ''} ${
          disabled ? 'opacity-50 pointer-events-none' : ''
        }`}
        {...props}
      >
        <span className="prismatic-btn-text">
          {icon && <span className="shrink-0">{icon}</span>}
          <span>{children || label}</span>
        </span>
      </button>

      <div className="prismatic-shadow" aria-hidden="true" />
    </div>
  );
};
