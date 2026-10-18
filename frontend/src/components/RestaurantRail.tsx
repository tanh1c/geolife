import React from 'react';
import { AssetImage } from './common/AssetImage';

export interface RestaurantItem {
  id: string;
  assetId: string;
  name: string;
  category: string;
  deliveryTime: string;
  distance: string;
  rating: number;
  highlight: string;
}

interface RestaurantRailProps {
  onSelectRestaurant?: (restaurant: RestaurantItem) => void;
}

export const RestaurantRail: React.FC<RestaurantRailProps> = ({ onSelectRestaurant }) => {
  const restaurants: RestaurantItem[] = [
    {
      id: 'banh-mi-ngon',
      assetId: 'menu-banhmi',
      name: 'Bánh Mì Thơm Ngon',
      category: 'Bánh mì thịt nướng & Pate',
      deliveryTime: '15-20 phút',
      distance: '1.2 km',
      rating: 4.9,
      highlight: 'Từ 20k',
    },
    {
      id: 'com-tam-sai-gon',
      assetId: 'menu-comtam',
      name: 'Cơm Tấm Sài Gòn',
      category: 'Sườn nướng, Bì chả & Trứng',
      deliveryTime: '20-25 phút',
      distance: '1.8 km',
      rating: 4.8,
      highlight: 'Từ 45k',
    },
    {
      id: 'pho-ngon-truyen-thong',
      assetId: 'menu-pho',
      name: 'Phở Ngon Truyền Thống',
      category: 'Bò tái, Phở gà & Bò viên',
      deliveryTime: '20-30 phút',
      distance: '2.4 km',
      rating: 4.9,
      highlight: 'Từ 40k',
    },
    {
      id: 'tra-sua-ngon',
      assetId: 'menu-trasua',
      name: 'Trà Sữa Ngon',
      category: 'Trà sữa, Khoai môn & Trà đào',
      deliveryTime: '15-20 phút',
      distance: '1.0 km',
      rating: 4.8,
      highlight: 'Từ 30k',
    },
  ];

  return (
    <div className="mt-5 select-none">
      {/* Section Header */}
      <div className="px-4 mb-3 flex items-center justify-between">
        <h2 className="text-[17px] font-semibold text-[#1E2528] tracking-tight">
          Gợi ý quán ngon
        </h2>
        <span className="text-[12.5px] font-medium text-[#737C7F]">Giao nhanh 15p</span>
      </div>

      {/* Horizontal Scroll Rail */}
      <div className="flex gap-3 overflow-x-auto px-4 pb-28 no-scrollbar scroll-smooth">
        {restaurants.map((rest) => (
          <div
            key={rest.id}
            onClick={() => onSelectRestaurant?.(rest)}
            className="w-[144px] h-[144px] shrink-0 rounded-[22px] bg-white border border-gray-200/70 relative overflow-hidden cursor-pointer active:scale-95 transition-all shadow-[0_4px_16px_rgba(15,23,42,0.08)] group hover:shadow-[0_8px_24px_rgba(15,23,42,0.14)]"
          >
            {/* Real Menu Poster Photo */}
            <AssetImage
              assetId={rest.assetId}
              alt={rest.name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />

            {/* Subtle bottom glass gradient overlay with restaurant title and rating */}
            <div className="absolute inset-x-0 bottom-0 pt-8 pb-2.5 px-2.5 bg-gradient-to-t from-black/85 via-black/45 to-transparent flex items-end justify-between text-white pointer-events-none">
              <div className="truncate pr-1">
                <span className="text-[12px] font-bold text-white leading-tight block truncate drop-shadow-sm">
                  {rest.name}
                </span>
                <span className="text-[10px] text-white/85 font-medium block truncate mt-0.5">
                  {rest.deliveryTime} • {rest.highlight}
                </span>
              </div>
              <span className="text-[10.5px] text-amber-300 font-bold shrink-0 bg-black/50 px-1.5 py-0.5 rounded-full backdrop-blur-xs">
                ★ {rest.rating}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
