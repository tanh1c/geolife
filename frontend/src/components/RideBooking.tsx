import React, { useState } from 'react';
import { BookingMap } from './booking/BookingMap';
import { BookingBottomSheet } from './booking/BookingBottomSheet';
import { VehicleId, VehicleOptionData } from './booking/VehicleOptionList';

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
    <div className="flex-1 bg-[#F5F8F9] flex flex-col h-full min-h-full relative overflow-hidden select-none">
      {/* 1. Upper Half: Interactive Map with Route & Floating Controls */}
      <div className="flex-1 min-h-[160px] relative overflow-hidden">
        <BookingMap
          onBack={onBack}
          destinationLabel={truncatedDestination}
          pickupLabel={truncatedPickup}
          onEditDestination={onEditDestination || onBack}
          onEditPickup={onEditPickup || onBack}
          onAddStop={onEditDestination || onBack}
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
    </div>
  );
};
