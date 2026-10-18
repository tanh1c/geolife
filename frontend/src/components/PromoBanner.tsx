import React, { useState, useEffect } from 'react';
import { AssetImage } from './common/AssetImage';

interface PromoBannerProps {
  onBannerClick?: () => void;
}

export const PromoBanner: React.FC<PromoBannerProps> = ({ onBannerClick }) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const slides = [
    {
      id: 'banner-xanhsm-6trieu',
      title: 'Mừng khách hàng thứ 6 triệu Xanh SM',
      badge: 'XANH SM',
      sub: 'Tri ân khách hàng - Vô vàn ưu đãi thuần điện',
    },
    {
      id: 'banner-phuclong',
      title: 'Phúc Long Giảm 30%',
      badge: 'GIẢM 30%',
      sub: 'Tươi mát • Thơm ngon • Tự nhiên',
    },
    {
      id: 'banner-highlands',
      title: 'Highlands Coffee Mua 1 Tặng 1',
      badge: 'MUA 1 TẶNG 1',
      sub: 'Thưởng thức cà phê đậm đà mỗi ngày',
    },
    {
      id: 'banner-kfc',
      title: 'KFC Combo 99K',
      badge: 'COMBO 99K',
      sub: 'Gà rán giòn cay nóng hổi giao tận nơi',
    },
    {
      id: 'banner-lotteria',
      title: 'Lotteria Giảm 50%',
      badge: 'GIẢM 50%',
      sub: 'Burger thơm ngon, trọn vị giòn rụm',
    },
  ];

  // Auto advance banner every 4.5 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length);
    }, 4500);
    return () => clearInterval(timer);
  }, [slides.length]);

  const activeSlide = slides[currentSlide];

  return (
    <div className="px-4 mt-5">
      {/* Banner Container - Exact 16:9 aspect ratio matching 1920x1080 banners */}
      <div
        onClick={onBannerClick}
        className="w-full relative rounded-[20px] overflow-hidden aspect-[16/9] shadow-[0_6px_20px_rgba(45,204,212,0.12)] border border-[#E0F7FA]/70 cursor-pointer active:scale-[0.99] transition-transform select-none bg-gray-100"
      >
        <AssetImage
          assetId={activeSlide.id}
          alt={activeSlide.title}
          className="w-full h-full object-cover transition-all duration-500"
          fallback={
        /* Banner Scene Illustration Fallback */
        <svg
          viewBox="0 0 520 220"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full object-cover"
          preserveAspectRatio="xMidYMid slice"
        >
          <defs>
            <linearGradient id="skyGrad" x1="0" y1="0" x2="520" y2="220" gradientUnits="userSpaceOnUse">
              <stop stopColor="#D9F9FA" />
              <stop offset="0.6" stopColor="#A8F2F6" />
              <stop offset="1" stopColor="#D2F6F8" />
            </linearGradient>
            <linearGradient id="streetGrad" x1="0" y1="160" x2="0" y2="220" gradientUnits="userSpaceOnUse">
              <stop stopColor="#E2A62C" />
              <stop offset="0.3" stopColor="#D99B26" />
              <stop offset="1" stopColor="#BF841A" />
            </linearGradient>
            <linearGradient id="vanTeal" x1="160" y1="120" x2="340" y2="180" gradientUnits="userSpaceOnUse">
              <stop stopColor="#5AE5EB" />
              <stop offset="0.5" stopColor="#25CCD5" />
              <stop offset="1" stopColor="#1599A2" />
            </linearGradient>
            <linearGradient id="vanRoof" x1="200" y1="110" x2="320" y2="150" gradientUnits="userSpaceOnUse">
              <stop stopColor="#E8FAFB" />
              <stop offset="1" stopColor="#8DF6FA" />
            </linearGradient>
            <linearGradient id="goldText" x1="0" y1="0" x2="0" y2="24" gradientUnits="userSpaceOnUse">
              <stop stopColor="#FEF08A" />
              <stop offset="0.45" stopColor="#FACC15" />
              <stop offset="1" stopColor="#EAB308" />
            </linearGradient>
            <linearGradient id="cyanText" x1="0" y1="0" x2="0" y2="28" gradientUnits="userSpaceOnUse">
              <stop stopColor="#A5F3FC" />
              <stop offset="0.4" stopColor="#22D3EE" />
              <stop offset="1" stopColor="#0891B2" />
            </linearGradient>
            <filter id="boxDrop" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="2" dy="4" stdDeviation="3" floodColor="#0D3B40" floodOpacity="0.25" />
            </filter>
          </defs>

          {/* Sky / Ambient background */}
          <rect width="520" height="220" fill="url(#skyGrad)" />

          {/* Background Shophouse Buildings */}
          {/* Shop 1: Trà Sữa (Left) */}
          <g transform="translate(10, 85)">
            <rect x="0" y="20" width="105" height="60" fill="#EADBC8" />
            <polygon points="-5,20 110,20 100,5 5,5" fill="#78350F" />
            {/* Awning stripes */}
            <path d="M 0 20 L 5 5 L 18 5 L 14 20 Z" fill="#D97706" />
            <path d="M 28 20 L 32 5 L 45 5 L 42 20 Z" fill="#D97706" />
            <path d="M 56 20 L 60 5 L 73 5 L 70 20 Z" fill="#D97706" />
            <path d="M 84 20 L 88 5 L 101 5 L 98 20 Z" fill="#D97706" />
            {/* Storefront Signboard */}
            <rect x="12" y="26" width="80" height="18" rx="3" fill="#14532D" />
            <text x="52" y="39" fill="#FEF08A" fontSize="10" fontWeight="800" fontFamily="sans-serif" textAnchor="middle">
              TRÀ SỮA
            </text>
            {/* Glass window */}
            <rect x="15" y="48" width="75" height="30" fill="#BAE6FD" opacity="0.6" stroke="#92400E" strokeWidth="1.5" />
          </g>

          {/* Shop 2: Siêu Thị (Center-Left) */}
          <g transform="translate(120, 80)">
            <rect x="0" y="25" width="130" height="60" fill="#F1F5F9" />
            <polygon points="-5,25 135,25 125,8 5,8" fill="#991B1B" />
            {/* Storefront Signboard */}
            <rect x="15" y="32" width="100" height="20" rx="3" fill="#DC2626" />
            <text x="65" y="46" fill="#FFFFFF" fontSize="11" fontWeight="800" fontFamily="sans-serif" textAnchor="middle">
              SIÊU THỊ
            </text>
            <rect x="20" y="55" width="90" height="28" fill="#FDE047" opacity="0.5" stroke="#991B1B" strokeWidth="1.5" />
          </g>

          {/* Shop 3: Cafe (Right) */}
          <g transform="translate(410, 85)">
            <rect x="0" y="20" width="105" height="60" fill="#E2E8F0" />
            <polygon points="-5,20 110,20 100,5 5,5" fill="#1E3A8A" />
            <rect x="12" y="26" width="80" height="18" rx="3" fill="#1E40AF" />
            <text x="52" y="39" fill="#FFFFFF" fontSize="10" fontWeight="800" fontFamily="sans-serif" textAnchor="middle">
              CAFE
            </text>
            <rect x="15" y="48" width="75" height="30" fill="#CBD5E1" opacity="0.6" stroke="#1E3A8A" strokeWidth="1.5" />
          </g>

          {/* Yellow Sidewalk / Road Ground */}
          <rect y="155" width="520" height="65" fill="url(#streetGrad)" />
          <line x1="0" y1="156" x2="520" y2="156" stroke="#FFFFFF" strokeWidth="2" strokeDasharray="16 8" opacity="0.4" />

          {/* Electric Delivery Van (Turquoise Xanh SM Van) */}
          <g transform="translate(170, 92)" filter="url(#boxDrop)">
            {/* Van Body */}
            <path
              d="M 12 70 
                 L 12 24 
                 C 12 18 16 15 22 15 
                 L 115 15 
                 C 122 15 128 19 133 26 
                 L 142 42 
                 L 155 46 
                 C 160 48 162 53 162 58 
                 L 162 70 
                 Z"
              fill="url(#vanTeal)"
            />

            {/* Van Roof Curve */}
            <path d="M 22 15 L 115 15 C 122 15 128 19 133 26 L 115 26 L 22 26 Z" fill="url(#vanRoof)" opacity="0.6" />

            {/* Windshield & Driver Window */}
            <path d="M 115 22 L 132 24 L 140 42 L 115 42 Z" fill="#0F2B30" />
            <path d="M 92 24 L 111 24 L 111 42 L 92 42 Z" fill="#0F2B30" />

            {/* Bright Yellow Wave Graphic across the van */}
            <path
              d="M 50 68 
                 L 75 22 
                 L 90 22 
                 L 65 68 Z"
              fill="#FACC15"
            />

            {/* "NHANH & CHUẨN" Slogan on Van Body */}
            <rect x="70" y="30" width="54" height="14" rx="2" fill="#0E4B52" opacity="0.4" />
            <text x="97" y="40" fill="#FEF08A" fontSize="7.5" fontWeight="900" fontStyle="italic" fontFamily="sans-serif" textAnchor="middle">
              NHANH & CHUẨN
            </text>

            {/* Xanh SM Logo Mark on Front Door */}
            <g transform="translate(32, 38)">
              <rect x="0" y="0" width="18" height="12" rx="2" fill="#FFFFFF" opacity="0.9" />
              <path d="M 4 8 L 8 4 L 14 10" stroke="#0891B2" strokeWidth="2" strokeLinecap="round" />
            </g>

            {/* Van Wheels */}
            <g transform="translate(38, 64)">
              <circle cx="8" cy="8" r="10" fill="#18181B" />
              <circle cx="8" cy="8" r="6" fill="#71717A" />
              <circle cx="8" cy="8" r="3" fill="#25CCD5" />
            </g>
            <g transform="translate(125, 64)">
              <circle cx="8" cy="8" r="10" fill="#18181B" />
              <circle cx="8" cy="8" r="6" fill="#71717A" />
              <circle cx="8" cy="8" r="3" fill="#25CCD5" />
            </g>

            {/* Headlights */}
            <ellipse cx="160" cy="54" rx="3" ry="5" fill="#FEF08A" />
          </g>

          {/* Delivery Driver Figure standing on the right */}
          <g transform="translate(345, 96)" filter="url(#boxDrop)">
            {/* Head and smiling face */}
            <circle cx="36" cy="18" r="12" fill="#FDBA74" />
            {/* Dark Hair / Cap */}
            <path d="M 24 16 C 24 8 48 8 48 16 L 50 18 L 22 18 Z" fill="#0F172A" />
            <circle cx="33" cy="17" r="1.5" fill="#1E293B" />
            <circle cx="41" cy="17" r="1.5" fill="#1E293B" />
            <path d="M 33 22 Q 37 26 41 22" stroke="#B45309" strokeWidth="1.5" strokeLinecap="round" />

            {/* Navy Uniform Polo Shirt with Yellow Collar */}
            <path d="M 20 30 L 52 30 L 55 78 L 17 78 Z" fill="#0F2B35" />
            {/* Yellow collar trim */}
            <path d="M 28 30 L 36 38 L 44 30" stroke="#FACC15" strokeWidth="2.5" strokeLinecap="round" />
            {/* Xanh SM emblem on chest */}
            <rect x="38" y="36" width="10" height="5" rx="1" fill="#22D3EE" />

            {/* Dark Trousers */}
            <rect x="22" y="78" width="13" height="40" fill="#020617" />
            <rect x="37" y="78" width="13" height="40" fill="#020617" />

            {/* Holding Green Delivery Box in front */}
            <g transform="translate(10, 48)">
              <rect x="0" y="0" width="34" height="24" rx="3" fill="#15803D" stroke="#166534" strokeWidth="1" />
              <rect x="13" y="0" width="8" height="24" fill="#FACC15" />
              {/* Xanh SM logo on box */}
              <text x="17" y="15" fill="#FFFFFF" fontSize="6.5" fontWeight="900" fontFamily="sans-serif" textAnchor="middle">
                XANHSM
              </text>
            </g>
          </g>

          {/* Floating Cardboard Delivery Parcels in the air */}
          <g transform="translate(415, 65) rotate(15)" filter="url(#boxDrop)">
            <rect x="0" y="0" width="22" height="18" rx="2" fill="#D97706" />
            <rect x="8" y="0" width="5" height="18" fill="#FDE68A" />
            <rect x="0" y="7" width="22" height="4" fill="#FDE68A" />
          </g>
          <g transform="translate(460, 40) rotate(-18)" filter="url(#boxDrop)">
            <rect x="0" y="0" width="18" height="15" rx="2" fill="#B45309" />
            <rect x="6" y="0" width="4" height="15" fill="#FDE68A" />
          </g>

          {/* Primary Slogan Text on Left */}
          {/* Top Line: "BẠN TRAO HÀNG HÓA" */}
          <g transform="translate(22, 44)">
            <text
              x="0"
              y="0"
              fill="#0F383D"
              fontSize="20"
              fontWeight="900"
              fontFamily="sans-serif"
              letterSpacing="0.5"
              stroke="#082F49"
              strokeWidth="4"
              strokeLinejoin="round"
            >
              BẠN TRAO HÀNG HÓA
            </text>
            <text
              x="0"
              y="0"
              fill="url(#goldText)"
              fontSize="20"
              fontWeight="900"
              fontFamily="sans-serif"
              letterSpacing="0.5"
            >
              BẠN TRAO HÀNG HÓA
            </text>
          </g>

          {/* Bottom Line: "XANH GỬI NIỀM TIN" */}
          <g transform="translate(22, 72)">
            <text
              x="0"
              y="0"
              fill="#062E34"
              fontSize="23"
              fontWeight="900"
              fontFamily="sans-serif"
              letterSpacing="0.5"
              stroke="#062E34"
              strokeWidth="4.5"
              strokeLinejoin="round"
            >
              XANH GỬI NIỀM TIN
            </text>
            <text
              x="0"
              y="0"
              fill="url(#cyanText)"
              fontSize="23"
              fontWeight="900"
              fontFamily="sans-serif"
              letterSpacing="0.5"
            >
              XANH GỬI NIỀM TIN
            </text>
          </g>

          {/* "GIẢM NGAY 40K" Badge in top center-right */}
          <g transform="translate(270, 24)" filter="url(#boxDrop)">
            {/* Badge container with green border */}
            <rect x="0" y="0" width="102" height="42" rx="6" fill="#044738" stroke="#10B981" strokeWidth="2" />
            {/* Left yellow part: GIẢM NGAY */}
            <rect x="3" y="3" width="42" height="36" rx="4" fill="#FACC15" />
            <text x="24" y="18" fill="#064E3B" fontSize="8" fontWeight="900" fontFamily="sans-serif" textAnchor="middle">
              GIẢM
            </text>
            <text x="24" y="30" fill="#064E3B" fontSize="8" fontWeight="900" fontFamily="sans-serif" textAnchor="middle">
              NGAY
            </text>
            {/* Right dark part: 40K */}
            <text x="74" y="28" fill="#FACC15" fontSize="21" fontWeight="900" fontFamily="sans-serif" textAnchor="middle">
              40K
            </text>
          </g>

          {/* Legal fine print on bottom-left */}
          <text x="22" y="206" fill="#FFFFFF" fontSize="8" fontWeight="500" opacity="0.9" fontFamily="sans-serif">
            (*) Chương trình có điều kiện & điều khoản đi kèm.
          </text>
        </svg>
        }
        />
      </div>

      {/* Pagination Dots (Dynamic matching slides length with active indicator) */}
      <div className="flex items-center justify-center gap-1.5 mt-2.5">
        {slides.map((_, idx) => {
          const isActive = idx === currentSlide;
          return (
            <button
              key={idx}
              onClick={(e) => {
                e.stopPropagation();
                setCurrentSlide(idx);
              }}
              aria-label={`Chuyển đến banner ${idx + 1}`}
              className={`transition-all duration-300 rounded-full cursor-pointer ${
                isActive
                  ? "w-5 h-1.5 bg-[#2DCCD4]"
                  : "w-1.5 h-1.5 bg-[#D1D5DB] hover:bg-[#9CA3AF]"
              }`}
            />
          );
        })}
      </div>
    </div>
  );
};
