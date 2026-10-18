import { useRef, useState, type FormEvent } from 'react';
import { BETA_MODE } from './auth/cognito';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Clock,
  Clock3,
  LockKeyhole,
  LogOut,
  MapPin,
  ShieldCheck,
  Sparkles,
  UserRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Compass,
  Zap,
  Coffee,
  ShoppingBag,
  Dumbbell,
  BookOpen,
  Trees,
} from 'lucide-react';
import { LiquidGlassButton } from './components/common/LiquidGlassButton';
import { PrismaticGlassButton } from './components/common/PrismaticGlassButton';
import loginBg from './assets/greensm-login-bg-1080x1920.png';
import profileBg from './assets/greensm-profile-bg-1920x1080.png';
import defaultAvatar from './assets/default-avatar-circle-1080x1080.png';
import placeCafe from './assets/place-cafe.png';
import placeGym from './assets/place-gym.png';
import placeLibrary from './assets/place-library.png';
import placeMall from './assets/place-mall.png';
import placeMarket from './assets/place-market.png';
import placePark from './assets/place-park.png';
import placeStation from './assets/place-station.png';

const placeIcons: Record<string, string> = {
  cafe: placeCafe,
  gym: placeGym,
  library: placeLibrary,
  market: placeMarket,
  park: placePark,
  station: placeStation,
  unseen_station: placeStation,
  mall: placeMall,
};

const placeNames: Record<string, string> = {
  library: 'Thư viện',
  market: 'Khu chợ thực phẩm',
  gym: 'Phòng tập Gym',
  cafe: 'Quán Cà Phê',
  park: 'Công viên cây xanh',
  station: 'Ga tàu & Bến xe',
  unseen_station: 'Ga tàu & Bến xe',
  mall: 'Trung tâm thương mại',
};

const PRESET_TIMES = [
  { label: '08:00 Sáng', desc: 'Cà phê & Đi làm', time: '2026-09-24T08:00:00+07:00' },
  { label: '12:00 Trưa', desc: 'Bữa trưa', time: '2026-09-24T12:00:00+07:00' },
  { label: '18:00 Tối', desc: 'Tan sở & Thể thao', time: '2026-09-24T18:00:00+07:00' },
];

export function placeName(ref: string) {
  return placeNames[ref.replace(/^s\d+_/, '')] ?? ref;
}

export function getPlaceIcon(ref: string, className = "w-10 h-10 object-contain drop-shadow-sm") {
  const clean = ref.replace(/^s\d+_/, '').toLowerCase();
  const iconSrc = placeIcons[clean];
  if (iconSrc) {
    return (
      <img
        src={iconSrc}
        alt={placeName(ref)}
        className={className}
      />
    );
  }
  return <MapPin className="w-5 h-5 text-[#158E9A]" />;
}

type Suggestion = { rank: number; place_ref: string; explanations: string[] };
export type Result = {
  source: 'synthetic_fixture';
  status: 'suggested' | 'abstained';
  suggestions: Suggestion[];
  note: string;
};

export function GeoLife({
  session,
  result,
  onResult,
  when,
  onWhenChange,
  origin,
  onOriginChange,
  onLogin,
  onLogout,
  onBack,
  onBookDestination,
}: {
  session: { account: string; token: string } | null;
  result: Result | null;
  onResult: (result: Result | null) => void;
  when: string;
  onWhenChange: (when: string) => void;
  origin: string;
  onOriginChange: (origin: string) => void;
  onLogin: (account: string, token: string) => void;
  onLogout: () => void;
  onBack: () => void;
  onBookDestination?: (destination: string) => void;
}) {
  const [account, setAccount] = useState('demo_000');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const token = session?.token ?? '';
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const loginForm = useRef<HTMLFormElement>(null);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    onResult(null);
    try {
      const response = await fetch('/v2/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: account.trim(), password }),
        cache: 'no-store',
      });
      setPassword('');
      if (!response.ok) {
        throw new Error(
          response.status === 503
            ? 'API chưa được cấu hình tài khoản demo.'
            : 'Đăng nhập thất bại. Kiểm tra lại tài khoản hoặc mật khẩu demo.'
        );
      }
      const data: { account_id: string; access_token: string } = await response.json();
      onLogin(data.account_id, data.access_token);
    } catch (error) {
      setMessage(
        error instanceof Error && error.message !== 'Failed to fetch'
          ? error.message
          : 'Không kết nối được API local (127.0.0.1:8000).'
      );
    } finally {
      setPassword('');
      setBusy(false);
    }
  }

  async function suggest(overrideWhen?: string) {
    const targetWhen = (overrideWhen || when).trim();
    setBusy(true);
    onResult(null);
    const params = new URLSearchParams({ when: targetWhen });
    if (origin.trim()) params.set('origin_place_id', origin.trim());
    try {
      const response = await fetch(`${BETA_MODE ? '/v3/beta/destination-suggestions' : '/v2/me/destination-suggestions'}?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (response.status === 401) {
        onLogout();
        return;
      }
      if (!response.ok) {
        throw new Error('Không lấy được gợi ý. Kiểm tra cấu hình API.');
      }
      const data: Result = await response.json();
      onResult(data);
      setMessage(
        data.status === 'abstained'
          ? 'Chưa đủ dữ liệu quan sát lặp lại cho mốc thời gian này.'
          : 'Đã cập nhật gợi ý điểm đến thông minh từ GeoLife.'
      );
    } catch (error) {
      setMessage(
        error instanceof Error && error.message !== 'Failed to fetch'
          ? error.message
          : 'Không kết nối được API local.'
      );
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    if (BETA_MODE) { onLogout(); return; }
    setBusy(true);
    try {
      await fetch('/v2/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
    } catch {
      // The local session is still cleared if the API is unavailable.
    } finally {
      onLogout();
    }
  }

  // ==========================================
  // VIEW 1: USER LOGIN SCREEN (With 9:16 background)
  // ==========================================
  if (!token) {
    return (
      <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar relative flex flex-col justify-between text-[#202425] select-none">
        {/* Full-Height Authentic Green SM Vertical Background */}
        <div
          className="absolute inset-0 bg-cover bg-top pointer-events-none z-0"
          style={{ backgroundImage: `url(${loginBg})` }}
        />

        {/* Ambient Top & Bottom Vignette / Contrast Overlays */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#2DCCD4]/10 via-transparent to-[#0A262C]/30 pointer-events-none z-0" />

        {/* Top Header Floating Navigation */}
        <header className="relative z-10 flex items-center justify-between px-4 pt-10 pb-2">
          <button
            type="button"
            onClick={onBack}
            aria-label="Quay lại trang chủ"
            className="w-10 h-10 rounded-full bg-white/80 backdrop-blur-md border border-white/90 shadow-[0_4px_12px_rgba(0,0,0,0.06)] flex items-center justify-center text-[#1E2528] active:scale-95 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div className="w-10 h-10" />
        </header>

        {/* Main Floating Liquid Glass Form Container */}
        <main className="relative z-10 px-4 py-4 flex flex-col items-center">
          {/* Brand Welcome Slogan */}
          <div className="text-center mb-4">
            <h1 className="text-[23px] font-black tracking-tight text-[#0A2E33] leading-tight drop-shadow-xs">
              Đăng nhập tài khoản
            </h1>
            <p className="text-[12.5px] text-[#24545B] font-medium mt-1">
              Trải nghiệm gợi ý điểm đến thông minh từ GeoLife
            </p>
          </div>

          {/* Floating Frosted Glass Card */}
          <div className="w-full max-w-[360px] rounded-[28px] bg-white/85 backdrop-blur-2xl border border-white/90 p-5 shadow-[0_16px_40px_-6px_rgba(15,45,50,0.2),0_4px_12px_rgba(0,0,0,0.04)] relative overflow-hidden">
            {/* Top Specular Edge Line */}
            <div className="absolute top-0 inset-x-0 h-[1.5px] bg-gradient-to-r from-transparent via-white to-transparent" />

            <form ref={loginForm} onSubmit={login} className="space-y-3.5" autoComplete="off">
              {/* Account Input */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[12px] font-bold text-[#1E2528]" htmlFor="demo-account">
                    Mã tài khoản
                  </label>
                  <button
                    type="button"
                    onClick={() => setAccount('demo_000')}
                    className="text-[11px] font-semibold text-[#158E9A] hover:underline cursor-pointer"
                  >
                    Gợi ý: demo_000
                  </button>
                </div>
                <div className="glass-input flex h-[48px] items-center gap-3 rounded-[16px] px-3.5 focus-within:ring-2 focus-within:ring-[#2DCCD4]/40">
                  <div className="w-7 h-7 rounded-xl bg-[#E0F8FA] flex items-center justify-center shrink-0 text-[#158E9A]">
                    <UserRound className="w-4 h-4" strokeWidth={2.2} />
                  </div>
                  <input
                    id="demo-account"
                    value={account}
                    onChange={(e) => setAccount(e.target.value)}
                    required
                    maxLength={64}
                    placeholder="Nhập mã tài khoản..."
                    autoComplete="username"
                    className="min-w-0 flex-1 bg-transparent text-[13.5px] font-medium text-gray-900 placeholder:text-gray-400 outline-none"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div>
                <label className="block text-[12px] font-bold text-[#1E2528] mb-1.5" htmlFor="demo-password">
                  Mật khẩu
                </label>
                <div className="glass-input flex h-[48px] items-center gap-3 rounded-[16px] px-3.5 focus-within:ring-2 focus-within:ring-[#2DCCD4]/40">
                  <div className="w-7 h-7 rounded-xl bg-[#E0F8FA] flex items-center justify-center shrink-0 text-[#158E9A]">
                    <LockKeyhole className="w-4 h-4" strokeWidth={2.2} />
                  </div>
                  <input
                    id="demo-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="Nhập mật khẩu demo..."
                    autoComplete="off"
                    className="min-w-0 flex-1 bg-transparent text-[13.5px] font-medium text-gray-900 placeholder:text-gray-400 outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="p-1 text-gray-400 hover:text-gray-600 transition cursor-pointer"
                    aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Status / Alert Message */}
              {message && (
                <div className="flex items-center gap-2 p-2.5 rounded-xl bg-[#E8FAFB] border border-[#2DCCD4]/30 text-[11.5px] text-[#0E525C] leading-snug animate-in fade-in">
                  <AlertCircle className="w-4 h-4 text-[#158E9A] shrink-0" />
                  <span>{message}</span>
                </div>
              )}

              {/* Submit CTA */}
              <button type="submit" className="sr-only">
                Đăng nhập
              </button>
              <div className="pt-1">
                <PrismaticGlassButton
                  label={busy ? 'Đang xác thực...' : 'Đăng nhập ngay'}
                  size="full"
                  variant="turquoise"
                  disabled={busy}
                  onClick={() => loginForm.current?.requestSubmit()}
                />
              </div>
            </form>

          </div>
        </main>

        {/* Footer info note */}
        <footer className="relative z-10 px-4 pb-4 pt-2 text-center">
          <p className="text-[11px] font-medium text-white/90 drop-shadow-md">
            Demo tích hợp module với Greensm
          </p>
        </footer>
      </div>
    );
  }

  // ==========================================
  // VIEW 2: LOGGED-IN PROFILE & GEOLIFE DASHBOARD (Green SM authentic UI)
  // ==========================================
  return (
    <div className="flex-1 min-h-0 overflow-y-auto no-scrollbar bg-[#F5F8F9] text-[#1F2937] select-none flex flex-col">
      {/* 1. Hero Landscape Banner (greensm-profile-bg-1920x1080.png) */}
      <div className="relative w-full aspect-[16/9] min-h-[180px] max-h-[220px] overflow-hidden bg-[#EBF7F8]">
        <img
          src={profileBg}
          alt="Green SM Profile Banner"
          className="w-full h-full object-cover object-center"
        />
        {/* Soft bottom gradient to blend into page body */}
        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#F5F8F9] to-transparent pointer-events-none" />

        {/* Top Header Navigation on Banner */}
        <header className="absolute top-10 inset-x-0 px-4 flex items-center justify-between z-10">
          <button
            type="button"
            onClick={onBack}
            aria-label="Quay lại"
            className="w-9 h-9 rounded-full bg-white/90 backdrop-blur-md border border-white/80 shadow-[0_2px_8px_rgba(0,0,0,0.08)] flex items-center justify-center text-gray-800 active:scale-95 transition-all cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <span className="px-3.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-gray-800 text-[12px] font-bold tracking-wide border border-white/80 shadow-2xs">
            Hồ sơ cá nhân
          </span>

          <div className="w-9 h-9" />
        </header>
      </div>

      {/* 2. Main Profile Body Container */}
      <div className="px-4 -mt-10 relative z-10 space-y-3.5 pb-28 flex-1">
        {/* User Profile Card */}
        <div className="rounded-[24px] bg-white p-4 shadow-[0_10px_25px_rgba(15,35,40,0.05)] border border-gray-100">
          <div className="flex items-center gap-3.5">
            {/* Avatar */}
            <div className="relative shrink-0">
              <img
                src={defaultAvatar}
                alt={account}
                className="w-14 h-14 rounded-full object-cover"
              />
              <div className="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full bg-[#2DCCD4] border-2 border-white flex items-center justify-center text-white shadow-xs">
                <CheckCircle2 className="w-3.5 h-3.5" />
              </div>
            </div>

            {/* User Meta */}
            <div className="min-w-0 flex-1">
              <h2 className="text-[17px] font-extrabold text-gray-900 truncate tracking-tight">
                {session?.account}
              </h2>
              <p className="text-[12px] text-gray-500 font-medium mt-0.5">Tài khoản demo · Dữ liệu synthetic</p>
            </div>
          </div>
        </div>

        {/* 3. GeoLife Smart Destination Module */}
        <section className="rounded-[24px] bg-white p-4 shadow-[0_10px_25px_rgba(15,35,40,0.05)] border border-gray-100 relative overflow-hidden">
          {/* Section Header */}
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-[15.5px] font-bold text-gray-900 tracking-tight">
              Gợi ý điểm đến thông minh
            </h3>
            <span className="text-[10px] font-bold text-[#158E9A] bg-[#E0F8FA] px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              GeoLife AI
            </span>
          </div>

          <p className="text-[12px] text-gray-600 mb-3.5 leading-relaxed">
            Dự đoán điểm đến phù hợp dựa trên thói quen di chuyển cá nhân và mốc thời gian.
          </p>

          {/* Quick Context Presets */}
          <div className="mb-3">
            <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">
              Thời điểm trong ngày
            </label>
            <div className="grid grid-cols-3 gap-1.5">
              {PRESET_TIMES.map((preset) => {
                const isSelected = when === preset.time;
                return (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => {
                      onWhenChange(preset.time);
                    }}
                    className={`p-2 rounded-xl text-left transition-all cursor-pointer border ${
                      isSelected
                        ? 'bg-[#E0F8FA] border-[#2DCCD4] text-[#0A4850] shadow-xs'
                        : 'bg-gray-50 hover:bg-gray-100 border-gray-100 text-gray-700'
                    }`}
                  >
                    <div className="text-[12px] font-bold leading-tight">{preset.label}</div>
                    <div className="text-[10px] text-gray-500 truncate mt-0.5">{preset.desc}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Collapsible custom parameters */}
          <div className="mb-3.5">
            <button
              type="button"
              onClick={() => setShowCustom(!showCustom)}
              className="text-[11.5px] font-semibold text-[#158E9A] hover:underline flex items-center gap-1 cursor-pointer"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>{showCustom ? 'Thu gọn cài đặt nâng cao' : 'Tùy chỉnh thời gian & điểm xuất phát'}</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showCustom ? 'rotate-180' : ''}`} />
            </button>

            {showCustom && (
              <div className="mt-2.5 p-3 rounded-2xl bg-gray-50 border border-gray-100 space-y-2.5 animate-in fade-in">
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 mb-1" htmlFor="custom-when">
                    Thời gian dự đoán (ISO 8601):
                  </label>
                  <div className="flex items-center gap-2 rounded-xl bg-white border border-gray-200 px-3 py-2 text-[12px]">
                    <Clock3 className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                    <input
                      id="custom-when"
                      value={when}
                      onChange={(e) => onWhenChange(e.target.value)}
                      className="w-full outline-none text-gray-800 font-medium"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 mb-1" htmlFor="custom-origin">
                    Điểm xuất phát:
                  </label>
                  <div className="flex items-center gap-2 rounded-xl bg-white border border-gray-200 px-3 py-2 text-[12px]">
                    <MapPin className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                    <input
                      id="custom-origin"
                      value={origin}
                      onChange={(e) => onOriginChange(e.target.value)}
                      className="w-full outline-none text-gray-800 font-medium"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Primary CTA */}
          <PrismaticGlassButton
            label={busy ? 'Đang phân tích thói quen...' : 'Dự đoán điểm đến'}
            size="full"
            variant="turquoise"
            disabled={busy}
            onClick={() => suggest()}
          />

          {/* Suggestion Results Display inside the SAME unified card */}
          {result?.status === 'suggested' && (
            <div className="mt-4 pt-4 border-t border-gray-100 animate-in fade-in space-y-3">
              {/* Header inside Card */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-[14px] font-bold text-gray-900 tracking-tight">
                    Điểm đến gợi ý ({result.suggestions.length})
                  </h4>
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    Phù hợp nhất theo thói quen di chuyển
                  </p>
                </div>
              </div>

              {/* List of Destinations inside the single card */}
              <div className="divide-y divide-gray-100">
                {result.suggestions.map((item) => (
                  <div
                    key={item.place_ref}
                    className="py-3 first:pt-1 last:pb-1 flex items-center gap-3 transition-colors hover:bg-gray-50/80 -mx-1 px-1 rounded-xl group"
                  >
                    {/* Category Icon */}
                    <div className="w-10 h-10 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                      {getPlaceIcon(item.place_ref)}
                    </div>

                    {/* Info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[14px] font-bold text-gray-900 truncate">
                          {placeName(item.place_ref)}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded-md text-[9.5px] font-black shrink-0 ${
                            item.rank === 1
                              ? 'bg-[#E0F8FA] text-[#158E9A]'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          Top {item.rank}
                        </span>
                      </div>
                      <p className="text-[11.5px] text-gray-500 truncate mt-0.5">
                        {item.explanations.join(' • ')}
                      </p>
                    </div>

                    {/* Direct Booking CTA */}
                    <button
                      type="button"
                      onClick={() => onBookDestination?.(placeName(item.place_ref))}
                      className="px-3.5 py-1.5 rounded-xl bg-[#E0F8FA] hover:bg-[#D4F4F7] text-[#127F8B] border border-[#2DCCD4]/40 font-bold text-[12px] shrink-0 active:scale-95 transition-all shadow-2xs flex items-center gap-1 cursor-pointer"
                    >
                      <span>Đặt xe</span>
                      <ChevronRight className="w-3.5 h-3.5 text-[#127F8B]" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* 5. Standard Green SM Profile Menu Items */}
        <section className="rounded-[24px] bg-white p-2 shadow-[0_4px_20px_rgba(0,0,0,0.04)] border border-gray-100 divide-y divide-gray-50">
          <div className="p-3 flex items-center justify-between hover:bg-gray-50 rounded-xl transition cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-gray-50 text-gray-600 flex items-center justify-center">
                <MapPin className="w-4 h-4 text-[#158E9A]" />
              </div>
              <div>
                <div className="text-[13px] font-semibold text-gray-800">Địa chỉ đã lưu</div>
                <div className="text-[11px] text-gray-400">Nhà riêng, Cơ quan, Điểm đón quen</div>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400" />
          </div>

          <div className="p-3 flex items-center justify-between hover:bg-gray-50 rounded-xl transition cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-gray-50 text-gray-600 flex items-center justify-center">
                <Clock className="w-4 h-4 text-[#158E9A]" />
              </div>
              <div>
                <div className="text-[13px] font-semibold text-gray-800">Lịch sử chuyến đi</div>
                <div className="text-[11px] text-gray-400">Xem lại các cuốc xe Xanh SM</div>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400" />
          </div>

          <div className="p-3 flex items-center justify-between hover:bg-gray-50 rounded-xl transition cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-gray-50 text-gray-600 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4 text-[#158E9A]" />
              </div>
              <div>
                <div className="text-[13px] font-semibold text-gray-800">Cài đặt & Bảo mật</div>
                <div className="text-[11px] text-gray-400">Tài khoản & quyền riêng tư</div>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400" />
          </div>
        </section>

        {/* Global Feedback Alert Message */}
        {message && (
          <div className="p-3 rounded-2xl bg-[#E0F8FA] border border-[#2DCCD4]/30 text-[12px] text-[#0A3D44] flex items-start gap-2 animate-in fade-in">
            <Zap className="w-4 h-4 text-[#158E9A] shrink-0 mt-0.5" />
            <span className="leading-snug">{message}</span>
          </div>
        )}

        {/* 6. Clean Logout Action */}
        <div className="pt-2 pb-8 text-center">
          <button
            type="button"
            disabled={busy}
            onClick={logout}
            className="text-[13px] font-semibold text-red-500 hover:text-red-600 py-2.5 px-4 rounded-xl hover:bg-red-50 transition cursor-pointer inline-flex items-center gap-1.5 active:scale-95"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Đăng xuất tài khoản</span>
          </button>
        </div>
      </div>
    </div>
  );
}
