import React, { useState } from 'react';
import {
  Clock,
  Zap,
  Check,
  X,
  CheckCircle2,
} from 'lucide-react';
import {
  VehicleOptionList,
  VehicleId,
  VehicleOptionData,
} from './VehicleOptionList';
import { LiquidGlassButton } from '../common/LiquidGlassButton';

interface BookingBottomSheetProps {
  vehicles: VehicleOptionData[];
  selectedVehicleId: VehicleId;
  onSelectVehicle: (id: VehicleId) => void;
  destinationName: string;
  pickupName: string;
  formatVnd: (amount: number) => string;
}

// 4-Dots / Tiles Grid Icon with plus for Invoice (matching image_4.png)
const InvoiceGridIcon: React.FC<{ className?: string }> = ({ className = "w-4 h-4" }) => (
  <svg viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="2" y="2" width="5" height="5" rx="1.2" fill="#8E989D" />
    <rect x="9.5" y="2" width="5" height="5" rx="1.2" fill="#8E989D" />
    <rect x="2" y="9.5" width="5" height="5" rx="1.2" fill="#8E989D" />
    <rect x="9.5" y="9.5" width="5" height="5" rx="1.2" fill="#8E989D" />
    {/* Tiny plus mark accent */}
    <path d="M 2.5 1.5 L 4.5 1.5 M 3.5 0.5 L 3.5 2.5" stroke="#8E989D" strokeWidth="0.8" strokeLinecap="round" />
  </svg>
);

// Purple Cash / Payment Note Icon matching image_4.png
const CashMoneyIcon: React.FC<{ className?: string }> = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="2" y="5" width="20" height="14" rx="3.5" fill="#7C3AED" />
    {/* Inner white note design */}
    <circle cx="12" cy="12" r="3.2" fill="#FFFFFF" />
    <circle cx="5.5" cy="12" r="1.2" fill="#DDD6FE" />
    <circle cx="18.5" cy="12" r="1.2" fill="#DDD6FE" />
  </svg>
);

// Ticket / Voucher Outline Icon matching image_4.png
const VoucherOutlineIcon: React.FC<{ className?: string }> = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path
      d="M 3 8 
         C 4.65 8 6 6.65 6 5 
         L 18 5 
         C 18 6.65 19.35 8 21 8 
         L 21 16 
         C 19.35 16 18 17.35 18 19 
         L 6 19 
         C 6 17.35 4.65 16 3 16 
         Z"
      stroke="#202425"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path d="M 10 7 L 10 17" stroke="#202425" strokeWidth="1.8" strokeDasharray="2.5 2" strokeLinecap="round" />
  </svg>
);

export const BookingBottomSheet: React.FC<BookingBottomSheetProps> = ({
  vehicles,
  selectedVehicleId,
  onSelectVehicle,
  destinationName,
  pickupName,
  formatVnd,
}) => {
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'card' | 'wallet'>('cash');
  const [appliedPromo, setAppliedPromo] = useState<string | null>(null);
  const [xanhNow, setXanhNow] = useState(true);
  const [scheduledTime, setScheduledTime] = useState<string | null>(null);
  const [activeModal, setActiveModal] = useState<null | 'payment' | 'promo' | 'schedule' | 'invoice' | 'confirmed'>(null);

  const currentVehicle = vehicles.find((v) => v.id === selectedVehicleId) || vehicles[0];
  const finalFare = appliedPromo ? Math.max(currentVehicle.fare - 40000, 20000) : currentVehicle.fare;

  return (
    <div className="w-full bg-white rounded-t-[28px] shadow-[0_-8px_30px_rgba(15,45,50,0.08)] z-30 flex flex-col justify-between px-4 pt-2 pb-4 sm:pb-5 select-none relative">
      
      {/* 1. Grab Handle Bar (Soft pill affordance) */}
      <div className="w-10 h-1 rounded-full bg-[#E2E8F0] mx-auto mt-0.5 mb-2.5" />

      {/* 2. Vehicle Options List (3 rows matching image_4.png) */}
      <VehicleOptionList
        vehicles={vehicles}
        selectedVehicleId={selectedVehicleId}
        onSelectVehicle={onSelectVehicle}
        formatVnd={formatVnd}
      />

      {/* 3. Payment & Promotion Row */}
      <div className="flex items-center justify-between py-2.5 px-2 mt-1 border-t border-b border-gray-100/90">
        {/* Left: Payment Method */}
        <button
          onClick={() => setActiveModal('payment')}
          className="flex items-center gap-2 hover:opacity-80 active:scale-95 transition cursor-pointer select-none"
        >
          <CashMoneyIcon className="w-5 h-5 shrink-0" />
          <span className="text-[13.5px] font-semibold text-[#202425]">
            {paymentMethod === 'cash'
              ? 'Tiền mặt'
              : paymentMethod === 'card'
              ? 'Thẻ'
              : 'Ví điện tử'}
          </span>
        </button>

        {/* Right: Promotion */}
        <button
          onClick={() => setActiveModal('promo')}
          className="flex items-center gap-2 hover:opacity-80 active:scale-95 transition cursor-pointer select-none"
        >
          <VoucherOutlineIcon className="w-5 h-5 shrink-0" />
          <span className="text-[13.5px] font-semibold text-[#202425]">
            {appliedPromo ? `Mã: ${appliedPromo}` : 'Ưu đãi'}
          </span>
        </button>
      </div>

      {/* 4. Invoice & Additional Services Row */}
      <button
        onClick={() => setActiveModal('invoice')}
        className="w-full py-2.5 px-3.5 rounded-[12px] bg-[#F8FAFB] hover:bg-gray-100/90 border border-gray-100 flex items-center gap-2.5 my-1.5 transition active:scale-[0.99]"
      >
        <InvoiceGridIcon className="w-4 h-4 text-[#8E989D] shrink-0" />
        <span className="text-[12px] text-[#737C7F] font-medium truncate">
          Xuất hóa đơn & dịch vụ bổ sung tại đây.
        </span>
      </button>

      {/* 5. Persistent Bottom Booking Action Bar (HIGHEST PRIORITY - Hẹn giờ, XanhNow, Đặt xe CTA) */}
      <div className="flex items-center gap-2.5 pt-2.5">
        {/* Action 1: Hẹn giờ (Cyan clock icon above label) */}
        <button
          onClick={() => setActiveModal('schedule')}
          className="w-14 h-12 flex flex-col items-center justify-center gap-0.5 active:scale-95 transition hover:opacity-85"
        >
          <Clock className="w-5 h-5 text-[#2DCCD4]" strokeWidth={2.2} />
          <span className="text-[11px] font-semibold text-[#202425] leading-tight">
            {scheduledTime ? 'Đã hẹn' : 'Hẹn giờ'}
          </span>
        </button>

        {/* Action 2: XanhNow (Turquoise lightning bolt icon above label) */}
        <button
          onClick={() => setXanhNow(!xanhNow)}
          className="w-16 h-12 flex flex-col items-center justify-center gap-0.5 active:scale-95 transition hover:opacity-85"
        >
          <Zap className="w-5 h-5 text-[#2DCCD4] fill-[#2DCCD4]" strokeWidth={1.8} />
          <span className="text-[11px] font-semibold text-[#202425] leading-tight">
            XanhNow
          </span>
        </button>

        {/* Primary CTA: Caustic Liquid Glass Button */}
        <div className="flex-1">
          <LiquidGlassButton
            size="full"
            variant="turquoise"
            onClick={() => setActiveModal('confirmed')}
            label={`Đặt xe ${appliedPromo ? `• ${formatVnd(finalFare)}` : ''}`}
          />
        </div>
      </div>

      {/* ================= MODALS & SHEETS ================= */}

      {/* 1. Payment Method Modal */}
      {activeModal === 'payment' && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs z-50 flex items-end justify-center">
          <div className="w-full max-w-[412px] bg-white rounded-t-[26px] p-5 shadow-2xl animate-in slide-in-from-bottom">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <h3 className="text-[16px] font-bold text-[#202425]">Phương thức thanh toán</h3>
              <button
                onClick={() => setActiveModal(null)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2.5 py-4">
              {[
                { id: 'cash' as const, name: 'Tiền mặt', desc: 'Thanh toán trực tiếp cho tài xế khi đến nơi' },
                { id: 'card' as const, name: 'Thẻ quốc tế (Visa / Master)', desc: '•••• 8892' },
                { id: 'wallet' as const, name: 'Ví điện tử MoMo / ZaloPay', desc: 'Thanh toán không dùng tiền mặt' },
              ].map((m) => (
                <div
                  key={m.id}
                  onClick={() => {
                    setPaymentMethod(m.id);
                    setActiveModal(null);
                  }}
                  className={`p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                    paymentMethod === m.id ? 'border-[#2DCCD4] bg-[#F2FCFD]' : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div>
                    <div className="text-[14px] font-bold text-[#202425]">{m.name}</div>
                    <div className="text-[12px] text-gray-500">{m.desc}</div>
                  </div>
                  {paymentMethod === m.id && <Check className="w-5 h-5 text-[#2DCCD4]" />}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 2. Promotions / Voucher Sheet */}
      {activeModal === 'promo' && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs z-50 flex items-end justify-center">
          <div className="w-full max-w-[412px] bg-white rounded-t-[26px] p-5 shadow-2xl animate-in slide-in-from-bottom">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <h3 className="text-[16px] font-bold text-[#202425]">Mã ưu đãi chuyến đi</h3>
              <button
                onClick={() => setActiveModal(null)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 py-4">
              {[
                { code: 'XANH40K', title: 'Giảm ngay 40.000đ mọi chuyến Xanh Car', expire: 'HSD: 31/12/2026' },
                { code: 'XANHNOW', title: 'Ưu tiên đón nhanh trong giờ cao điểm', expire: 'HSD: 30/11/2026' },
              ].map((voucher) => (
                <div key={voucher.code} className="p-3.5 rounded-xl border border-gray-200 flex items-center justify-between">
                  <div>
                    <span className="inline-block px-2 py-0.5 rounded bg-[#FEF3C7] text-[#B45309] font-bold text-[11px] mb-1">
                      {voucher.code}
                    </span>
                    <div className="text-[13px] font-bold text-[#202425]">{voucher.title}</div>
                    <div className="text-[11px] text-gray-400 mt-0.5">{voucher.expire}</div>
                  </div>
                  <button
                    onClick={() => {
                      setAppliedPromo(appliedPromo === voucher.code ? null : voucher.code);
                      setActiveModal(null);
                    }}
                    className={`px-3.5 py-1.5 rounded-lg text-[12px] font-bold transition ${
                      appliedPromo === voucher.code
                        ? 'bg-gray-100 text-gray-600'
                        : 'bg-[#2DCCD4] text-white hover:bg-[#20BDC8]'
                    }`}
                  >
                    {appliedPromo === voucher.code ? 'Bỏ chọn' : 'Áp dụng'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 3. Schedule / Hẹn giờ Sheet */}
      {activeModal === 'schedule' && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs z-50 flex items-end justify-center">
          <div className="w-full max-w-[412px] bg-white rounded-t-[26px] p-5 shadow-2xl animate-in slide-in-from-bottom">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <h3 className="text-[16px] font-bold text-[#202425]">Đặt lịch hẹn trước</h3>
              <button
                onClick={() => setActiveModal(null)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-3">
              <p className="text-[13px] text-gray-600">
                Tài xế thuần điện Xanh SM sẽ có mặt đúng giờ theo lịch hẹn của bạn.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {['Hôm nay, 14:30', 'Hôm nay, 17:00', 'Ngày mai, 07:30', 'Ngày mai, 08:30'].map((time) => (
                  <button
                    key={time}
                    onClick={() => {
                      setScheduledTime(time);
                      setActiveModal(null);
                    }}
                    className="p-3 rounded-xl border border-gray-200 text-left hover:border-[#2DCCD4] text-[13px] font-medium"
                  >
                    {time}
                  </button>
                ))}
              </div>
            </div>

            {scheduledTime && (
              <button
                onClick={() => {
                  setScheduledTime(null);
                  setActiveModal(null);
                }}
                className="w-full py-2.5 rounded-xl bg-gray-100 text-gray-600 font-semibold text-[13px]"
              >
                Hủy lịch hẹn
              </button>
            )}
          </div>
        </div>
      )}

      {/* 4. Invoice & Extras Sheet */}
      {activeModal === 'invoice' && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs z-50 flex items-end justify-center">
          <div className="w-full max-w-[412px] bg-white rounded-t-[26px] p-5 shadow-2xl animate-in slide-in-from-bottom">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <h3 className="text-[16px] font-bold text-[#202425]">Xuất hóa đơn điện tử VAT</h3>
              <button
                onClick={() => setActiveModal(null)}
                className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-3">
              <div className="flex items-center justify-between p-3 rounded-xl bg-gray-50">
                <span className="text-[13.5px] font-semibold text-gray-800">Yêu cầu hóa đơn GTGT</span>
                <input type="checkbox" defaultChecked className="w-4 h-4 accent-[#2DCCD4]" />
              </div>
              <p className="text-[12px] text-gray-500 leading-normal">
                Hóa đơn điện tử sẽ được tự động gửi về email đăng ký sau khi kết thúc chuyến đi.
              </p>
            </div>

            <button
              onClick={() => setActiveModal(null)}
              className="w-full h-11 rounded-xl solid-primary text-white font-bold text-[14px] flex items-center justify-center cursor-pointer"
            >
              Lưu thông tin
            </button>
          </div>
        </div>
      )}

      {/* 5. Demo Booking Confirmation Sheet */}
      {activeModal === 'confirmed' && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-2xs z-50 flex items-end justify-center">
          <div className="w-full max-w-[412px] bg-white rounded-t-[26px] p-6 shadow-2xl text-center animate-in slide-in-from-bottom">
            <div className="w-16 h-16 rounded-full bg-[#DCFCE7] text-[#16A34A] flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <h3 className="text-[18px] font-bold text-[#202425]">
              Đặt xe thành công (Mô phỏng)
            </h3>
            <p className="text-[12.5px] text-gray-500 mt-1">
              Bản xem trước giao diện chuyến đi Xanh SM (Phase 6 Liquid Glass V3).
            </p>

            <div className="my-4 p-3.5 bg-[#F8FAFB] rounded-xl text-left text-[13px] space-y-2 border border-gray-100">
              <div className="flex justify-between">
                <span className="text-gray-500">Dịch vụ:</span>
                <span className="font-bold text-[#202425]">{currentVehicle.name} ({currentVehicle.capacity} chỗ)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Thời gian đón:</span>
                <span className="font-semibold text-[#202425]">{currentVehicle.eta}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Điểm đón:</span>
                <span className="font-semibold text-[#202425] truncate max-w-[200px]">{pickupName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Điểm đến:</span>
                <span className="font-semibold text-[#202425] truncate max-w-[200px]">{destinationName}</span>
              </div>
              <div className="flex justify-between border-t border-gray-200/60 pt-2">
                <span className="text-gray-500">Cước phí:</span>
                <span className="font-bold text-[#158E9A] text-[15px]">{formatVnd(finalFare)}</span>
              </div>
            </div>

            <div className="flex justify-center pt-1">
              <LiquidGlassButton
                label="Hoàn tất"
                size="md"
                variant="turquoise"
                onClick={() => setActiveModal(null)}
              />
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
