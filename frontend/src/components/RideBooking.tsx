import React, { useState } from 'react';
import { BookingMap } from './booking/BookingMap';
import { BookingBottomSheet } from './booking/BookingBottomSheet';
import { VehicleId, VehicleOptionData } from './booking/VehicleOptionList';
import { X, Users, Check } from 'lucide-react';

interface RideBookingProps {
  onBack: () => void;
  destinationName?: string;
  onEditDestination?: () => void;
  onEditPickup?: () => void;
}

export const RideBooking: React.FC<RideBookingProps> = ({
  onBack,
  destinationName = 'Vincom Center Bà Triệu',
  onEditDestination,
  onEditPickup,
}) => {
  const [selectedVehicleId, setSelectedVehicleId] = useState<VehicleId>('xanh-car');
  const [isBookOtherModalOpen, setIsBookOtherModalOpen] = useState(false);
  const [otherPassenger, setOtherPassenger] = useState('Người thân / Bạn bè');

  // Exact 3 vehicles from image_3.png and design.md
  const vehicles: VehicleOptionData[] = [
    {
      id: 'xanh-car',
      name: 'Xanh Car',
      capacity: 4,
      eta: 'Đón trong 2 phút',
      fare: 101000,
      description: 'VF e34 / VF 5 Plus tiện nghi, êm ái',
    },
    {
      id: 'xanh-premium',
      name: 'Xanh Premium',
      capacity: 4,
      eta: 'Đón trong 2 phút',
      fare: 129000,
      description: 'VF 8 đẳng cấp thương gia',
    },
    {
      id: 'green-mini',
      name: 'Green Mini',
      capacity: 3,
      eta: 'Đón trong 2 phút',
      fare: 105000,
      description: 'VF 3 nhỏ gọn, linh hoạt trong phố',
    },
  ];

  const formatVnd = (amount: number) => {
    return new Intl.NumberFormat('vi-VN').format(amount) + 'đ';
  };

  // Truncate destination for floating map chip (e.g., "Vincom Center Bà Tr...")
  const truncatedDestination =
    destinationName.length > 20
      ? destinationName.slice(0, 20) + '...'
      : destinationName;

  const pickupLocation = 'Điểm Đón Xanh Taxi - Tòa Nhà Văn Phòng';
  const truncatedPickup = 'Điểm Đón Xanh Taxi - ...';

  return (
    <div className="flex-1 bg-[#F5F8F9] flex flex-col h-full min-h-full relative overflow-y-auto no-scrollbar select-none">
      
      {/* 1. Upper Half: Interactive Map with Route & Floating Controls */}
      <div className="flex-1 min-h-[220px] relative overflow-hidden shrink-0">
        <BookingMap
          onBack={onBack}
          destinationLabel={truncatedDestination}
          pickupLabel={truncatedPickup}
          onEditDestination={onEditDestination || onBack}
          onEditPickup={onEditPickup || onBack}
          onAddStop={onEditDestination || onBack}
          onBookForOther={() => setIsBookOtherModalOpen(true)}
        />
      </div>

      {/* 2. Lower Half: White Bottom Booking Sheet */}
      <div className="shrink-0 relative z-30">
        <BookingBottomSheet
          vehicles={vehicles}
          selectedVehicleId={selectedVehicleId}
          onSelectVehicle={setSelectedVehicleId}
          destinationName={destinationName}
          pickupName={pickupLocation}
          formatVnd={formatVnd}
        />
      </div>

      {/* "Đặt hộ" Passenger Sheet */}
      {isBookOtherModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs z-50 flex items-end justify-center">
          <div className="w-full max-w-[412px] bg-white rounded-t-[26px] p-5 shadow-2xl animate-in slide-in-from-bottom">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-[#2DCCD4]" />
                <h3 className="text-[16px] font-bold text-gray-900">Đặt xe hộ người khác</h3>
              </div>
              <button
                onClick={() => setIsBookOtherModalOpen(false)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-3">
              <p className="text-[13px] text-gray-600 leading-normal">
                Tài xế sẽ nhận được thông tin liên hệ và đón đúng hành khách bạn chỉ định.
              </p>
              <div className="space-y-2">
                {['Bản thân tôi', 'Người thân / Bạn bè', 'Khách hàng / Đối tác'].map((p) => (
                  <div
                    key={p}
                    onClick={() => {
                      setOtherPassenger(p);
                      setIsBookOtherModalOpen(false);
                    }}
                    className={`p-3 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                      otherPassenger === p ? 'border-[#2DCCD4] bg-[#F2FCFD]' : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <span className="text-[13.5px] font-semibold text-gray-800">{p}</span>
                    {otherPassenger === p && <Check className="w-4 h-4 text-[#2DCCD4]" />}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
