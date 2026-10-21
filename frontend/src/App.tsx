/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useRef, useState, useEffect } from 'react';
import { Search, X, CheckCircle2, ChevronRight, Sparkles, ArrowLeft, MapPin } from 'lucide-react';
import { GeoLife, placeName, getPlaceIcon, type Result, type ResearchCase } from './GeoLife';
import { apiBaseUrl, finishLogin, isSessionValid, logout as cognitoLogout } from './auth';
import type { AuthSession } from './auth';

const DEMO_DATE = '2026-09-24';
const DEMO_OFFSET = '+07:00';
const defaultDemoHour = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', hourCycle: 'h23' }).format(new Date());
const demoClock = (hour: string) => `${DEMO_DATE}T${hour}:00${DEMO_OFFSET}`;
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
} from './components/ServiceIllustrations';
import { PromoBanner } from './components/PromoBanner';
import { RestaurantRail } from './components/RestaurantRail';
import { FloatingNav, TabType } from './components/FloatingNav';
import { DestinationSearch, PlaceSelection } from './components/DestinationSearch';
import { RideBooking } from './components/RideBooking';
import { LiquidGlassButton } from './components/common/LiquidGlassButton';
import { AssetImage } from './components/common/AssetImage';
import { AssetGallery } from './components/dev/AssetGallery';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<'home' | 'search' | 'booking' | 'assets' | 'geolife' | 'ride-suggestions'>('home');
  const [activeTab, setActiveTab] = useState<TabType>('home');
  const [selectedDestination, setSelectedDestination] = useState<string>('Vincom Center Bà Triệu');
  const [activeServiceModal, setActiveServiceModal] = useState<string | null>(null);
  const [selectedRestaurant, setSelectedRestaurant] = useState<any | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [mode, setMode] = useState<'synthetic' | 'research'>('synthetic');
  const [researchAlias, setResearchAlias] = useState('');
  const [researchResult, setResearchResult] = useState<ResearchCase | null>(null);
  const [researchProfiles, setResearchProfiles] = useState<{ alias: string; user_id: string }[]>([]);
  const [researchMessage, setResearchMessage] = useState('');
  const [authError, setAuthError] = useState('');
  const [suggestionResult, setSuggestionResult] = useState<Result | null>(null);
  const [suggestionWhen, setSuggestionWhen] = useState('2026-09-24T08:00:00+07:00');
  const [suggestionOrigin, setSuggestionOrigin] = useState('s0_starting_point');
  const [demoHour, setDemoHour] = useState(`${defaultDemoHour}:00`);
  // ponytail: demo uses the fixed fixture date; add a timeline picker if multi-day playback is needed.
  const [rideSuggestions, setRideSuggestions] = useState<Result | null>(null);
  const [showRidePopup, setShowRidePopup] = useState(false);
  const [rideLoading, setRideLoading] = useState(false);
  const [rideMessage, setRideMessage] = useState('');
  const [bookingFromSuggestion, setBookingFromSuggestion] = useState(false);
  const [rideWhen, setRideWhen] = useState('');
  const rideRequest = useRef(0);
  const sessionRef = useRef(session);
  sessionRef.current = session;

  const endSession = () => {
    rideRequest.current += 1;
    sessionRef.current = null;
    setSession(null);
    setMode('synthetic');
    setResearchAlias('');
    setResearchResult(null);
    setResearchProfiles([]);
    setResearchMessage('');
    setSuggestionResult(null);
    setRideSuggestions(null);
    setRideMessage('');
    setAuthError('');
    setShowRidePopup(false);
    setBookingFromSuggestion(false);
    setActiveTab('home');
    setCurrentScreen('home');
  };

  useEffect(() => {
    finishLogin().then((restored) => {
      if (restored && isSessionValid(restored)) setSession(restored);
    }).catch(() => {
      setAuthError('Đăng nhập chưa hoàn tất. Vui lòng thử lại.');
      setCurrentScreen('geolife');
    });
  }, []);

  useEffect(() => {
    if (!session) return;
    const remaining = session.expiresAt * 1000 - Date.now();
    if (remaining <= 0) {
      endSession();
      cognitoLogout();
      return;
    }
    const timer = window.setTimeout(() => {
      endSession();
      cognitoLogout();
    }, remaining);
    return () => window.clearTimeout(timer);
  }, [session]);

  const onSessionExpired = () => {
    endSession();
    cognitoLogout();
  };

  const leaveRideSuggestions = () => {
    rideRequest.current += 1;
    setShowRidePopup(false);
    setCurrentScreen('home');
  };

  const showRideSuggestions = async (selectedAlias?: string) => {
    if (!sessionRef.current) {
      setCurrentScreen('geolife');
      return;
    }
    const request = ++rideRequest.current;
    const currentSession = sessionRef.current;
    const when = demoClock(demoHour);
    setRideWhen(when);
    setShowRidePopup(true);
    setCurrentScreen('home');
    setRideMessage('');
    if (mode === 'research') {
      setRideLoading(true);
      setResearchResult(null);
      try {
        const listed = await fetch(`${apiBaseUrl}/v2/research/cases`, {
          headers: { Authorization: `Bearer ${currentSession.accessToken}` }, cache: 'no-store',
        });
        if (listed.status === 401) { onSessionExpired(); return; }
        if (!listed.ok) throw new Error();
        const data: { cases: { alias: string; user_id: string }[] } = await listed.json();
        if (request !== rideRequest.current || sessionRef.current !== currentSession) return;
        setResearchProfiles(data.cases);
        const preferred = selectedAlias ?? researchAlias;
        const alias = data.cases.some((profile) => profile.alias === preferred) ? preferred : data.cases[0]?.alias;
        if (!alias) throw new Error();
        setResearchAlias(alias);
        const response = await fetch(`${apiBaseUrl}/v2/research/cases`, {
          method: 'POST', headers: { Authorization: `Bearer ${currentSession.accessToken}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ alias, when }), cache: 'no-store',
        });
        if (response.status === 401) { onSessionExpired(); return; }
        if (!response.ok) throw new Error();
        const caseResult: ResearchCase = await response.json();
        if (request === rideRequest.current && sessionRef.current === currentSession) setResearchResult(caseResult);
      } catch {
        if (request === rideRequest.current) setRideMessage('Không tải được điểm dừng GeoLife.');
      } finally {
        if (request === rideRequest.current) setRideLoading(false);
      }
      return;
    }
    if (!rideSuggestions) {
      setRideLoading(true);
    }
    const params = new URLSearchParams({ when, origin_place_id: suggestionOrigin });
    try {
      const response = await fetch(`${apiBaseUrl}/v2/me/destination-suggestions?${params}`, {
        headers: { Authorization: `Bearer ${currentSession.accessToken}` }, cache: 'no-store',
      });
      if (request !== rideRequest.current || sessionRef.current !== currentSession) return;
      if (response.status === 401) {
        onSessionExpired();
        return;
      }
      if (!response.ok) throw new Error('Không lấy được gợi ý từ API local.');
      const data: Result = await response.json();
      if (request === rideRequest.current && sessionRef.current === currentSession) setRideSuggestions(data);
    } catch {
      if (request === rideRequest.current) setRideMessage('Không kết nối được API gợi ý. Hãy thử lại sau.');
    } finally {
      if (request === rideRequest.current) setRideLoading(false);
    }
  };

  // Automatically pre-fetch smart destination suggestions for the current demo hour whenever session or demoHour changes
  useEffect(() => {
    if (!session || mode !== 'synthetic') return;
    const controller = new AbortController();
    const when = demoClock(demoHour);
    setRideWhen(when);
    const params = new URLSearchParams({ when, origin_place_id: suggestionOrigin });
    fetch(`${apiBaseUrl}/v2/me/destination-suggestions?${params}`, {
      headers: { Authorization: `Bearer ${session.accessToken}` },
      cache: 'no-store', signal: controller.signal,
    })
      .then((res) => {
        if (controller.signal.aborted) return null;
        if (res.status === 401) {
          onSessionExpired();
          return null;
        }
        return res.ok ? res.json() : null;
      })
      .then((data: Result | null) => {
        if (!controller.signal.aborted && data) setRideSuggestions(data);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [session, demoHour, suggestionOrigin, mode]);

  // 8 additional services strictly ordered as requested:
  // bike -> intercity -> express -> subscription -> giftcard -> vinbus -> buyvinfast -> car-rent
  const additionalServices = [
    {
      id: 'bike',
      assetId: 'bike',
      label: 'Xe máy',
      icon: ScooterIcon,
      desc: 'Xe máy điện Xanh SM Bike êm ái, bảo vệ môi trường.',
    },
    {
      id: 'intercity',
      assetId: 'intercity',
      label: 'Đi liên tỉnh',
      icon: IntercityIcon,
      desc: 'Di chuyển liên tỉnh thoải mái với giá trọn gói niêm yết.',
    },
    {
      id: 'express',
      assetId: 'express',
      label: 'Giao hàng',
      icon: DeliveryIcon,
      desc: 'Dịch vụ giao hàng siêu tốc Xanh Express an toàn, nhanh chóng.',
    },
    {
      id: 'subscription',
      assetId: 'subscription',
      label: 'Gói hội viên',
      icon: MembershipIcon,
      desc: 'Đặc quyền Xanh Club tiết kiệm tới 40% chi phí di chuyển.',
    },
    {
      id: 'giftcard',
      assetId: 'giftcard',
      label: 'Thẻ quà tặng',
      icon: GiftCardIcon,
      desc: 'Thẻ quà tặng di chuyển thông minh cho bạn bè, người thân.',
    },
    {
      id: 'vinbus',
      assetId: 'vinbus',
      label: 'VinBus',
      icon: VinBusIcon,
      desc: 'Tra cứu lộ trình và vé xe buýt điện VinBus thông minh.',
    },
    {
      id: 'buyvinfast',
      assetId: 'buyvinfast',
      label: 'Mua VinFast',
      icon: BuyVinFastIcon,
      desc: 'Hệ thống showroom ô tô điện VinFast chính hãng: VF 3, VF 5, VF 6, VF 7, VF 8, VF 9.',
    },
    {
      id: 'car-rent',
      assetId: 'car-rent',
      label: 'Thuê xe tự lái',
      icon: CarRentIcon,
      desc: 'Dịch vụ thuê xe ô tô điện VinFast tự lái theo ngày hoặc dài hạn tiện lợi.',
    },
  ];

  const handlePlaceSelect = (place: PlaceSelection) => {
    setSelectedDestination(place.name + (place.entrance ? ` (${place.entrance})` : ''));
    setBookingFromSuggestion(false);
    setCurrentScreen('booking');
  };

  return (
    <div className="min-h-screen w-full bg-[#E8ECEE] flex justify-center items-center md:py-6 select-none font-sans">
      {/* Mobile Frame Container (matches 375x812 - 390x844 mobile ergonomics) */}
      <div className="w-full max-w-[412px] h-[100dvh] md:h-[864px] md:max-h-[92vh] md:rounded-[44px] md:shadow-[0_20px_60px_rgba(15,35,40,0.22)] md:border-[7px] md:border-[#1E2528] bg-white flex flex-col relative overflow-hidden">
        
        <div aria-label="Thanh trạng thái iPhone mô phỏng" className="absolute top-0 left-0 right-0 z-40 flex h-9 items-center justify-between bg-transparent px-6 pointer-events-none font-['SF_Pro_Text',-apple-system,BlinkMacSystemFont,'Segoe_UI',sans-serif] text-[13px] font-semibold tracking-[-0.02em] text-[#202425]">
          <label title="Giờ mô phỏng; chạm để đổi" className="pointer-events-auto">
            <span className="sr-only">Giờ mô phỏng</span>
            <select aria-label="Giờ mô phỏng" value={demoHour} onChange={(event) => setDemoHour(event.target.value)} className="w-[52px] appearance-none bg-transparent text-[14px] font-bold outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] cursor-pointer">
              {Array.from({ length: 24 }, (_, hour) => {
                const time = `${hour.toString().padStart(2, '0')}:00`;
                return <option key={time} value={time}>{time}</option>;
              })}
            </select>
          </label>
          <span className="flex items-center gap-[5px]" aria-hidden="true">
            <svg width="17" height="13" viewBox="0 0 17 13" fill="currentColor"><rect x="0" y="9" width="2.5" height="4" rx="0.5"/><rect x="4" y="6.5" width="2.5" height="6.5" rx="0.5"/><rect x="8" y="3.5" width="2.5" height="9.5" rx="0.5"/><rect x="12" y="0" width="2.5" height="13" rx="0.5"/></svg>
            <svg width="17" height="13" viewBox="0 0 17 13" fill="none"><path d="M1 4.2a11.8 11.8 0 0 1 15 0M3.5 7a8 8 0 0 1 10 0M6.2 9.5a4.2 4.2 0 0 1 4.6 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><circle cx="8.5" cy="11.7" r="1" fill="currentColor"/></svg>
            <svg width="24" height="13" viewBox="0 0 24 13" fill="none"><rect x="0.7" y="1" width="20" height="11" rx="2.6" stroke="currentColor" strokeWidth="1.3"/><rect x="2.6" y="2.8" width="15" height="7.4" rx="1" fill="currentColor"/><path d="M22 4.6v3.8a2 2 0 0 0 0-3.8Z" fill="currentColor"/></svg>
          </span>
        </div>
        {/* Screen Routing */}
        {currentScreen === 'assets' ? (
          <AssetGallery onClose={() => setCurrentScreen('home')} />
        ) : currentScreen === 'geolife' ? (
          <GeoLife
            session={session}
            authError={authError}
            result={suggestionResult}
            onResult={setSuggestionResult}
            when={suggestionWhen}
            onWhenChange={setSuggestionWhen}
            origin={suggestionOrigin}
            onOriginChange={setSuggestionOrigin}
            onLogout={() => {
              endSession();
              cognitoLogout();
            }}
            onBack={() => {
              setActiveTab('home');
              setCurrentScreen('home');
            }}
            onBookDestination={(destination) => {
              setSelectedDestination(destination);
              setBookingFromSuggestion(true);
              setCurrentScreen('booking');
            }}
            mode={mode}
            onModeChange={(next) => { rideRequest.current += 1; setShowRidePopup(false); setRideSuggestions(null); setResearchResult(null); setMode(next); }}
            researchAlias={researchAlias}
            onResearchAliasChange={(alias) => { rideRequest.current += 1; setResearchAlias(alias); setResearchResult(null); }}
            researchResult={researchResult}
            onResearchResultChange={setResearchResult}
          />
        ) : currentScreen === 'ride-suggestions' ? (
          <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar bg-white px-4 pb-8 text-[#202425]">
            <header className="flex items-center gap-3 border-b border-[#EDF0F2] py-3">
              <button type="button" onClick={leaveRideSuggestions} aria-label="Quay lại trang chủ" className="glass-button flex h-10 w-10 items-center justify-center rounded-full"><ArrowLeft className="h-5 w-5" /></button>
              <h1 className="text-[17px] font-bold">Gợi ý điểm đến</h1>
            </header>
            <div className="mt-5 rounded-[18px] border border-[#EDF0F2] bg-[#F8FAFB] p-4">
              <p className="text-[13px] font-semibold">Giờ mô phỏng: {rideWhen.slice(11, 16)}</p>
              <p className="mt-1 text-[12px] text-[#737C7F]">{DEMO_DATE} · tài khoản {session?.account} · lịch sử synthetic</p>
            </div>
            <p className="mt-5 text-[13px] text-[#737C7F]">Địa điểm gợi ý cho chuyến đi lúc này:</p>
            {rideLoading && <p role="status" className="mt-4 text-[13px]">Đang tải gợi ý...</p>}
            {rideMessage && <p role="alert" className="mt-4 text-[13px] text-red-600">{rideMessage}</p>}
            {rideSuggestions?.status === 'abstained' && <p role="status" className="mt-4 text-[13px]">Chưa đủ lịch sử synthetic để đưa ra gợi ý. Bạn có thể tự tìm điểm đến.</p>}
            {rideSuggestions?.status === 'suggested' && (
              <ol className="mt-3 space-y-2">
                {rideSuggestions.suggestions.map((item) => (
                  <li key={item.place_ref}>
                    <button type="button" onClick={() => { setSelectedDestination(placeName(item.place_ref)); setBookingFromSuggestion(true); setCurrentScreen('booking'); }} className="glass-card flex w-full items-center gap-3 rounded-[18px] p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#E0F8FA] font-bold text-[#158E9A]">{item.rank}</span>
                      <span className="min-w-0 flex-1"><strong className="block text-[14px]">{placeName(item.place_ref)}</strong><small className="block text-[11px] text-[#737C7F]">{item.place_ref} · {item.explanations.join(' · ')}</small></span>
                      <ChevronRight className="h-4 w-4 shrink-0 text-[#158E9A]" />
                    </button>
                  </li>
                ))}
              </ol>
            )}
            <button type="button" onClick={() => setCurrentScreen('search')} className="mt-6 flex items-center gap-2 text-[13px] font-semibold text-[#158E9A]"><MapPin className="h-4 w-4" /> Tự chọn điểm đến</button>
            <p className="mt-6 text-[11px] leading-relaxed text-[#737C7F]">Gợi ý chỉ dùng dữ liệu synthetic; không phải vị trí thật, điểm tin cậy hay tuyến đường đã tính toán.</p>
          </div>
        ) : currentScreen === 'search' ? (
          <DestinationSearch
            onBack={() => setCurrentScreen('home')}
            onSelectPlace={handlePlaceSelect}
            suggestions={rideSuggestions}
            demoHour={demoHour}
          />
        ) : currentScreen === 'booking' ? (
          <RideBooking
            onBack={() => {
              if (bookingFromSuggestion) {
                setShowRidePopup(true);
                setCurrentScreen('home');
              } else {
                setCurrentScreen('search');
              }
            }}
            destinationName={selectedDestination}
          />
        ) : (
          /* SCREEN A: HOME SCREEN (Matches REF-01 and image.png) */
          <div className="flex-1 overflow-y-auto no-scrollbar relative flex flex-col bg-white">
            
            {/* Top Isometric City Map Backdrop (High-key blurred urban visual fading down) */}
            <div className="absolute top-0 left-0 right-0 h-[280px] pointer-events-none overflow-hidden z-0">
              <svg
                viewBox="0 0 400 280"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="w-full h-full object-cover opacity-65"
                preserveAspectRatio="xMidYMid slice"
              >
                <defs>
                  <linearGradient id="fadeToWhite" x1="0" y1="0" x2="0" y2="280" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#F1F7F8" stopOpacity="0.9" />
                    <stop offset="0.6" stopColor="#F8FCFD" stopOpacity="0.8" />
                    <stop offset="1" stopColor="#FFFFFF" />
                  </linearGradient>
                  <linearGradient id="bldgGrad" x1="0" y1="0" x2="20" y2="40" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#E2E8F0" />
                    <stop offset="1" stopColor="#CBD5E1" />
                  </linearGradient>
                </defs>

                {/* Base city fill */}
                <rect width="400" height="280" fill="url(#fadeToWhite)" />

                {/* 3D Isometric building grid shapes (matching screenshot upper backdrop) */}
                <g opacity="0.45" transform="translate(10, 0)">
                  {/* Building 1 */}
                  <polygon points="40,20 80,40 40,60 0,40" fill="#E2E8F0" />
                  <polygon points="0,40 40,60 40,90 0,70" fill="#CBD5E1" />
                  <polygon points="40,60 80,40 80,70 40,90" fill="#94A3B8" />

                  {/* Building 2 */}
                  <polygon points="120,10 170,35 120,60 70,35" fill="#E2E8F0" />
                  <polygon points="70,35 120,60 120,100 70,75" fill="#CBD5E1" />
                  <polygon points="120,60 170,35 170,75 120,100" fill="#94A3B8" />

                  {/* Building 3 */}
                  <polygon points="230,15 270,35 230,55 190,35" fill="#E2E8F0" />
                  <polygon points="190,35 230,55 230,85 190,65" fill="#CBD5E1" />
                  <polygon points="230,55 270,35 270,65 230,85" fill="#94A3B8" />

                  {/* Building 4 */}
                  <polygon points="320,5 370,30 320,55 270,30" fill="#E2E8F0" />
                  <polygon points="270,30 320,55 320,95 270,70" fill="#CBD5E1" />
                  <polygon points="320,55 370,30 370,70 320,95" fill="#94A3B8" />

                  {/* Middle row buildings */}
                  <polygon points="80,80 130,105 80,130 30,105" fill="#E2E8F0" />
                  <polygon points="30,105 80,130 80,160 30,135" fill="#CBD5E1" />
                  <polygon points="80,130 130,105 130,135 80,160" fill="#94A3B8" />

                  <polygon points="200,75 250,100 200,125 150,100" fill="#E2E8F0" />
                  <polygon points="150,100 200,125 200,155 150,130" fill="#CBD5E1" />
                  <polygon points="200,125 250,100 250,130 200,155" fill="#94A3B8" />

                  <polygon points="310,70 360,95 310,120 260,95" fill="#E2E8F0" />
                  <polygon points="260,95 310,120 310,150 260,125" fill="#CBD5E1" />
                  <polygon points="310,120 360,95 360,125 310,150" fill="#94A3B8" />

                  {/* Road grid lines */}
                  <line x1="0" y1="40" x2="400" y2="240" stroke="#FFFFFF" strokeWidth="6" />
                  <line x1="400" y1="40" x2="0" y2="240" stroke="#FFFFFF" strokeWidth="6" />
                </g>
              </svg>
            </div>

            {/* No external background glow outside the 2 primary action cards */}

            {/* Main Content Area */}
            <div className="relative z-10 flex flex-col pt-10 pb-28">
              
              {/* 1. Global Destination Search Bar (Liquid Glass V3 elevated input) */}
              <div className="px-4 pt-1 pb-1">
                <button
                  onClick={() => setCurrentScreen('search')}
                  className="w-full h-[52px] glass-input rounded-2xl flex items-center px-4 gap-3 cursor-pointer active:scale-[0.99] transition-all text-left group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
                >
                  <Search className="w-5 h-5 text-[#8E989D] group-hover:text-[#2DCCD4] transition-colors shrink-0" strokeWidth={2.2} />
                  <span className="text-[15px] font-medium text-[#8E989D] truncate">
                    Bạn muốn đi đâu?
                  </span>
                </button>
              </div>

              {/* 2. Primary Actions Row (Two equal-width cards: "Đặt ô tô" & "Đặt món ăn") */}
              <div className="grid grid-cols-2 gap-3 px-4 mt-3">
                {/* Card 1: Đặt ô tô (Borderless Liquid Glass with soft cyan right-edge glow) */}
                <button
                  type="button"
                  onClick={() => { void showRideSuggestions(); }}
                  className="h-[108px] w-full rounded-[22px] p-4 relative overflow-hidden glass-card-car cursor-pointer active:scale-95 transition-all flex flex-col justify-between group text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
                >
                  {/* High contrast dark bold text - completely crisp and opaque */}
                  <span className="relative z-10 text-[17px] font-bold text-[#0F172A] tracking-tight leading-none select-none">
                    Đặt ô tô
                  </span>

                  {/* Soft ambient glow at middle of right edge - expanded spread */}
                  <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-24 h-24 rounded-full bg-[#2DCCD4]/16 blur-xl pointer-events-none" />
                  
                  {/* Cyan electric car 3D asset */}
                  <div className="absolute right-1 bottom-1 pointer-events-none z-10 transform translate-x-1 translate-y-1 group-hover:scale-105 transition-transform duration-300">
                    <AssetImage
                      assetId="car"
                      fallback={<CarIllustration className="w-26 h-18" />}
                      className="w-24 h-20 object-contain drop-shadow-[0_4px_10px_rgba(0,0,0,0.06)]"
                    />
                  </div>
                </button>

                {/* Card 2: Đặt món ăn (Borderless Liquid Glass with soft golden-peach right-edge glow) */}
                <div
                  onClick={() => setActiveServiceModal('Đặt món ăn')}
                  className="h-[108px] rounded-[22px] p-4 relative overflow-hidden glass-card-food cursor-pointer active:scale-95 transition-all flex flex-col justify-between group"
                >
                  {/* High contrast dark bold text - completely crisp and opaque */}
                  <span className="relative z-10 text-[17px] font-bold text-[#0F172A] tracking-tight leading-none select-none">
                    Đặt món ăn
                  </span>

                  {/* Soft ambient glow at middle of right edge - expanded spread */}
                  <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-24 h-24 rounded-full bg-[#F59E0B]/14 blur-xl pointer-events-none" />

                  {/* Food / Takeout 3D asset */}
                  <div className="absolute right-1.5 bottom-1 pointer-events-none z-10 transform translate-y-1 group-hover:scale-105 transition-transform duration-300">
                    <AssetImage
                      assetId="food"
                      fallback={<FoodIllustration className="w-24 h-18" />}
                      className="w-22 h-18 object-contain drop-shadow-[0_4px_10px_rgba(0,0,0,0.06)]"
                    />
                  </div>
                </div>
              </div>

              {/* 3. Section Row: "Dịch vụ khác" + "Xem tất cả" */}
              <div className="flex items-center justify-between px-4 mt-5 mb-2.5">
                <h2 className="text-[17px] font-semibold text-[#1E2528] tracking-tight">
                  Dịch vụ khác
                </h2>
                <button
                  onClick={() => setActiveServiceModal('Tất cả dịch vụ')}
                  className="text-[13px] font-medium text-[#737C7F] hover:text-[#2DCCD4] transition-colors flex items-center gap-0.5 active:scale-95 cursor-pointer"
                >
                  <span>Xem tất cả</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* 4. 4 × 2 Services Grid: bike, intercity, express, subscription, giftcard, vinbus, buyvinfast, car-rent */}
              <div className="grid grid-cols-4 gap-2.5 px-4">
                {additionalServices.map((service) => {
                  const IconComp = service.icon;
                  return (
                    <button
                      key={service.id}
                      onClick={() => setActiveServiceModal(service.label)}
                      className="glass-card-service active:scale-95 rounded-[18px] py-2 px-1 flex flex-col items-center justify-center min-h-[96px] group cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
                    >
                      <div className="w-12 h-12 flex items-center justify-center group-hover:scale-105 transition-transform">
                        <AssetImage
                          assetId={service.assetId}
                          fallback={<IconComp className="w-11 h-11" />}
                          className="w-11 h-11 object-contain drop-shadow-xs"
                        />
                      </div>
                      <span className="text-[11.5px] font-medium text-[#252C30] text-center mt-1.5 leading-snug line-clamp-1 group-hover:text-[#158E9A] transition-colors">
                        {service.label}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* 5. Promotional Carousel Banner */}
              <PromoBanner
                onBannerClick={() => setActiveServiceModal('Ưu đãi giao hàng 40K')}
              />

              {/* 6. Recommendations: "Gợi ý quán ngon" */}
              <RestaurantRail
                onSelectRestaurant={(rest) => setSelectedRestaurant(rest)}
              />

            </div>
          </div>
        )}

        {/* 7. Floating Translucent Navigation Dock (Fixed above bottom of screen frame) */}
        {currentScreen === 'home' && (
          <FloatingNav
            activeTab={activeTab}
            onTabChange={(tab) => {
              setActiveTab(tab);
              if (tab === 'profile') {
                setActiveServiceModal(null);
                setCurrentScreen('geolife');
              } else if (tab !== 'home') {
                setActiveServiceModal(tab === 'history' ? 'Lịch sử chuyến đi' : 'Thông báo mới');
              }
            }}
          />
        )}

        {/* Modal: Service Detail & Feedback Sheet */}
        {activeServiceModal && (
          <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-end justify-center animate-in fade-in">
            <div className="w-full max-w-[412px] bg-white rounded-t-[28px] p-6 shadow-2xl animate-in slide-in-from-bottom duration-200">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-[#E0F8FA] text-[#158E9A] flex items-center justify-center">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <h3 className="text-[17px] font-bold text-gray-900">{activeServiceModal}</h3>
                </div>
                <button
                  onClick={() => setActiveServiceModal(null)}
                  className="w-8 h-8 rounded-full glass-button flex items-center justify-center text-gray-500 hover:text-gray-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="py-4 text-[13.5px] text-gray-600 leading-relaxed">
                {activeServiceModal === 'Đặt món ăn' ? (
                  <p>
                    Dịch vụ giao đồ ăn nóng hổi từ hàng ngàn quán ngon chọn lọc, tài xế Xanh SM giao hàng bằng xe máy điện êm ái, lịch sự.
                  </p>
                ) : activeServiceModal === 'Ưu đãi giao hàng 40K' ? (
                  <div className="space-y-3.5">
                    <p className="text-[13px] text-gray-700">
                      Mã <strong>XANH40K</strong>: Giảm ngay 40.000đ cho chuyến đi hoặc giao hàng đầu tiên! Trải nghiệm 2 thiết kế Liquid Glass / Glassmorphism cao cấp:
                    </p>
                    
                    {/* Liquid Glass Showcase 1: Caustic Button (Get started) */}
                    <div className="py-4 px-3 rounded-2xl bg-gradient-to-b from-[#f5f5f7] to-[#e2e2e8] flex flex-col items-center justify-center border border-gray-200/80 shadow-inner">
                      <div className="text-[11px] font-bold text-gray-600 uppercase tracking-wider mb-2.5">
                        1. Caustic Liquid Glass (Thấu kính lồi)
                      </div>
                      <LiquidGlassButton
                        label="Get started"
                        size="md"
                        variant="turquoise"
                        onClick={() => {
                          setActiveServiceModal(null);
                          setCurrentScreen('booking');
                        }}
                      />
                      <span className="text-[10.5px] text-[#737C7F] mt-2 font-medium">
                        Filter contrast(3) • Viền specular phản xạ 45°
                      </span>
                    </div>

                    {/* Liquid Glass Showcase 2: Caustic Button */}
                    <div className="py-4 px-3 rounded-2xl bg-[#E2E8EC] flex flex-col items-center justify-center border border-gray-200/80 shadow-inner relative overflow-hidden">
                      <div className="text-[11px] font-bold text-[#0E4850] uppercase tracking-wider mb-2.5">
                        2. Caustic Liquid Glass (Thấu kính lồi)
                      </div>
                      <LiquidGlassButton
                        label="Đặt xe Xanh Car"
                        variant="turquoise"
                        size="md"
                        onClick={() => {
                          setActiveServiceModal(null);
                          setCurrentScreen('booking');
                        }}
                      />
                      <span className="text-[10.5px] text-[#737C7F] mt-2 font-medium">
                        Viền specular phản xạ 45°
                      </span>
                    </div>
                  </div>
                ) : activeServiceModal === 'Tất cả dịch vụ' ? (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                    {additionalServices.map((s) => (
                      <div
                        key={s.id}
                        onClick={() => {
                          setActiveServiceModal(null);
                          if (s.id === 'bike' || s.id === 'intercity' || s.id === 'car-rent') {
                            setCurrentScreen('booking');
                          }
                        }}
                        className="p-2.5 rounded-xl bg-gray-50 hover:bg-gray-100/80 transition flex items-center justify-between cursor-pointer"
                      >
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 flex items-center justify-center">
                            <AssetImage
                              assetId={s.assetId}
                              fallback={<s.icon className="w-7 h-7" />}
                              className="w-7 h-7 object-contain"
                            />
                          </div>
                          <div>
                            <span className="font-semibold text-gray-800 text-[13px] block">{s.label}</span>
                            <span className="text-[11px] text-gray-500 line-clamp-1">{s.desc}</span>
                          </div>
                        </div>
                        <span className="text-[11px] text-[#2DCCD4] font-bold shrink-0 ml-2">Khám phá</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>
                    Tính năng <strong>{activeServiceModal}</strong> đã sẵn sàng hoạt động trong hệ sinh thái thuần điện Xanh SM. Trải nghiệm ngay các chuyến đi văn minh, không khói bụi và không tiếng ồn.
                  </p>
                )}
              </div>

              <div className="pt-2">
                <button
                  onClick={() => {
                    const modal = activeServiceModal;
                    setActiveServiceModal(null);
                    if (modal === 'Xe máy' || modal === 'Đi liên tỉnh' || modal === 'Thuê xe tự lái') {
                      setCurrentScreen('booking');
                    }
                  }}
                  className="w-full h-11 rounded-xl solid-primary text-white font-bold text-[14px] flex items-center justify-center cursor-pointer"
                >
                  Đóng
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Restaurant Preview Sheet */}
        {selectedRestaurant && (
          <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-end justify-center animate-in fade-in">
            <div className="w-full max-w-[412px] bg-white rounded-t-[28px] p-6 shadow-2xl animate-in slide-in-from-bottom duration-200">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <div>
                  <h3 className="text-[17px] font-bold text-gray-900">{selectedRestaurant.name}</h3>
                  <p className="text-[12px] text-gray-500 mt-0.5">{selectedRestaurant.category} • ⭐ {selectedRestaurant.rating}</p>
                </div>
                <button
                  onClick={() => setSelectedRestaurant(null)}
                  className="w-8 h-8 rounded-full glass-button flex items-center justify-center text-gray-500 hover:text-gray-800 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Menu Poster Banner in Preview Sheet */}
              <div className="mt-3.5 w-full rounded-2xl overflow-hidden aspect-[16/10] bg-gray-100 shadow-xs border border-gray-100">
                <AssetImage
                  assetId={selectedRestaurant.assetId || selectedRestaurant.id}
                  alt={selectedRestaurant.name}
                  className="w-full h-full object-cover"
                />
              </div>

              <div className="py-3.5 space-y-2.5">
                <div className="flex items-center justify-between text-[13px] bg-[#E0F8FA] p-3 rounded-xl text-[#158E9A] font-medium">
                  <span>Thời gian giao: {selectedRestaurant.deliveryTime}</span>
                  <span>Khoảng cách: {selectedRestaurant.distance}</span>
                </div>
                <p className="text-[12.5px] text-gray-600">
                  Thực đơn phong phú, chế biến tươi ngon mỗi ngày. Tài xế Xanh SM giao hàng nhanh chóng bằng xe máy điện thuần khiết.
                </p>
              </div>

              <button
                onClick={() => setSelectedRestaurant(null)}
                className="w-full h-11 rounded-xl solid-primary text-white font-bold text-[14px] flex items-center justify-center cursor-pointer"
              >
                Đặt món ngay
              </button>
            </div>
          </div>
        )}

        {/* Modal: Home Screen Smart Ride Suggestions Bottom Sheet */}
        {currentScreen === 'home' && showRidePopup && (
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-2xs z-50 flex items-end justify-center animate-in fade-in duration-200"
            onClick={leaveRideSuggestions}
          >
            <div
              className="w-full max-w-[412px] bg-white rounded-t-[28px] p-5 shadow-2xl animate-in slide-in-from-bottom duration-300 max-h-[85vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Drag handle */}
              <div className="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-3 shrink-0" />

              {/* Header */}
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 shrink-0">
                <div>
                  <h3 className="text-[17px] font-bold text-[#0E4850] leading-tight">
                    Gợi ý điểm đến
                  </h3>
                  <p className="text-[12px] text-[#737C7F] mt-0.5 font-medium">
                    Giờ mô phỏng: {rideWhen.slice(11, 16) || demoHour}
                  </p>
                  <p className="text-[11px] text-[#737C7F]">
                    {mode === 'research' ? `GeoLife user ID ${researchResult?.user_id ?? ''} · gợi ý từ lịch sử` : `${DEMO_DATE} · tài khoản ${session?.account} · lịch sử synthetic`}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={leaveRideSuggestions}
                  aria-label="Quay lại trang chủ"
                  className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200 active:scale-90 transition cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Content */}
              <div className="py-3 flex-1 overflow-y-auto no-scrollbar">
                {mode === 'research' && researchProfiles.length > 1 && (
                  <label className="mb-3 block text-[12px] font-semibold" htmlFor="ride-research-profile">
                    GeoLife user ID
                    <select id="ride-research-profile" value={researchAlias} onChange={(event) => { setResearchAlias(event.target.value); setResearchResult(null); void showRideSuggestions(event.target.value); }} className="mt-1 w-full rounded-xl border border-gray-200 bg-white p-2 text-[13px]">
                      {researchProfiles.map((profile) => <option key={profile.alias} value={profile.alias}>{profile.user_id}</option>)}
                    </select>
                  </label>
                )}
                {mode === 'research' && researchResult && (
                  <div>
                    <p className="text-[12.5px] text-[#737C7F] mb-2.5 font-medium">Điểm đến gợi ý từ lịch sử GeoLife (không phải vị trí hiện tại):</p>
                    {researchResult.suggestions.length ? (
                      <ol className="space-y-2.5">
                        {researchResult.suggestions.map((item) => (
                          <li key={item.place_ref}>
                            <button type="button" onClick={() => { setSelectedDestination(`${item.label} · GeoLife ${researchResult.user_id}`); setBookingFromSuggestion(true); setShowRidePopup(false); setCurrentScreen('booking'); }} className="glass-card flex w-full items-center gap-3 rounded-[20px] p-3 text-left border border-gray-100 hover:border-[#2DCCD4]/40 cursor-pointer">
                              <span className="w-10 h-10 shrink-0 flex items-center justify-center">{getPlaceIcon(item.label === 'HOME' ? 'home' : item.label === 'OFFICE' ? 'office' : 'station')}</span>
                              <span className="min-w-0 flex-1"><strong className="block text-[14.5px]">{item.label}</strong><small className="block text-[11.5px] text-[#737C7F]">{item.explanations.join(' · ')}</small></span>
                              <span className="text-[11px] font-bold text-[#127F8B]">Top {item.rank} · Đặt xe</span>
                            </button>
                          </li>
                        ))}
                      </ol>
                    ) : <p role="status" className="text-[13px]">Chưa đủ lịch sử lặp lại để gợi ý điểm đến.</p>}
                  </div>
                )}
                {rideLoading && (
                  <div className="py-8 text-center flex flex-col items-center justify-center">
                    <div className="w-8 h-8 border-3 border-[#2DCCD4] border-t-transparent rounded-full animate-spin mb-3" />
                    <p role="status" className="text-[13px] font-medium text-[#737C7F]">
                      Đang tải gợi ý...
                    </p>
                  </div>
                )}

                {rideMessage && (
                  <div role="alert" className="p-3 rounded-xl bg-red-50 text-red-600 text-[13px] font-medium">
                    {rideMessage}
                  </div>
                )}

                {mode === 'synthetic' && rideSuggestions?.status === 'abstained' && (
                  <div className="py-6 text-center">
                    <p role="status" className="text-[13px] text-[#737C7F]">
                      Chưa đủ lịch sử synthetic để đưa ra gợi ý. Bạn có thể tự tìm điểm đến.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setShowRidePopup(false);
                        setCurrentScreen('search');
                      }}
                      className="mt-4 px-4 py-2.5 rounded-xl bg-[#2DCCD4] text-white text-[13px] font-bold hover:bg-[#20BDC8] active:scale-95 transition cursor-pointer"
                    >
                      Tự chọn điểm đến
                    </button>
                  </div>
                )}

                {mode === 'synthetic' && rideSuggestions?.status === 'suggested' && (
                  <div>
                    <p className="text-[12.5px] text-[#737C7F] mb-2.5 font-medium">
                      Địa điểm gợi ý cho chuyến đi lúc này:
                    </p>
                    <ol className="space-y-2.5">
                      {rideSuggestions.suggestions.map((item) => (
                        <li key={item.place_ref}>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedDestination(placeName(item.place_ref));
                              setBookingFromSuggestion(true);
                              setShowRidePopup(false);
                              setCurrentScreen('booking');
                            }}
                            className="glass-card flex w-full items-center gap-3 rounded-[20px] p-3 text-left border border-gray-100 hover:border-[#2DCCD4]/40 hover:bg-[#E0F8FA]/20 active:scale-[0.98] transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] group"
                          >
                            <div className="w-10 h-10 shrink-0 flex items-center justify-center group-hover:scale-105 transition-transform">
                              {getPlaceIcon(item.place_ref, "w-10 h-10 object-contain drop-shadow-2xs")}
                            </div>
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center gap-2">
                                <strong className="block text-[14.5px] font-bold text-[#202425] leading-snug group-hover:text-[#127F8B] transition-colors">
                                  {placeName(item.place_ref)}
                                </strong>
                                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-[#E0F8FA] text-[#127F8B] border border-[#2DCCD4]/30 shrink-0">
                                  Top {item.rank}
                                </span>
                              </span>
                              <small className="block text-[11.5px] text-[#737C7F] truncate mt-0.5">
                                {item.place_ref} · {item.explanations.join(' · ')}
                              </small>
                            </span>
                            <div className="shrink-0 flex items-center gap-1 text-[12px] font-bold text-[#127F8B] bg-[#E0F8FA] group-hover:bg-[#D4F4F7] px-2.5 py-1 rounded-xl border border-[#2DCCD4]/30">
                              <span>Đặt xe</span>
                              <ChevronRight className="h-3.5 w-3.5 text-[#127F8B]" />
                            </div>
                          </button>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>

              {/* Footer actions */}
              <div className="pt-3 border-t border-gray-100 flex items-center justify-between gap-2 shrink-0">
                {mode === 'synthetic' && <button
                  type="button"
                  onClick={() => {
                    setShowRidePopup(false);
                    setCurrentScreen('search');
                  }}
                  className="flex-1 h-11 rounded-xl bg-gray-100 hover:bg-gray-200 text-[#202425] font-bold text-[13px] flex items-center justify-center gap-2 active:scale-95 transition cursor-pointer"
                >
                  <MapPin className="h-4 w-4 text-[#158E9A]" />
                  <span>Tự chọn điểm đến</span>
                </button>}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
