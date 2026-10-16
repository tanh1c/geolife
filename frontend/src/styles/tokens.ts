/**
 * Xanh SM Design System V3: Liquid Glass & Visual Materials Token Architecture
 * Runtime source of truth synced with CSS custom properties in src/index.css
 */

export const TOKENS = {
  colors: {
    // Brand Turquoise Identity
    primary: '#2DCCD4',
    primaryHover: '#20BDC8',
    primarySoft: '#E8FAFB',
    primaryStroke: '#55D8DC',
    primaryText: '#158E9A',

    // Text & Content Hierarchy
    textPrimary: '#202425',
    textSecondary: '#737C7F',
    textMuted: '#8E989D',
    textLight: '#A9B0B2',

    // Structural Canvas & Surfaces
    bgApp: '#F0F3F4',
    surfaceWhite: '#FFFFFF',
    surfaceMuted: '#F8FAFB',
    borderSubtle: '#EDF0F2',
    borderHairline: 'rgba(0, 0, 0, 0.04)',

    // Semantic Accents
    yellowPin: '#F6C600',
    successGreen: '#16A34A',
    purpleCash: '#7C3AED',
  },

  typography: {
    fontFamily: "'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    weights: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    sizes: {
      headingSection: '17px',
      titlePrimary: '15.5px',
      titleSecondary: '14px',
      body: '13px',
      caption: '11.5px',
      tiny: '10.5px',
      price: '15px',
      cta: '15.5px',
    },
  },

  radii: {
    xs: '6px',
    sm: '10px',
    md: '14px',
    card: '18px',
    cardLg: '20px',
    sheetTop: '28px',
    pill: '9999px',
  },

  // Liquid Glass V3 Material System Class Mappings
  materials: {
    dock: 'glass-dock',
    dockActive: 'glass-dock-active',
    button: 'glass-button',
    card: 'glass-card',
    cardCar: 'glass-card-car',
    cardFood: 'glass-card-food',
    cardService: 'glass-card-service',
    pill: 'glass-pill',
    input: 'glass-input',
    routeBadge: 'glass-route-badge',
    solidPrimary: 'solid-primary',
  },
} as const;

export type MaterialVariant = keyof typeof TOKENS.materials;
