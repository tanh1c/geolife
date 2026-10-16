import React from 'react';

export interface LiquidGlassButtonProps {
  label?: string;
  onClick?: () => void;
  className?: string;
  width?: string;
  height?: string;
  transparencyRange?: string; // --tr
  size?: 'sm' | 'md' | 'lg' | 'full' | 'responsive';
  variant?: 'default' | 'turquoise';
  icon?: React.ReactNode;
  ariaLabel?: string;
  disabled?: boolean;
}

/**
 * Standard Liquid Glass Caustic Button Component
 * Fully responsive recreation of optical liquid glass with specular highlights and caustics
 */
export const LiquidGlassButton: React.FC<LiquidGlassButtonProps> = ({
  label = 'Get started',
  onClick,
  className = '',
  width,
  height,
  transparencyRange = '15%',
  size = 'responsive',
  variant = 'default',
  icon,
  ariaLabel,
  disabled = false,
}) => {
  // Compute default responsive dimensions based on size
  const defaultW =
    size === 'sm'
      ? '180px'
      : size === 'md'
      ? '220px'
      : size === 'lg'
      ? '280px'
      : size === 'full'
      ? '100%'
      : 'min(260px, 92vw)';

  const defaultH =
    size === 'sm'
      ? '48px'
      : size === 'md'
      ? '58px'
      : size === 'lg'
      ? '72px'
      : size === 'full'
      ? '56px'
      : '70px';

  const w = width || defaultW;
  const h = height || defaultH;

  const styleObj = {
    '--w': w,
    '--h': h,
    '--tr': transparencyRange,
  } as React.CSSProperties;

  return (
    <div className={`lq-container lq-fx-layer ${size === 'full' ? 'w-full' : ''} ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        aria-label={ariaLabel || label}
        className={`box start-btn lq-glass-box focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] focus-visible:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none ${
          size === 'sm' ? 'size-sm' : size === 'md' ? 'size-md' : size === 'lg' ? 'size-lg' : size === 'full' ? 'size-full' : ''
        } ${variant === 'turquoise' ? 'brand-turquoise' : ''}`}
        style={styleObj}
      >
        <span className="text lq-text select-none">{label}</span>
        
        <div className="btn-icon">
          {icon ? (
            icon
          ) : (
            <svg
              className="svg"
              viewBox="0 0 1024 1024"
              version="1.1"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path d="M779.180132 473.232045 322.354755 16.406668c-21.413706-21.413706-56.121182-21.413706-77.534887 0-21.413706 21.413706-21.413706 56.122205 0 77.534887l418.057421 418.057421L244.819868 930.057421c-21.413706 21.413706-21.413706 56.122205 0 77.534887 10.706853 10.706853 24.759917 16.059767 38.767955 16.059767s28.061103-5.353938 38.767955-16.059767L779.180132 550.767955C800.593837 529.35425 800.593837 494.64575 779.180132 473.232045z" />
            </svg>
          )}
        </div>

        <div className="circle-overlay" />
      </button>
    </div>
  );
};
