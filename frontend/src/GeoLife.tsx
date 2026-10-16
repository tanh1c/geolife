import { useState, type FormEvent } from 'react';

type Suggestion = { rank: number; place_ref: string; explanations: string[] };
type Result = { source: 'synthetic_fixture'; status: 'suggested' | 'abstained'; suggestions: Suggestion[]; note: string };

export function GeoLife({ onBack }: { onBack: () => void }) {
  const [account, setAccount] = useState('demo_000');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [when, setWhen] = useState('2026-09-24T08:00:00+07:00');
  const [origin, setOrigin] = useState('s0_starting_point');
  const [result, setResult] = useState<Result | null>(null);
  const [message, setMessage] = useState('Chưa đăng nhập.');
  const [busy, setBusy] = useState(false);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setToken('');
    setResult(null);
    try {
      const response = await fetch('/v2/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: account.trim(), password }),
        cache: 'no-store',
      });
      setPassword('');
      if (!response.ok) throw new Error(response.status === 503 ? 'API chưa được cấu hình tài khoản demo.' : 'Đăng nhập thất bại hoặc tài khoản chưa được cấp.');
      const data: { access_token: string } = await response.json();
      setToken(data.access_token);
      setMessage('Đã đăng nhập tài khoản demo. Chỉ dùng lịch sử synthetic.');
    } catch (error) {
      setMessage(error instanceof Error && error.message !== 'Failed to fetch' ? error.message : 'Không kết nối được API local.');
    } finally {
      setPassword('');
      setBusy(false);
    }
  }

  async function suggest() {
    setBusy(true);
    setResult(null);
    const params = new URLSearchParams({ when: when.trim() });
    if (origin.trim()) params.set('origin_place_id', origin.trim());
    try {
      const response = await fetch(`/v2/me/destination-suggestions?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (response.status === 401) {
        setToken('');
        throw new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
      }
      if (!response.ok) throw new Error('Không lấy được gợi ý. Kiểm tra thời gian có múi giờ và cấu hình synthetic.');
      const data: Result = await response.json();
      setResult(data);
      setMessage(data.status === 'abstained' ? 'Chưa đủ dữ liệu để gợi ý.' : 'Gợi ý từ lịch sử synthetic, không phải GPS thật.');
    } catch (error) {
      setMessage(error instanceof Error && error.message !== 'Failed to fetch' ? error.message : 'Không kết nối được API local.');
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    const bearer = token;
    setToken('');
    setResult(null);
    setBusy(true);
    try {
      const response = await fetch('/v2/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${bearer}` },
        cache: 'no-store',
      });
      setMessage(response.ok ? 'Đã đăng xuất.' : 'Đã xóa phiên trong trang; máy chủ chưa xác nhận thu hồi token.');
    } catch {
      setMessage('Đã xóa phiên trong trang; không kết nối được máy chủ để thu hồi token.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto bg-[#F5F9F9] p-5 pb-12 text-[#1E2528]">
      <button type="button" disabled={busy} onClick={async () => { if (token) await logout(); onBack(); }} className="text-sm font-semibold text-[#158E9A] disabled:opacity-50">← Trang chủ</button>
      <h1 className="mt-6 text-2xl font-bold">GeoLife · Gợi ý điểm đến</h1>
      <p className="mt-2 text-sm text-gray-600">Top-3 từ dữ liệu giả lập theo tài khoản demo. Không dùng vị trí thật, không phải dự đoán HOME/OFFICE hay đặt xe.</p>

      <section className="mt-6 rounded-2xl bg-white p-4 shadow-sm" aria-label="Tài khoản demo">
        <h2 className="font-semibold">Tài khoản demo</h2>
        {token ? (
          <div className="mt-3 flex items-center justify-between gap-3 text-sm">
            <span>Đã đăng nhập: {account}</span>
            <button type="button" disabled={busy} onClick={logout} className="font-semibold text-[#158E9A] disabled:opacity-50">Đăng xuất</button>
          </div>
        ) : (
          <form onSubmit={login} className="mt-3 space-y-3" autoComplete="off">
            <label className="block text-sm">Demo account ID
              <input value={account} onChange={(event) => setAccount(event.target.value)} required maxLength={64} autoComplete="username" className="mt-1 w-full rounded-xl border border-gray-300 p-2" />
            </label>
            <label className="block text-sm">Mật khẩu demo
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="off" className="mt-1 w-full rounded-xl border border-gray-300 p-2" />
            </label>
            <button disabled={busy} className="w-full rounded-xl bg-[#158E9A] p-2.5 font-semibold text-white disabled:opacity-50">Đăng nhập</button>
          </form>
        )}
        <p className="mt-3 text-xs text-gray-500">Token chỉ giữ trong bộ nhớ trang; tải lại trang sẽ cần đăng nhập lại.</p>
      </section>

      <section className="mt-4 rounded-2xl bg-white p-4 shadow-sm" aria-label="Ngữ cảnh gợi ý">
        <h2 className="font-semibold">Ngữ cảnh dự đoán</h2>
        <label className="mt-3 block text-sm">Thời điểm ISO có múi giờ
          <input value={when} onChange={(event) => setWhen(event.target.value)} maxLength={48} className="mt-1 w-full rounded-xl border border-gray-300 p-2" />
        </label>
        <label className="mt-3 block text-sm">Mã điểm xuất phát synthetic (tùy chọn)
          <input value={origin} onChange={(event) => setOrigin(event.target.value)} maxLength={64} className="mt-1 w-full rounded-xl border border-gray-300 p-2" />
        </label>
        <button type="button" disabled={!token || busy} onClick={suggest} className="mt-4 w-full rounded-xl bg-[#158E9A] p-2.5 font-semibold text-white disabled:opacity-50">Xem Top-3 gợi ý</button>
      </section>

      <p role="status" aria-live="polite" className="mt-4 rounded-xl bg-[#E0F8FA] p-3 text-sm">{busy ? 'Đang xử lý…' : message}</p>
      <section className="mt-4 rounded-2xl bg-white p-4 shadow-sm" aria-label="Kết quả gợi ý">
        <h2 className="font-semibold">Kết quả synthetic</h2>
        {result?.status === 'suggested' ? (
          <ol className="mt-2 divide-y divide-gray-100">
            {result.suggestions.map((item) => (
              <li key={item.place_ref} className="py-3">
                <span className="text-xs font-semibold text-[#158E9A]">TOP {item.rank}</span>
                <strong className="block">{item.place_ref}</strong>
                <span className="text-sm text-gray-600">{item.explanations.join(' · ')}</span>
              </li>
            ))}
          </ol>
        ) : <p className="mt-2 text-sm text-gray-600">{result ? 'Chưa đủ lịch sử quan sát lặp lại.' : 'Chưa có kết quả.'}</p>}
        <p className="mt-3 text-xs text-gray-500">Thứ hạng không phải độ tin cậy, Evidence Score hay tọa độ trên bản đồ.</p>
      </section>
    </div>
  );
}
