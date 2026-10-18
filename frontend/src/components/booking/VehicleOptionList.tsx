import React from 'react';
import { Users, Clock, Info } from 'lucide-react';
import { AssetImage } from '../common/AssetImage';

export type VehicleId = 'xanh-car' | 'xanh-premium' | 'green-mini';

export interface VehicleOptionData {
  id: VehicleId;
  name: string;
  capacity: number;
  eta: string;
  fare: number;
  description: string;
}

interface VehicleOptionListProps {
  vehicles: VehicleOptionData[];
  selectedVehicleId: VehicleId;
  onSelectVehicle: (id: VehicleId) => void;
  formatVnd: (amount: number) => string;
}

// 1. High fidelity side-view illustration for Xanh Car (VinFast VF e34 / VF 5 Plus) matching image_4.png
export const XanhCarIllustration: React.FC<{ className?: string }> = ({ className = "w-14 h-9" }) => (
  <svg viewBox="0 0 90 50" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <ellipse cx="45" cy="44" rx="36" ry="3.5" fill="#0C2E33" fillOpacity="0.18" />
    {/* Aerodynamic Car body */}
    <path
      d="M 8 32 
         C 8 26 12 22 18 19 
         L 32 14 
         C 38 9 44 7 52 7 
         L 65 7 
         C 72 7 76 10 79 16 
         L 83 23 
         C 86 26 86 31 84 35 
         L 16 35 
         C 10 35 8 34 8 32 Z"
      fill="#2DCCD4"
    />
    {/* Cabin Roof highlight */}
    <path d="M 33 14 L 64 8 C 70 8 74 11 77 16 L 68 18 L 33 18 Z" fill="#6EE7EB" />
    {/* Tinted Windshield & windows */}
    <path d="M 20 20 L 33 15 L 47 15 L 43 25 L 22 25 Z" fill="#13363D" />
    <path d="M 49 15 L 63 15 L 62 25 L 45 25 Z" fill="#13363D" />
    <path d="M 65 15 L 75 16 C 78 18 79 21 80 25 L 64 25 Z" fill="#13363D" />
    {/* Character shoulder crease line */}
    <path d="M 10 27 Q 45 23 83 28" stroke="#87F7FA" strokeWidth="1.2" strokeLinecap="round" />
    {/* Alloy Wheels */}
    <g transform="translate(20, 27)">
      <circle cx="8" cy="8" r="7.5" fill="#1E293B" />
      <circle cx="8" cy="8" r="4.8" fill="#CBD5E1" />
      <circle cx="8" cy="8" r="2.2" fill="#2DCCD4" />
    </g>
    <g transform="translate(62, 27)">
      <circle cx="8" cy="8" r="7.5" fill="#1E293B" />
      <circle cx="8" cy="8" r="4.8" fill="#CBD5E1" />
      <circle cx="8" cy="8" r="2.2" fill="#2DCCD4" />
    </g>
  </svg>
);

// 2. High fidelity side-view illustration for Xanh Premium (VinFast VF 8 with golden sparkles)
export const XanhPremiumIllustration: React.FC<{ className?: string }> = ({ className = "w-14 h-9" }) => (
  <svg viewBox="0 0 90 50" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <ellipse cx="45" cy="44" rx="38" ry="3.5" fill="#0A2428" fillOpacity="0.2" />
    {/* Premium Body in dark teal */}
    <path
      d="M 6 33 
         C 6 27 10 23 17 20 
         L 30 14 
         C 36 9 44 6 54 6 
         L 68 6 
         C 75 6 80 9 82 16 
         L 86 24 
         C 88 28 88 32 85 36 
         L 14 36 
         C 8 36 6 35 6 33 Z"
      fill="#1A9EA7"
    />
    <path d="M 31 14 L 67 7 C 73 7 77 10 80 15 L 70 17 L 31 17 Z" fill="#45C1C9" />
    {/* Tinted Windows */}
    <path d="M 19 21 L 32 15 L 48 15 L 44 26 L 21 26 Z" fill="#0C2328" />
    <path d="M 50 15 L 66 15 L 65 26 L 46 26 Z" fill="#0C2328" />
    <path d="M 68 15 L 77 16 C 80 18 81 21 82 25 L 67 25 Z" fill="#0C2328" />
    <path d="M 8 28 Q 45 24 85 29" stroke="#E2E8F0" strokeWidth="1.2" strokeLinecap="round" />
    {/* Wheels */}
    <g transform="translate(19, 28)">
      <circle cx="8" cy="8" r="8" fill="#18181B" />
      <circle cx="8" cy="8" r="5" fill="#E2E8F0" />
      <circle cx="8" cy="8" r="2.2" fill="#0E7490" />
    </g>
    <g transform="translate(64, 28)">
      <circle cx="8" cy="8" r="8" fill="#18181B" />
      <circle cx="8" cy="8" r="5" fill="#E2E8F0" />
      <circle cx="8" cy="8" r="2.2" fill="#0E7490" />
    </g>
    {/* Premium golden sparkle stars ✨ */}
    <path d="M 14 8 Q 14 11 17 11 Q 14 11 14 14 Q 14 11 11 11 Q 14 11 14 8 Z" fill="#FACC15" />
    <path d="M 75 4 Q 75 6 77 6 Q 75 6 75 8 Q 75 6 73 6 Q 75 6 75 4 Z" fill="#FACC15" />
  </svg>
);

// 3. High fidelity side-view illustration for Green Mini (VinFast VF 3 compact electric SUV)
export const GreenMiniIllustration: React.FC<{ className?: string }> = ({ className = "w-14 h-9" }) => (
  <svg viewBox="0 0 90 50" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <ellipse cx="45" cy="44" rx="30" ry="3.5" fill="#0C2E33" fillOpacity="0.16" />
    {/* Boxy compact SUV body */}
    <path
      d="M 12 34 
         C 12 28 15 24 20 22 
         L 32 16 
         C 36 12 40 10 46 10 
         L 64 10 
         C 68 10 72 13 74 18 
         L 76 26 
         C 78 29 77 34 75 36 
         L 16 36 
         C 13 36 12 35 12 34 Z"
      fill="#28C7CF"
    />
    {/* White contrast roof */}
    <path d="M 31 16 L 46 10 L 64 10 C 68 10 71 12 73 17 L 70 18 L 31 18 Z" fill="#FFFFFF" />
    {/* Windows */}
    <path d="M 23 22 L 34 17 L 48 17 L 46 26 L 24 26 Z" fill="#13363D" />
    <path d="M 50 17 L 66 17 C 69 18 70 21 71 25 L 48 26 Z" fill="#13363D" />
    {/* Wheels */}
    <g transform="translate(19, 28)">
      <circle cx="8" cy="8" r="8" fill="#1E293B" />
      <circle cx="8" cy="8" r="4.5" fill="#94A3B8" />
      <circle cx="8" cy="8" r="2" fill="#28C7CF" />
    </g>
    <g transform="translate(56, 28)">
      <circle cx="8" cy="8" r="8" fill="#1E293B" />
      <circle cx="8" cy="8" r="4.5" fill="#94A3B8" />
      <circle cx="8" cy="8" r="2" fill="#28C7CF" />
    </g>
  </svg>
);

// Green small indicator tag next to price in Xanh Car (matching image_4.png)
const GreenPriceIndicator: React.FC = () => (
  <svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5 inline-block mr-1">
    <path d="M3 5L7 9L11 5" stroke="#16A34A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M3 8L7 12L11 8" stroke="#16A34A" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.6" />
  </svg>
);

export const VehicleOptionList: React.FC<VehicleOptionListProps> = ({
  vehicles,
  selectedVehicleId,
  onSelectVehicle,
  formatVnd,
}) => {
  return (
    <div className="space-y-1 select-none">
      {vehicles.map((vehicle) => {
        const isSelected = selectedVehicleId === vehicle.id;

        return (
          <div
            key={vehicle.id}
            onClick={() => onSelectVehicle(vehicle.id)}
            className={`w-full rounded-[16px] px-3.5 py-2.5 transition-all flex items-center justify-between cursor-pointer ${
              isSelected
                ? 'border border-[#2DCCD4] bg-gradient-to-r from-[#F4FCFD] via-white to-white shadow-2xs'
                : 'border border-transparent bg-white hover:bg-gray-50/80 active:bg-gray-100/60'
            }`}
          >
            {/* Left: Vehicle Image + Title + Specs */}
            <div className="flex items-center gap-3">
              {/* Vehicle Illustration (Real 3D models with transparent background) */}
              <div className="w-16 h-11 flex items-center justify-center shrink-0">
                {vehicle.id === 'xanh-car' ? (
                  <AssetImage
                    assetId="xanh-car"
                    fallback={<XanhCarIllustration className="w-14 h-9" />}
                    className="w-16 h-11 object-contain drop-shadow-xs"
                  />
                ) : vehicle.id === 'xanh-premium' ? (
                  <AssetImage
                    assetId="xanh-premium"
                    fallback={<XanhPremiumIllustration className="w-14 h-9" />}
                    className="w-16 h-11 object-contain drop-shadow-xs"
                  />
                ) : (
                  <AssetImage
                    assetId="green-mini"
                    fallback={<GreenMiniIllustration className="w-14 h-9" />}
                    className="w-16 h-11 object-contain drop-shadow-xs"
                  />
                )}
              </div>

              {/* Title & Specs */}
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[15px] font-semibold text-[#202425] leading-tight">
                    {vehicle.name}
                  </span>
                  {vehicle.id === 'xanh-car' && (
                    <Info className="w-3.5 h-3.5 text-[#8E989D]" />
                  )}
                </div>

                <div className="flex items-center gap-2 mt-0.5 text-[11.5px] text-[#8E989D] font-medium">
                  <div className="flex items-center gap-1">
                    <Users className="w-3 h-3 text-[#8E989D]" />
                    <span>{vehicle.capacity}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-[#8E989D]" />
                    <span>{vehicle.eta}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Fare with optional green indicator for Xanh Car */}
            <div className="text-right shrink-0 flex items-center">
              {vehicle.id === 'xanh-car' && isSelected && <GreenPriceIndicator />}
              <span className="text-[15px] font-semibold text-[#202425] tabular-nums leading-tight">
                {formatVnd(vehicle.fare)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
