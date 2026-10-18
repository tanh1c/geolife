import React from 'react';

/**
 * High-fidelity 3D-styled illustrations replicating the exact visuals from Xanh SM Home Screen
 */

export const CarIllustration: React.FC<{ className?: string }> = ({ className = "w-24 h-16" }) => (
  <svg viewBox="0 0 160 100" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="carBody" x1="20" y1="20" x2="140" y2="85" gradientUnits="userSpaceOnUse">
        <stop stopColor="#5BE1E7" />
        <stop offset="0.45" stopColor="#32CBD3" />
        <stop offset="1" stopColor="#1B9EA6" />
      </linearGradient>
      <linearGradient id="carRoof" x1="50" y1="10" x2="110" y2="50" gradientUnits="userSpaceOnUse">
        <stop stopColor="#7EF2F7" />
        <stop offset="1" stopColor="#38D0D8" />
      </linearGradient>
      <linearGradient id="carGlass" x1="45" y1="20" x2="105" y2="45" gradientUnits="userSpaceOnUse">
        <stop stopColor="#1E3A42" />
        <stop offset="0.7" stopColor="#2A4B54" />
        <stop offset="1" stopColor="#3E6A75" />
      </linearGradient>
      <linearGradient id="carGlow" x1="12" y1="58" x2="35" y2="68" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FFFFFF" />
        <stop offset="1" stopColor="#8DF6FA" />
      </linearGradient>
      <radialGradient id="wheelRim" cx="50%" cy="50%" r="50%">
        <stop stopColor="#F0F4F5" />
        <stop offset="0.6" stopColor="#A0AEB3" />
        <stop offset="1" stopColor="#4A5559" />
      </radialGradient>
      <filter id="carShadow" x="-10%" y="-10%" width="120%" height="130%" filterUnits="userSpaceOnUse">
        <feGaussianBlur stdDeviation="3.5" />
      </filter>
    </defs>

    {/* Soft drop shadow underneath */}
    <ellipse cx="80" cy="84" rx="64" ry="10" fill="#13474C" fillOpacity="0.22" filter="url(#carShadow)" />

    {/* Lower chassis / underbody */}
    <path d="M 22 72 Q 24 78 30 79 L 132 79 Q 142 78 144 71 L 140 65 L 25 65 Z" fill="#1C383D" />

    {/* Main aerodynamic car body */}
    <path
      d="M 18 64 
         C 16 57 20 52 28 48 
         L 52 38 
         C 58 25 68 18 84 17 
         L 112 17 
         C 126 17 136 24 140 37 
         L 144 46 
         C 147 52 146 62 143 68 
         C 140 73 133 75 125 75 
         L 32 75 
         C 23 75 19 70 18 64 Z"
      fill="url(#carBody)"
    />

    {/* Cabin & Roof highlight */}
    <path
      d="M 54 37 
         C 59 26 68 20 82 19 
         L 112 19 
         C 124 19 133 25 137 36 
         L 125 38 
         L 54 38 Z"
      fill="url(#carRoof)"
      opacity="0.9"
    />

    {/* Windshield and Side Windows (Glossy tinted) */}
    {/* Front windshield */}
    <path
      d="M 29 49 
         L 53 38 
         L 62 38 
         L 44 54 
         C 37 54 32 52 29 49 Z"
      fill="url(#carGlass)"
    />
    {/* Front side window */}
    <path
      d="M 58 37 
         L 85 37 
         L 84 53 
         L 49 54 
         Z"
      fill="url(#carGlass)"
    />
    {/* Rear side window */}
    <path
      d="M 89 37 
         L 116 37 
         C 124 37 130 42 133 49 
         L 132 53 
         L 88 53 
         Z"
      fill="url(#carGlass)"
    />

    {/* Glass reflections */}
    <path d="M 62 39 L 78 39 L 68 51 L 54 51 Z" fill="#FFFFFF" opacity="0.25" />
    <path d="M 94 39 L 108 39 L 102 51 L 90 51 Z" fill="#FFFFFF" opacity="0.2" />

    {/* Character shoulder crease line */}
    <path d="M 22 55 Q 80 50 143 56" stroke="#87F7FA" strokeWidth="1.8" strokeLinecap="round" opacity="0.75" />

    {/* Front LED Headlight */}
    <path
      d="M 18 56 C 18 53 23 51 28 52 L 27 58 C 22 59 18 58 18 56 Z"
      fill="url(#carGlow)"
    />
    <ellipse cx="22" cy="55" rx="3.5" ry="2" fill="#FFFFFF" />

    {/* Front Wheel */}
    <g transform="translate(36, 56)">
      <circle cx="15" cy="15" r="14" fill="#202628" />
      <circle cx="15" cy="15" r="9.5" fill="url(#wheelRim)" />
      <circle cx="15" cy="15" r="4.5" fill="#32CBD3" />
      <circle cx="15" cy="15" r="2" fill="#FFFFFF" />
      {/* 5-spoke rim design */}
      <line x1="15" y1="6" x2="15" y2="24" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.7" />
      <line x1="6" y1="12" x2="24" y2="18" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.7" />
      <line x1="8" y1="20" x2="22" y2="10" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.7" />
    </g>

    {/* Rear Wheel */}
    <g transform="translate(104, 56)">
      <circle cx="15" cy="15" r="14" fill="#202628" />
      <circle cx="15" cy="15" r="9.5" fill="url(#wheelRim)" />
      <circle cx="15" cy="15" r="4.5" fill="#32CBD3" />
      <circle cx="15" cy="15" r="2" fill="#FFFFFF" />
      <line x1="15" y1="6" x2="15" y2="24" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.7" />
      <line x1="6" y1="12" x2="24" y2="18" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.7" />
      <line x1="8" y1="20" x2="22" y2="10" stroke="#FFFFFF" strokeWidth="1.2" opacity="0.7" />
    </g>

    {/* Door seam and handle */}
    <path d="M 86 40 L 85 71" stroke="#1D8E95" strokeWidth="1.2" opacity="0.7" />
    <rect x="92" y="55" width="7" height="2.2" rx="1" fill="#1C7E85" />
    <rect x="58" y="55" width="7" height="2.2" rx="1" fill="#1C7E85" />
  </svg>
);

export const FoodIllustration: React.FC<{ className?: string }> = ({ className = "w-22 h-16" }) => (
  <svg viewBox="0 0 140 100" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="bagGrad" x1="20" y1="20" x2="75" y2="85" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FBBF24" />
        <stop offset="1" stopColor="#D97706" />
      </linearGradient>
      <linearGradient id="drinkGrad" x1="60" y1="35" x2="95" y2="85" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" />
        <stop offset="0.5" stopColor="#F472B6" />
        <stop offset="1" stopColor="#FB7185" />
      </linearGradient>
      <linearGradient id="breadGrad" x1="80" y1="30" x2="125" y2="70" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FDE68A" />
        <stop offset="0.4" stopColor="#F59E0B" />
        <stop offset="1" stopColor="#B45309" />
      </linearGradient>
      <filter id="foodShadow" x="-10%" y="-10%" width="120%" height="130%" filterUnits="userSpaceOnUse">
        <feGaussianBlur stdDeviation="3" />
      </filter>
    </defs>

    {/* Shadow */}
    <ellipse cx="70" cy="85" rx="52" ry="8" fill="#92400E" fillOpacity="0.2" filter="url(#foodShadow)" />

    {/* Grocery Bag */}
    <g transform="translate(10, 16)">
      {/* Bag Body */}
      <path
        d="M 12 18 L 48 15 L 56 68 L 14 70 Z"
        fill="url(#bagGrad)"
      />
      {/* Bag side fold */}
      <path
        d="M 12 18 L 14 70 L 6 64 L 5 21 Z"
        fill="#B45309"
      />
      {/* Bag top rolled fold */}
      <path
        d="M 10 17 Q 30 14 50 14 L 48 20 Q 28 20 10 23 Z"
        fill="#FDE68A"
      />
      {/* Bag handle cutout */}
      <rect x="24" y="27" width="16" height="5" rx="2.5" fill="#92400E" opacity="0.4" />
    </g>

    {/* Boba / Milk Tea Drink Cup */}
    <g transform="translate(48, 30)">
      {/* Cup */}
      <path
        d="M 10 16 L 36 16 L 32 54 C 31 57 27 59 23 59 C 19 59 15 57 14 54 Z"
        fill="url(#drinkGrad)"
      />
      {/* Domed lid */}
      <path
        d="M 8 16 C 8 8 38 8 38 16 Z"
        fill="#E0F2FE"
        opacity="0.85"
      />
      {/* Cyan Straw */}
      <path d="M 23 3 L 28 12 L 24 35" stroke="#06B6D4" strokeWidth="3.5" strokeLinecap="round" />
      {/* Boba pearls */}
      <circle cx="18" cy="48" r="2.5" fill="#7C2D12" />
      <circle cx="24" cy="51" r="2.5" fill="#7C2D12" />
      <circle cx="28" cy="47" r="2.2" fill="#7C2D12" />
      <circle cx="20" cy="42" r="2.2" fill="#7C2D12" />
    </g>

    {/* Golden Baguette / Croissant Bread */}
    <g transform="translate(76, 25) rotate(24)">
      <ellipse cx="28" cy="18" rx="26" ry="11" fill="url(#breadGrad)" />
      {/* Crust cuts */}
      <path d="M 14 14 Q 17 21 20 22" stroke="#FFFBEB" strokeWidth="2" strokeLinecap="round" />
      <path d="M 25 12 Q 28 20 31 22" stroke="#FFFBEB" strokeWidth="2" strokeLinecap="round" />
      <path d="M 36 11 Q 39 19 42 21" stroke="#FFFBEB" strokeWidth="2" strokeLinecap="round" />
    </g>
  </svg>
);

/* 1. Xe máy (Cyan/Teal Electric Scooter) */
export const ScooterIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="scooterBody" x1="10" y1="15" x2="55" y2="55" gradientUnits="userSpaceOnUse">
        <stop stopColor="#55D8DC" />
        <stop offset="1" stopColor="#1E9CA3" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="54" rx="24" ry="4" fill="#0E2F33" fillOpacity="0.15" />
    {/* Rear Wheel */}
    <circle cx="18" cy="46" r="9" fill="#263238" />
    <circle cx="18" cy="46" r="5" fill="#CFD8DC" />
    <circle cx="18" cy="46" r="2.5" fill="#37474F" />
    {/* Front Wheel */}
    <circle cx="47" cy="46" r="9" fill="#263238" />
    <circle cx="47" cy="46" r="5" fill="#CFD8DC" />
    <circle cx="47" cy="46" r="2.5" fill="#37474F" />
    {/* Body chassis & fairing */}
    <path
      d="M 18 42 
         C 16 32 24 28 32 28 
         L 37 38 
         L 44 38 
         L 47 22 
         L 42 20 
         L 43 17 
         L 49 19 
         C 51 24 49 32 46 42 
         Z"
      fill="url(#scooterBody)"
    />
    {/* Seat */}
    <path
      d="M 14 29 C 14 26 22 25 31 27 L 30 33 C 21 32 15 32 14 29 Z"
      fill="#263238"
    />
    {/* Footboard */}
    <rect x="27" y="41" width="14" height="4" rx="2" fill="#37474F" />
    {/* Headlight */}
    <circle cx="47" cy="20" r="3" fill="#FFF9C4" />
    <ellipse cx="48" cy="20" rx="1.5" ry="2" fill="#FFFFFF" />
  </svg>
);

/* 2. Đi sân bay (Commercial Airplane) */
export const AirportIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="planeGrad" x1="15" y1="15" x2="52" y2="52" gradientUnits="userSpaceOnUse">
        <stop stopColor="#67E8F9" />
        <stop offset="0.6" stopColor="#22D3EE" />
        <stop offset="1" stopColor="#0891B2" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="54" rx="20" ry="3.5" fill="#083344" fillOpacity="0.14" />
    {/* Airplane fuselage angled */}
    <g transform="translate(32, 30) rotate(-18) translate(-32, -30)">
      {/* Wings */}
      <path d="M 32 24 L 8 42 L 14 45 L 32 34 L 50 45 L 56 42 Z" fill="#06B6D4" />
      {/* Fuselage body */}
      <path
        d="M 32 10 
           C 35 10 37 16 37 25 
           L 36 48 
           L 44 54 
           L 41 56 
           L 32 52 
           L 23 56 
           L 20 54 
           L 28 48 
           L 27 25 
           C 27 16 29 10 32 10 Z"
        fill="url(#planeGrad)"
      />
      {/* Cockpit windshield */}
      <path d="M 29 17 C 29 15 35 15 35 17 L 34 20 L 30 20 Z" fill="#082F49" />
      {/* Cabin windows */}
      <circle cx="32" cy="25" r="1.2" fill="#E0F2FE" />
      <circle cx="32" cy="29" r="1.2" fill="#E0F2FE" />
      <circle cx="32" cy="33" r="1.2" fill="#E0F2FE" />
      <circle cx="32" cy="37" r="1.2" fill="#E0F2FE" />
      {/* Jet Engines */}
      <rect x="20" y="36" width="4" height="7" rx="2" fill="#155E75" />
      <rect x="40" y="36" width="4" height="7" rx="2" fill="#155E75" />
    </g>
  </svg>
);

/* 3. Gói hội viên (Sparkling Diamond Gem) */
export const MembershipIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="gemTop" x1="16" y1="20" x2="48" y2="28" gradientUnits="userSpaceOnUse">
        <stop stopColor="#A5F3FC" />
        <stop offset="1" stopColor="#38BDF8" />
      </linearGradient>
      <linearGradient id="gemBody" x1="14" y1="26" x2="48" y2="48" gradientUnits="userSpaceOnUse">
        <stop stopColor="#22D3EE" />
        <stop offset="1" stopColor="#0284C7" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="53" rx="18" ry="3.5" fill="#0369A1" fillOpacity="0.15" />
    {/* Gem facets */}
    {/* Top crown */}
    <path d="M 22 19 L 42 19 L 51 28 L 13 28 Z" fill="url(#gemTop)" />
    <path d="M 22 19 L 32 28 L 42 19 Z" fill="#CFFAFE" />
    <path d="M 13 28 L 22 19 L 26 28 Z" fill="#67E8F9" />
    <path d="M 51 28 L 42 19 L 38 28 Z" fill="#38BDF8" />

    {/* Bottom Pavilion */}
    <path d="M 13 28 L 32 50 L 51 28 Z" fill="url(#gemBody)" />
    <path d="M 24 28 L 32 50 L 40 28 Z" fill="#38BDF8" />
    <path d="M 24 28 L 32 50 L 13 28 Z" fill="#0284C7" />
    <path d="M 40 28 L 32 50 L 51 28 Z" fill="#0369A1" />

    {/* Golden sparkle stars */}
    <g transform="translate(45, 13)">
      <path d="M 4 0 Q 4 4 8 4 Q 4 4 4 8 Q 4 4 0 4 Q 4 4 4 0 Z" fill="#FBBF24" />
    </g>
    <g transform="translate(10, 36) scale(0.8)">
      <path d="M 4 0 Q 4 4 8 4 Q 4 4 4 8 Q 4 4 0 4 Q 4 4 4 0 Z" fill="#FDE047" />
    </g>
  </svg>
);

/* 4. Thẻ quà tặng (Gift Box with % Discount Voucher) */
export const GiftCardIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="giftBox" x1="16" y1="28" x2="48" y2="52" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" />
        <stop offset="1" stopColor="#0284C7" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="53" rx="18" ry="3.5" fill="#075985" fillOpacity="0.16" />
    {/* Gift Box Base */}
    <rect x="18" y="32" width="28" height="19" rx="3" fill="url(#giftBox)" />
    {/* Ribbon Vertical */}
    <rect x="29" y="32" width="6" height="19" fill="#FDE047" />
    {/* Box Lid */}
    <rect x="15" y="27" width="34" height="7" rx="2" fill="#0EA5E9" />
    <rect x="29" y="27" width="6" height="7" fill="#FDE047" />

    {/* Yellow Discount Tag Badge emerging from box */}
    <g transform="translate(30, 10) rotate(-12)">
      <path d="M 4 3 L 18 3 L 22 10 L 18 17 L 4 17 L 0 10 Z" fill="#F59E0B" />
      <path d="M 3 4 L 17 4 L 20 10 L 17 16 L 3 16 L 1 10 Z" fill="#FBBF24" />
      <circle cx="5" cy="10" r="1.5" fill="#78350F" />
      <text x="8" y="13" fill="#78350F" fontSize="8" fontWeight="800" fontFamily="inherit">%</text>
    </g>
  </svg>
);

/* 5. VinBus (Green & Yellow Electric Bus) */
export const VinBusIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="busGreen" x1="12" y1="20" x2="52" y2="48" gradientUnits="userSpaceOnUse">
        <stop stopColor="#84CC16" />
        <stop offset="0.6" stopColor="#22C55E" />
        <stop offset="1" stopColor="#15803D" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="53" rx="22" ry="4" fill="#14532D" fillOpacity="0.18" />

    {/* Bus body */}
    <path
      d="M 14 45 
         L 14 26 
         C 14 21 19 19 25 19 
         L 48 19 
         C 52 19 54 22 54 26 
         L 54 45 
         C 54 47 52 48 50 48 
         L 18 48 
         C 15 48 14 47 14 45 Z"
      fill="url(#busGreen)"
    />

    {/* Bright Yellow Energy Stripe (VinBus style) */}
    <path d="M 14 38 L 54 38 L 54 42 L 14 42 Z" fill="#FACC15" />

    {/* Panoramic Windows Band */}
    <rect x="16" y="23" width="36" height="12" rx="2" fill="#0F172A" />
    {/* Window divider struts */}
    <rect x="23" y="23" width="1.5" height="12" fill="#22C55E" />
    <rect x="31" y="23" width="1.5" height="12" fill="#22C55E" />
    <rect x="39" y="23" width="1.5" height="12" fill="#22C55E" />
    <rect x="47" y="23" width="1.5" height="12" fill="#22C55E" />

    {/* Front Headlights */}
    <circle cx="50" cy="44" r="2" fill="#FEF08A" />
    <circle cx="18" cy="44" r="1.5" fill="#EF4444" />

    {/* Wheels */}
    <g transform="translate(20, 43)">
      <circle cx="4" cy="4" r="5" fill="#1E293B" />
      <circle cx="4" cy="4" r="2.5" fill="#94A3B8" />
    </g>
    <g transform="translate(42, 43)">
      <circle cx="4" cy="4" r="5" fill="#1E293B" />
      <circle cx="4" cy="4" r="2.5" fill="#94A3B8" />
    </g>
  </svg>
);

/* 6. Giao hàng (Hands Delivering Gift Box) */
export const DeliveryIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="boxGrad" x1="20" y1="18" x2="44" y2="38" gradientUnits="userSpaceOnUse">
        <stop stopColor="#67E8F9" />
        <stop offset="1" stopColor="#0891B2" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="53" rx="18" ry="3.5" fill="#083344" fillOpacity="0.14" />

    {/* Cyan Package Box */}
    <g transform="translate(20, 16)">
      <rect x="0" y="6" width="24" height="18" rx="2" fill="url(#boxGrad)" />
      {/* Yellow Ribbon */}
      <rect x="10" y="6" width="4" height="18" fill="#FDE047" />
      <rect x="0" y="13" width="24" height="4" fill="#FDE047" />
      {/* Bow on top */}
      <ellipse cx="9" cy="5" rx="3.5" ry="2" fill="#FBBF24" />
      <ellipse cx="15" cy="5" rx="3.5" ry="2" fill="#FBBF24" />
    </g>

    {/* Supporting Hands underneath */}
    {/* Left hand */}
    <path
      d="M 12 45 
         C 15 42 20 40 26 40 
         L 28 44 
         C 22 44 18 46 14 49 Z"
      fill="#FDBA74"
    />
    {/* Right hand */}
    <path
      d="M 52 45 
         C 49 42 44 40 38 40 
         L 36 44 
         C 42 44 46 46 50 49 Z"
      fill="#FDBA74"
    />
  </svg>
);

/* 7. Hẹn giờ (Desk Calendar with Clock) */
export const ScheduleIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="calGrad" x1="16" y1="16" x2="48" y2="48" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" />
        <stop offset="1" stopColor="#0284C7" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="53" rx="18" ry="3.5" fill="#075985" fillOpacity="0.15" />

    {/* Calendar Page */}
    <rect x="16" y="20" width="32" height="28" rx="4" fill="#FFFFFF" stroke="#BAE6FD" strokeWidth="1.5" />
    {/* Top Header bar */}
    <path d="M 16 24 C 16 21.8 17.8 20 20 20 L 44 20 C 46.2 20 48 21.8 48 24 L 48 28 L 16 28 Z" fill="url(#calGrad)" />

    {/* Spiral Rings */}
    <rect x="22" y="16" width="3" height="7" rx="1.5" fill="#0369A1" />
    <rect x="30" y="16" width="3" height="7" rx="1.5" fill="#0369A1" />
    <rect x="38" y="16" width="3" height="7" rx="1.5" fill="#0369A1" />

    {/* Grid date dots */}
    <circle cx="23" cy="34" r="1.5" fill="#94A3B8" />
    <circle cx="29" cy="34" r="1.5" fill="#94A3B8" />
    <circle cx="35" cy="34" r="1.5" fill="#94A3B8" />
    <circle cx="41" cy="34" r="1.5" fill="#94A3B8" />

    <circle cx="23" cy="40" r="1.5" fill="#94A3B8" />
    <circle cx="29" cy="40" r="1.5" fill="#94A3B8" />
    <circle cx="35" cy="40" r="1.5" fill="#0284C7" />

    {/* Small Clock overlay badge on bottom right */}
    <g transform="translate(35, 33)">
      <circle cx="9" cy="9" r="8" fill="#F8FAFC" stroke="#0284C7" strokeWidth="2" />
      <path d="M 9 5 L 9 9 L 12 11" stroke="#0284C7" strokeWidth="1.8" strokeLinecap="round" />
    </g>
  </svg>
);

/* 8. Đi Liên tỉnh (Intercity Signpost) */
export const IntercityIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="signCyan" x1="16" y1="20" x2="48" y2="28" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" />
        <stop offset="1" stopColor="#0284C7" />
      </linearGradient>
      <linearGradient id="signGreen" x1="16" y1="28" x2="48" y2="36" gradientUnits="userSpaceOnUse">
        <stop stopColor="#4ADE80" />
        <stop offset="1" stopColor="#16A34A" />
      </linearGradient>
    </defs>
    {/* Shadow */}
    <ellipse cx="32" cy="54" rx="16" ry="3.5" fill="#1E293B" fillOpacity="0.18" />

    {/* Center Post Pole */}
    <rect x="30" y="14" width="4" height="40" rx="1" fill="#64748B" />

    {/* Top Sign (Pointing Right) */}
    <path
      d="M 18 20 
         L 42 20 
         L 48 24.5 
         L 42 29 
         L 18 29 
         Z"
      fill="url(#signCyan)"
    />
    <rect x="22" y="23" width="14" height="2.5" rx="1" fill="#FFFFFF" opacity="0.9" />

    {/* Bottom Sign (Pointing Left) */}
    <path
      d="M 44 31 
         L 20 31 
         L 14 35.5 
         L 20 40 
         L 44 40 
         Z"
      fill="url(#signGreen)"
    />
    <rect x="24" y="34" width="14" height="2.5" rx="1" fill="#FFFFFF" opacity="0.9" />

    {/* Base mound */}
    <ellipse cx="32" cy="52" rx="7" ry="2.5" fill="#94A3B8" />
  </svg>
);

/* 9. Mua xe VinFast (VinFast Showroom) */
export const BuyVinFastIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="vfShowroom" x1="10" y1="18" x2="54" y2="48" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" />
        <stop offset="1" stopColor="#0284C7" />
      </linearGradient>
    </defs>
    <ellipse cx="32" cy="54" rx="20" ry="4" fill="#1E293B" fillOpacity="0.16" />
    {/* Base slab */}
    <rect x="8" y="46" width="48" height="6" rx="2" fill="#E2E8F0" />
    {/* Glass showroom walls */}
    <rect x="12" y="24" width="40" height="23" rx="2" fill="#F0F9FF" stroke="#BAE6FD" strokeWidth="1.5" />
    {/* Roof fascia */}
    <rect x="10" y="16" width="44" height="10" rx="3" fill="url(#vfShowroom)" />
    {/* VinFast V logo on fascia */}
    <path d="M 28 20 L 32 25 L 36 20" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    {/* Miniature car silhouette inside */}
    <path d="M 22 41 C 24 37 32 37 34 38 L 40 38 C 42 40 43 42 42 44 L 20 44 Z" fill="#0284C7" />
    <circle cx="25" cy="44" r="2.5" fill="#1E293B" />
    <circle cx="37" cy="44" r="2.5" fill="#1E293B" />
  </svg>
);

/* 10. Thuê xe tự lái (VinFast Smart Car Key) */
export const CarRentIcon: React.FC<{ className?: string }> = ({ className = "w-11 h-11" }) => (
  <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="keyBody" x1="24" y1="20" x2="44" y2="52" gradientUnits="userSpaceOnUse">
        <stop stopColor="#334155" />
        <stop offset="1" stopColor="#0F172A" />
      </linearGradient>
    </defs>
    <ellipse cx="32" cy="55" rx="14" ry="3.5" fill="#1E293B" fillOpacity="0.16" />
    {/* Key ring */}
    <circle cx="32" cy="16" r="8" stroke="#94A3B8" strokeWidth="3" />
    {/* Key fob */}
    <rect x="23" y="22" width="18" height="30" rx="7" fill="url(#keyBody)" stroke="#475569" strokeWidth="1.5" />
    {/* VinFast V on key */}
    <path d="M 28 32 L 32 37 L 36 32" stroke="#38BDF8" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    {/* Lock / Unlock buttons */}
    <rect x="29" y="41" width="6" height="2" rx="1" fill="#64748B" />
    <rect x="29" y="45" width="6" height="2" rx="1" fill="#64748B" />
  </svg>
);

