import React from 'react';
import { TOKENS, MaterialVariant } from '../../styles/tokens';

export interface GlassSurfaceProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: MaterialVariant | 'service' | 'car' | 'food';
  intensity?: 'subtle' | 'medium' | 'strong';
  children?: React.ReactNode;
  className?: string;
}

/**
 * Core Liquid Glass V3 surface container
 */
export const GlassSurface = React.forwardRef<HTMLDivElement, GlassSurfaceProps>(
  ({ variant = 'card', intensity = 'medium', children, className = '', ...props }, ref) => {
    const variantClass =
      variant === 'dock'
        ? TOKENS.materials.dock
        : variant === 'dockActive'
        ? TOKENS.materials.dockActive
        : variant === 'button'
        ? TOKENS.materials.button
        : variant === 'pill'
        ? TOKENS.materials.pill
        : variant === 'input'
        ? TOKENS.materials.input
        : variant === 'car' || variant === 'cardCar'
        ? TOKENS.materials.cardCar
        : variant === 'food' || variant === 'cardFood'
        ? TOKENS.materials.cardFood
        : variant === 'service' || variant === 'cardService'
        ? TOKENS.materials.cardService
        : variant === 'routeBadge'
        ? TOKENS.materials.routeBadge
        : variant === 'solidPrimary'
        ? TOKENS.materials.solidPrimary
        : TOKENS.materials.card;

    return (
      <div
        ref={ref}
        className={`${variantClass} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
GlassSurface.displayName = 'GlassSurface';

export interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'standard' | 'pill' | 'subtle' | 'solidPrimary';
  children?: React.ReactNode;
  className?: string;
}

/**
 * Tactile Liquid Glass button with accessible focus and press interaction
 */
export const GlassButton = React.forwardRef<HTMLButtonElement, GlassButtonProps>(
  ({ variant = 'standard', children, className = '', disabled, ...props }, ref) => {
    const baseClass =
      variant === 'solidPrimary'
        ? 'solid-primary'
        : variant === 'pill'
        ? 'glass-pill'
        : 'glass-button';

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={`${baseClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] focus-visible:ring-offset-1 select-none cursor-pointer disabled:opacity-50 disabled:pointer-events-none ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);
GlassButton.displayName = 'GlassButton';

export interface GlassPillProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

/**
 * Compact floating context pill (used for map chips & indicators)
 */
export const GlassPill: React.FC<GlassPillProps> = ({
  children,
  className = '',
  onClick,
  ...props
}) => {
  return (
    <div
      onClick={onClick}
      className={`glass-pill select-none ${onClick ? 'cursor-pointer active:scale-95 transition-transform' : ''} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'car' | 'food' | 'service' | 'standard';
  children?: React.ReactNode;
  className?: string;
}

/**
 * Translucent glass card with directional specular reflections
 */
export const GlassCard: React.FC<GlassCardProps> = ({
  variant = 'standard',
  children,
  className = '',
  ...props
}) => {
  const cardClass =
    variant === 'car'
      ? 'glass-card-car'
      : variant === 'food'
      ? 'glass-card-food'
      : variant === 'service'
      ? 'glass-card-service'
      : 'glass-card';

  return (
    <div className={`${cardClass} select-none ${className}`} {...props}>
      {children}
    </div>
  );
};

export { LiquidGlassButton } from './LiquidGlassButton';
export type { LiquidGlassButtonProps } from './LiquidGlassButton';
export { PrismaticGlassButton } from './PrismaticGlassButton';
export type { PrismaticGlassButtonProps } from './PrismaticGlassButton';

