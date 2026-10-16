import React, { useState, useRef } from 'react';
import {
  ArrowLeft,
  ChevronRight,
  Plus,
  Repeat,
} from 'lucide-react';

interface BookingMapProps {
  onBack: () => void;
  destinationLabel?: string;
  pickupLabel?: string;
  onEditDestination?: () => void;
  onEditPickup?: () => void;
  onAddStop?: () => void;
  onBookForOther?: () => void;
}

export const BookingMap: React.FC<BookingMapProps> = ({
  onBack,
  destinationLabel = 'Vincom Center Bà Tr...',
  pickupLabel = 'Điểm Đón Xanh Taxi - ...',
  onEditDestination,
  onEditPickup,
  onAddStop,
}) => {
  // Support pan / drag interaction on the map
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  const handlePointerDown = (e: React.PointerEvent) => {
    setIsDragging(true);
    dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    const newX = Math.max(-120, Math.min(120, e.clientX - dragStart.current.x));
    const newY = Math.max(-80, Math.min(80, e.clientY - dragStart.current.y));
    setPan({ x: newX, y: newY });
  };

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  return (
    <div
      className="relative w-full h-full min-h-[220px] overflow-hidden select-none bg-[#F5F8F9] cursor-grab active:cursor-grabbing touch-none"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {/* 1. Interactive Pastel Map Canvas */}
      <div
        className="absolute inset-0 w-full h-full transform transition-transform duration-75 ease-out"
        style={{
          transform: `translate3d(${pan.x}px, ${pan.y}px, 0px) scale(1.05)`,
        }}
      >
        <svg
          viewBox="0 0 460 480"
          className="w-full h-full object-cover"
          preserveAspectRatio="xMidYMid slice"
        >
          <defs>
            {/* Water gradient */}
            <linearGradient id="riverHanoi" x1="0" y1="0" x2="460" y2="480" gradientUnits="userSpaceOnUse">
              <stop stopColor="#D5ECF8" />
              <stop offset="0.5" stopColor="#C9E5F5" />
              <stop offset="1" stopColor="#BFE0F4" />
            </linearGradient>

            {/* Cyan route line shadow */}
            <filter id="routeShadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="2" stdDeviation="2.5" floodColor="#0F474C" floodOpacity="0.22" />
            </filter>

            {/* Pin drop shadows */}
            <filter id="pinElevation" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#0F2428" floodOpacity="0.28" />
            </filter>
          </defs>

          {/* Pale Background Ground */}
          <rect width="460" height="480" fill="#F8FAFA" />

          {/* Pale Green Parks and Open Spaces */}
          <path d="M 0 30 Q 70 10 110 50 Q 140 100 80 130 Q 20 120 0 70 Z" fill="#E4F4E7" />
          <path d="M 190 20 Q 250 15 280 55 Q 260 110 210 115 Q 160 100 190 20 Z" fill="#E4F4E7" />
          <path d="M 330 40 Q 420 30 460 90 L 460 0 L 320 0 Z" fill="#E4F4E7" />
          <path d="M 360 210 Q 440 230 460 310 Q 410 360 340 330 Q 320 260 360 210 Z" fill="#E4F4E7" />
          <path d="M 60 280 Q 140 260 160 340 Q 110 400 40 380 Q 20 320 60 280 Z" fill="#E4F4E7" />

          {/* Sông Hồng (Red River) flowing smoothly across the city */}
          <path
            d="M 60 -20 
               C 80 80 50 150 120 230 
               C 170 290 190 350 150 430 
               C 130 470 110 500 90 520 
               L 0 520 L 0 -20 Z"
            fill="url(#riverHanoi)"
            opacity="0.85"
          />

          {/* Secondary Lake / River Arm */}
          <path
            d="M 240 -20 
               C 280 40 340 60 360 100 
               C 380 150 350 190 330 220 
               L 310 210 
               C 330 170 350 130 330 90 
               C 310 60 260 30 220 -20 Z"
            fill="url(#riverHanoi)"
            opacity="0.6"
          />

          {/* Primary City Road Grid */}
          <path d="M -20 80 L 480 80" stroke="#FFFFFF" strokeWidth="8" />
          <path d="M -20 80 L 480 80" stroke="#EDF0F2" strokeWidth="6" />

          <path d="M -20 190 L 480 180" stroke="#FFFFFF" strokeWidth="8" />
          <path d="M -20 190 L 480 180" stroke="#EDF0F2" strokeWidth="6" />

          <path d="M -20 320 L 480 320" stroke="#FFFFFF" strokeWidth="8" />
          <path d="M -20 320 L 480 320" stroke="#EDF0F2" strokeWidth="6" />

          <path d="M 120 -20 L 120 500" stroke="#FFFFFF" strokeWidth="7" />
          <path d="M 120 -20 L 120 500" stroke="#EDF0F2" strokeWidth="5" />

          <path d="M 280 -20 L 280 500" stroke="#FFFFFF" strokeWidth="8" />
          <path d="M 280 -20 L 280 500" stroke="#EDF0F2" strokeWidth="6" />

          <path d="M 390 -20 L 390 500" stroke="#FFFFFF" strokeWidth="7" />
          <path d="M 390 -20 L 390 500" stroke="#EDF0F2" strokeWidth="5" />

          {/* Cầu Vĩnh Tuy Bridge structure crossing Sông Hồng */}
          <g>
            <path d="M 160 280 L 210 240" stroke="#FFFFFF" strokeWidth="10" strokeLinecap="round" />
            <path d="M 160 280 L 210 240" stroke="#CBD5E1" strokeWidth="7" strokeLinecap="round" />
            {/* Bridge Text Label: Cầu Vĩnh Tuy */}
            <text
              x="200"
              y="255"
              fill="#0EA5E9"
              fontSize="8"
              fontWeight="700"
              fontFamily="sans-serif"
              transform="rotate(-38 200 255)"
              opacity="0.8"
            >
              Cầu Vĩnh Tuy
            </text>
          </g>

          {/* QL5 Highway Shield Marker */}
          <g transform="translate(245, 120)">
            <rect x="0" y="0" width="28" height="13" rx="2.5" fill="#FFFFFF" stroke="#94A3B8" strokeWidth="1" />
            <text x="14" y="9.5" fill="#475569" fontSize="7" fontWeight="800" fontFamily="sans-serif" textAnchor="middle">
              QL5
            </text>
          </g>

          {/* Turquoise Route Polyline matching image_3.png */}
          {/* Connecting destination (lower-left: ~75, 260) to pickup (upper-right: ~365, 125) */}
          <path
            d="M 75 255 
               L 95 255 
               L 95 240 
               L 155 240 
               L 175 255 
               L 205 235 
               L 255 185 
               L 300 135 
               L 330 130 
               L 365 125"
            stroke="#2DCCD4"
            strokeWidth="5.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#routeShadow)"
          />

          {/* Inner highlight line */}
          <path
            d="M 75 255 
               L 95 255 
               L 95 240 
               L 155 240 
               L 175 255 
               L 205 235 
               L 255 185 
               L 300 135 
               L 330 130 
               L 365 125"
            stroke="#95F6F9"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Traffic condition spots along route (orange / red minor delays matching map style) */}
          <circle cx="105" cy="240" r="3.2" fill="#F97316" />
          <circle cx="310" cy="138" r="3.2" fill="#EF4444" />

          {/* Destination Marker at lower-left (Yellow square pin) */}
          <g transform="translate(63, 243)" filter="url(#pinElevation)">
            <rect x="0" y="0" width="22" height="22" rx="5" fill="#F5C02F" />
            <rect x="6.5" y="6.5" width="9" height="9" rx="2" fill="#FFFFFF" />
          </g>

          {/* Pickup Marker at upper-right */}
          {/* Black location pin */}
          <g transform="translate(360, 110)" filter="url(#pinElevation)">
            <path
              d="M 10 0 
                 C 4.5 0 0 4.5 0 10 
                 C 0 16 10 24 10 24 
                 C 10 24 20 16 20 10 
                 C 20 4.5 15.5 0 10 0 Z"
              fill="#18181B"
            />
            <circle cx="10" cy="9.5" r="4" fill="#FFFFFF" />
          </g>

          {/* Fan cluster of 3 cyan electric cars around pickup (Signature Xanh SM map animation) */}
          <g transform="translate(355, 120)">
            {/* Car 1 (angled left) */}
            <g transform="translate(0, 0) rotate(-25)">
              <rect x="0" y="0" width="20" height="10" rx="3" fill="#2DCCD4" stroke="#FFFFFF" strokeWidth="1.2" />
              <rect x="4" y="2" width="7" height="6" rx="1.5" fill="#0C2F34" />
            </g>
            {/* Car 2 (center) */}
            <g transform="translate(6, 4) rotate(10)">
              <rect x="0" y="0" width="20" height="10" rx="3" fill="#20BDC8" stroke="#FFFFFF" strokeWidth="1.2" />
              <rect x="4" y="2" width="7" height="6" rx="1.5" fill="#0C2F34" />
            </g>
            {/* Car 3 (angled right) */}
            <g transform="translate(12, 8) rotate(35)">
              <rect x="0" y="0" width="20" height="10" rx="3" fill="#3AE3EB" stroke="#FFFFFF" strokeWidth="1.2" />
              <rect x="4" y="2" width="7" height="6" rx="1.5" fill="#0C2F34" />
            </g>
          </g>
        </svg>
      </div>

      {/* 2. FLOATING OVERLAYS (Liquid Glass V3 materials, independent of map pan/drag) */}

      {/* Top Floating Controls: Back arrow */}
      <div className="absolute top-10 left-4 z-20 pointer-events-auto">
        {/* Back Button (Liquid Glass Button) */}
        <button
          onClick={onBack}
          aria-label="Quay lại"
          className="w-10 h-10 rounded-full glass-button flex items-center justify-center text-[#202425] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
        >
          <ArrowLeft className="w-5 h-5" strokeWidth={2.2} />
        </button>
      </div>

      {/* Upper-Right: Pickup Chip + Direction Swap Button */}
      <div className="absolute top-10 right-4 flex items-center gap-1.5 z-20 pointer-events-auto max-w-[280px]">
        {/* Pickup Chip (Liquid Glass Pill) */}
        <div
          onClick={onEditPickup}
          className="h-10 px-3 glass-pill rounded-xl flex items-center gap-1.5 cursor-pointer active:scale-95 transition max-w-[210px]"
        >
          <span className="text-[13px] font-semibold text-[#202425] truncate">
            {pickupLabel}
          </span>
          <ChevronRight className="w-4 h-4 text-[#8E989D] shrink-0" />
        </div>

        {/* Direction Swap Button (Liquid Glass Button) */}
        <button
          onClick={() => {}}
          aria-label="Đổi chiều di chuyển"
          className="w-10 h-10 rounded-xl glass-button flex items-center justify-center text-[#2DCCD4] shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
        >
          <Repeat className="w-4 h-4 text-[#2DCCD4] rotate-90" strokeWidth={2.4} />
        </button>
      </div>

      {/* Lower-Left: Route summary & Destination Selector */}
      <div className="absolute bottom-5 left-4 z-20 flex flex-col items-start gap-1 pointer-events-auto max-w-[280px]">
        {/* Route Info Badge (Liquid Glass route badge) */}
        <div className="glass-route-badge text-[#158E9A] px-2.5 py-1 rounded-lg text-[12px] font-semibold shadow-2xs">
          21 phút · 10.8 km
        </div>

        {/* Destination Chip + Add Stop Button */}
        <div className="flex items-center gap-1.5">
          {/* Destination Chip (Liquid Glass Pill) */}
          <div
            onClick={onEditDestination}
            className="h-10 px-3 glass-pill rounded-xl flex items-center gap-1.5 cursor-pointer active:scale-95 transition max-w-[210px]"
          >
            <span className="text-[13px] font-semibold text-[#202425] truncate">
              {destinationLabel}
            </span>
            <ChevronRight className="w-4 h-4 text-[#8E989D] shrink-0" />
          </div>

          {/* Plus Button (Liquid Glass Button) */}
          <button
            onClick={onAddStop}
            aria-label="Thêm điểm dừng"
            className="w-10 h-10 rounded-xl glass-button flex items-center justify-center text-[#2DCCD4] shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
          >
            <Plus className="w-5 h-5 text-[#2DCCD4]" strokeWidth={2.6} />
          </button>
        </div>
      </div>

    </div>
  );
};
