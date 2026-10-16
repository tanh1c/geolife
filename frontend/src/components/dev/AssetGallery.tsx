import React, { useState } from 'react';
import { getAllRegisteredAssets, AssetMeta } from '../../assets/assetRegistry';
import { AssetImage } from '../common/AssetImage';
import {
  CarIllustration,
  FoodIllustration,
  ScooterIcon,
  AirportIcon,
  MembershipIcon,
  GiftCardIcon,
  VinBusIcon,
  DeliveryIcon,
  ScheduleIcon,
  IntercityIcon,
  BuyVinFastIcon,
  CarRentIcon,
} from '../ServiceIllustrations';
import {
  XanhCarIllustration,
  XanhPremiumIllustration,
  GreenMiniIllustration,
} from '../booking/VehicleOptionList';
import { ArrowLeft, RefreshCw, CheckCircle2, AlertCircle, Layers } from 'lucide-react';

interface AssetGalleryProps {
  onClose: () => void;
}

// Map each asset ID to its original handcrafted SVG fallback
function getSvgFallbackForAsset(id: string) {
  switch (id) {
    case 'car':
      return <CarIllustration className="w-full h-full" />;
    case 'food':
      return <FoodIllustration className="w-full h-full" />;
    case 'bike':
      return <ScooterIcon className="w-full h-full" />;
    case 'airport':
      return <AirportIcon className="w-full h-full" />;
    case 'subscription':
      return <MembershipIcon className="w-full h-full" />;
    case 'gift-card':
    case 'giftcard':
      return <GiftCardIcon className="w-full h-full" />;
    case 'vinbus':
      return <VinBusIcon className="w-full h-full" />;
    case 'express':
      return <DeliveryIcon className="w-full h-full" />;
    case 'schedule':
      return <ScheduleIcon className="w-full h-full" />;
    case 'intercity':
      return <IntercityIcon className="w-full h-full" />;
    case 'buyvinfast':
    case 'buy-vinfast':
      return <BuyVinFastIcon className="w-full h-full" />;
    case 'car-rent':
    case 'car-rental':
      return <CarRentIcon className="w-full h-full" />;
    case 'xanh-car':
      return <XanhCarIllustration className="w-full h-full" />;
    case 'xanh-premium':
      return <XanhPremiumIllustration className="w-full h-full" />;
    case 'green-mini':
      return <GreenMiniIllustration className="w-full h-full" />;
    default:
      return (
        <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded-lg text-[10px] text-gray-400 font-bold">
          SVG
        </div>
      );
  }
}

export const AssetGallery: React.FC<AssetGalleryProps> = ({ onClose }) => {
  const [size, setSize] = useState<48 | 64 | 96 | 128>(96);
  const [background, setBackground] = useState<'white' | 'gray' | 'cyan' | 'cream'>('white');
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'services' | 'booking' | 'banners' | 'restaurants'>('all');

  const assets = getAllRegisteredAssets();

  const filteredAssets = categoryFilter === 'all'
    ? assets
    : assets.filter((a) => a.category === categoryFilter);

  const bgClasses = {
    white: 'bg-white border-gray-200',
    gray: 'bg-[#F0F3F4] border-gray-300',
    cyan: 'bg-[#E8FAFB] border-[#55D8DC]/40',
    cream: 'bg-[#FFF3E0] border-[#FFE8CC]',
  };

  const availableCount = assets.filter((a) => a.isAvailable).length;

  return (
    <div className="fixed inset-0 z-50 bg-[#F5F8F9] overflow-y-auto font-sans flex flex-col text-[#202425]">
      {/* Top Header */}
      <div className="sticky top-0 z-20 bg-white/95 backdrop-blur-md border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-2xs">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            aria-label="Quay lại ứng dụng"
            className="w-10 h-10 rounded-xl bg-gray-100 hover:bg-gray-200 active:scale-95 transition flex items-center justify-center text-gray-700 cursor-pointer"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-[#1E2528]">Xanh SM 3D Asset Pipeline Gallery</h1>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-100 text-[#158E9A]">
                Local Dev Only
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Kiểm tra tỷ lệ, độ trong suốt, camera angle và tình trạng fallback SVG của toàn bộ asset
            </p>
          </div>
        </div>

        {/* Status Count */}
        <div className="flex items-center gap-4 text-xs font-semibold">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-50 text-green-700 border border-green-200">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            <span>{availableCount} AI Image file có sẵn</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span>{assets.length - availableCount} Dùng SVG Fallback</span>
          </div>
        </div>
      </div>

      {/* Control Bar: Sizes, Backgrounds, Categories */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        {/* Category Filter */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500 font-medium mr-1">Danh mục:</span>
          {(['all', 'services', 'booking', 'banners', 'restaurants'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer ${
                categoryFilter === cat
                  ? 'bg-[#2DCCD4] text-white shadow-xs'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {cat === 'all'
                ? 'Tất cả'
                : cat === 'services'
                ? 'Dịch vụ'
                : cat === 'booking'
                ? 'Xe đặt'
                : cat === 'banners'
                ? 'Banner'
                : 'Nhà hàng'}
            </button>
          ))}
        </div>

        {/* Preview Size Selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500 font-medium mr-1">Kích cỡ:</span>
          {([48, 64, 96, 128] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSize(s)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition cursor-pointer ${
                size === s
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s}px
            </button>
          ))}
        </div>

        {/* Background Contrast Selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500 font-medium mr-1">Nền thử nghiệm:</span>
          {[
            { id: 'white', label: 'Trắng', bg: 'bg-white border-gray-300' },
            { id: 'gray', label: 'Xám', bg: 'bg-[#F0F3F4] border-gray-300' },
            { id: 'cyan', label: 'Cyan Xanh', bg: 'bg-[#E8FAFB] border-[#55D8DC]' },
            { id: 'cream', label: 'Kem Món ăn', bg: 'bg-[#FFF3E0] border-[#FFE8CC]' },
          ].map((b) => (
            <button
              key={b.id}
              onClick={() => setBackground(b.id as any)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition cursor-pointer ${
                background === b.id ? 'ring-2 ring-[#2DCCD4]' : ''
              } ${b.bg}`}
            >
              <span>{b.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Asset Grid */}
      <div className="p-6 max-w-7xl mx-auto w-full flex-1">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredAssets.map((asset) => {
            const fallbackNode = getSvgFallbackForAsset(asset.id);

            return (
              <div
                key={asset.id}
                className="bg-white rounded-2xl border border-gray-200 p-4 flex flex-col justify-between shadow-2xs hover:shadow-md transition"
              >
                {/* Header info */}
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-mono font-bold text-gray-900 truncate">
                      {asset.id}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        asset.isAvailable
                          ? 'bg-green-100 text-green-700'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {asset.isAvailable ? 'AI Asset Ready' : 'SVG Fallback'}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-gray-800">{asset.name}</h3>
                  <p className="text-[11px] text-gray-500 line-clamp-2 mt-0.5">
                    {asset.description}
                  </p>
                </div>

                {/* Visual Canvas Test Bed */}
                <div className="my-3 flex items-center justify-center p-3 rounded-xl border border-dashed border-gray-200 bg-gray-50/50">
                  <div
                    style={{ width: `${size}px`, height: `${size}px` }}
                    className={`rounded-xl border flex items-center justify-center p-2 transition-all shadow-inner ${bgClasses[background]}`}
                  >
                    <AssetImage
                      assetId={asset.id}
                      fallback={fallbackNode}
                      className="w-full h-full object-contain"
                    />
                  </div>
                </div>

                {/* Specs Footer */}
                <div className="text-[11px] text-gray-400 border-t border-gray-100 pt-2 space-y-0.5">
                  <div className="flex justify-between">
                    <span>File đích:</span>
                    <span className="font-mono text-gray-600 font-semibold">{asset.recommendedFileName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Kích thước chuẩn:</span>
                    <span className="text-gray-600 font-medium">{asset.expectedDimensions}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Đường dẫn:</span>
                    <span className="font-mono text-gray-500 truncate max-w-[170px]">
                      src/assets/{asset.category}/
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
