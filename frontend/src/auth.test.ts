import { afterEach, beforeEach, expect, it, vi } from 'vitest';

const stored = new Map<string, string>();
const assigned = vi.fn();
const replaced = vi.fn();

beforeEach(() => {
  vi.stubGlobal('window', {
    location: { href: 'https://dxyhw0cktlmvt.cloudfront.net/', assign: assigned },
    history: { replaceState: replaced },
  });
  vi.stubGlobal('document', { title: 'GeoLife' });
  vi.stubGlobal('sessionStorage', {
    setItem: (key: string, value: string) => stored.set(key, value),
    getItem: (key: string) => stored.get(key) ?? null,
    removeItem: (key: string) => stored.delete(key),
  });
  vi.stubGlobal('crypto', globalThis.crypto);
});

afterEach(() => {
  stored.clear();
  assigned.mockClear();
  replaced.mockClear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it('starts authorization with S256 PKCE, registered scope and transient state', async () => {
  const { beginLogin, createPkceChallenge } = await import('./auth');
  await beginLogin();
  const url = new URL(assigned.mock.calls[0][0]);
  expect(url.searchParams.get('scope')).toBe('openid geolife-demo/read');
  expect(url.searchParams.get('response_type')).toBe('code');
  expect(url.searchParams.get('code_challenge_method')).toBe('S256');
  expect(url.searchParams.get('code_challenge')).toBe(await createPkceChallenge(stored.get('geolife.pkce.verifier')!));
  expect(url.searchParams.get('state')).toBe(stored.get('geolife.pkce.state'));
  expect(url.searchParams.get('nonce')).toBe(stored.get('geolife.pkce.nonce'));
});

it('rejects forged state before token exchange and clears PKCE material', async () => {
  const { beginLogin, finishLogin } = await import('./auth');
  await beginLogin();
  const fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  await expect(finishLogin(new URL('https://dxyhw0cktlmvt.cloudfront.net/?code=code&state=forged'))).rejects.toThrow();
  expect(fetchMock).not.toHaveBeenCalled();
  expect(stored.size).toBe(0);
  expect(replaced).toHaveBeenCalled();
});

it('rejects an identity token for another app client', async () => {
  const { beginLogin, finishLogin } = await import('./auth');
  await beginLogin();
  const state = stored.get('geolife.pkce.state');
  const payload = btoa(JSON.stringify({
    iss: 'https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_82m9sJb9P',
    sub: 'subject-a', nonce: stored.get('geolife.pkce.nonce'), aud: 'another-client',
    token_use: 'id', exp: Date.now() / 1000 + 300,
  }));
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ id_token: `a.${payload}.b`, access_token: 'token', expires_in: 60 }),
  }));
  await expect(finishLogin(new URL(`https://dxyhw0cktlmvt.cloudfront.net/?code=code&state=${state}`))).rejects.toThrow();
});

it('exchanges a valid callback once, handles cancellation and checks expiry', async () => {
  const { beginLogin, finishLogin, isSessionValid, logout } = await import('./auth');
  await beginLogin();
  const state = stored.get('geolife.pkce.state');
  const nonce = stored.get('geolife.pkce.nonce');
  const payload = btoa(JSON.stringify({ iss: 'https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_82m9sJb9P', sub: 'subject-a', nonce, aud: '6g3nfj725fmfo56uc87f4a1e5l', token_use: 'id', exp: Date.now() / 1000 + 300 }));
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id_token: `a.${payload}.b`, access_token: 'token', expires_in: 60 }) });
  vi.stubGlobal('fetch', fetchMock);
  const session = await finishLogin(new URL(`https://dxyhw0cktlmvt.cloudfront.net/?code=code&state=${state}`));
  expect(session?.account).toBe('subject-a');
  expect(session?.accessToken).toBe('token');
  expect(isSessionValid(session)).toBe(true);
  expect(isSessionValid({ ...session!, expiresAt: 0 })).toBe(false);
  expect(stored.size).toBe(0);
  expect(fetchMock).toHaveBeenCalledOnce();
  await expect(finishLogin(new URL('https://dxyhw0cktlmvt.cloudfront.net/?error=access_denied'))).rejects.toThrow();
  await beginLogin();
  expect(stored.size).toBe(3);
  logout();
  expect(stored.size).toBe(0);
  const target = new URL(assigned.mock.calls.at(-1)![0]);
  expect(target.pathname).toBe('/logout');
  expect(target.searchParams.get('logout_uri')).toBe('https://dxyhw0cktlmvt.cloudfront.net/');
});
