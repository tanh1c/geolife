import React, { useState } from 'react';
import { AssetId, getAssetUrl, ASSET_CATALOG } from '../../assets/assetRegistry';

export interface AssetImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  assetId: AssetId;
  fallback?: React.ReactNode;
  priority?: boolean;
  className?: string;
  alt?: string;
  objectFit?: 'contain' | 'cover' | 'fill' | 'none';
}

/**
 * Reusable AssetImage component with deterministic resolution:
 * Uses AI-generated asset (WebP/PNG) if placed in src/assets/,
 * otherwise seamlessly falls back to handcrafted SVG without broken icons or 404s.
 */
export const AssetImage: React.FC<AssetImageProps> = ({
  assetId,
  fallback,
  priority = false,
  className = '',
  alt,
  objectFit = 'contain',
  style,
  ...props
}) => {
  const [hasError, setHasError] = useState(false);
  const assetUrl = getAssetUrl(assetId);
  const meta = ASSET_CATALOG[assetId];
  const resolvedAlt = alt || meta?.name || assetId;

  // If no asset file is found or if image loading encountered an error, use handcrafted SVG fallback
  if (!assetUrl || hasError) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return null;
  }

  return (
    <img
      src={assetUrl}
      alt={resolvedAlt}
      loading={priority ? 'eager' : 'lazy'}
      decoding="async"
      onError={() => setHasError(true)}
      style={{
        objectFit,
        ...style,
      }}
      className={`select-none pointer-events-none ${className}`}
      {...props}
    />
  );
};
