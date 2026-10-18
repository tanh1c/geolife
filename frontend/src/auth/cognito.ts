/** Cognito managed-login Authorization Code + PKCE for the invite-only beta.
 * Access tokens exist in React memory only; only transient PKCE state uses sessionStorage.
 */
export const BETA_MODE = import.meta.env.VITE_PUBLIC_BETA === '1';

type BetaSession = {account: string; token: string};
type Options = {hosted: URL; clientId: string; redirect: string; scope: string};

function options(): Options {
  const rawHost = import.meta.env.VITE_COGNITO_DOMAIN as string | undefined;
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID as string | undefined;
  const redirect = (import.meta.env.VITE_COGNITO_REDIRECT_URI as string | undefined)
    || window.location.origin + '/';
  if (!rawHost || !clientId) throw new Error('Cognito chưa được cấu hình.');
  let hosted: URL, callback: URL;
  try { hosted = new URL(rawHost); callback = new URL(redirect); }
  catch { throw new Error('Cognito callback/domain không hợp lệ.'); }
  const loopback = window.location.hostname === '127.0.0.1'
    || window.location.hostname === 'localhost';
  if (hosted.protocol !== 'https:' || hosted.username || hosted.password
      || hosted.search || hosted.hash || hosted.pathname !== '/'
      || callback.origin !== window.location.origin
      || callback.pathname !== '/' || callback.search || callback.hash
      || (!loopback && callback.protocol !== 'https:')) {
    throw new Error('Cognito phải dùng HTTPS và callback cùng origin.');
  }
  return {hosted, clientId, redirect,
    scope: (import.meta.env.VITE_COGNITO_SCOPE as string | undefined)
      || 'openid geolife-demo/read'};
}

function base64url(bytes: Uint8Array): string {
  return btoa(Array.from(bytes, b => String.fromCharCode(b)).join(''))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function randomValue(): string {
  const data = new Uint8Array(32);
  crypto.getRandomValues(data);
  return base64url(data);
}

export async function startBetaLogin(): Promise<void> {
  const cfg = options();
  const verifier = randomValue(), state = randomValue();
  const bytes = new TextEncoder().encode(verifier);
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  sessionStorage.setItem('gl_beta_oauth', JSON.stringify({
    verifier, state, expiresAt: Date.now() + 10 * 60 * 1000,
  }));
  const url = new URL('/oauth2/authorize', cfg.hosted);
  url.search = new URLSearchParams({
    response_type: 'code', client_id: cfg.clientId, redirect_uri: cfg.redirect,
    scope: cfg.scope, state, code_challenge_method: 'S256',
    code_challenge: base64url(digest),
  }).toString();
  window.location.assign(url.toString());
}

export async function completeBetaLogin(): Promise<BetaSession | null> {
  const q = new URLSearchParams(window.location.search);
  if (!q.has('code') && !q.has('error')) return null;
  // Strip code from address/history before any API/network work.
  window.history.replaceState(null, document.title, window.location.pathname);
  const raw = sessionStorage.getItem('gl_beta_oauth');
  sessionStorage.removeItem('gl_beta_oauth');
  if (q.has('error') || !raw) throw new Error('Cognito login bị từ chối hoặc phiên đã hết hạn.');
  let state: {verifier: string; state: string; expiresAt: number};
  try { state = JSON.parse(raw); }
  catch { throw new Error('Invalid PKCE state.'); }
  if (!state.verifier || !state.state || state.expiresAt < Date.now()
      || q.get('state') !== state.state || !q.get('code')) {
    throw new Error('OAuth state không hợp lệ.');
  }
  const cfg = options();
  const response = await fetch(new URL('/oauth2/token', cfg.hosted), {
    method: 'POST', cache: 'no-store',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({
      grant_type: 'authorization_code', client_id: cfg.clientId,
      redirect_uri: cfg.redirect, code: q.get('code') || '',
      code_verifier: state.verifier,
    }),
  });
  if (!response.ok) throw new Error('Cognito token exchange thất bại.');
  const tokens = await response.json();
  if (typeof tokens.access_token !== 'string' || !tokens.access_token) {
    throw new Error('Cognito access token không hợp lệ.');
  }
  const me = await fetch('/v3/beta/me', {
    headers: {Authorization: 'Bearer ' + tokens.access_token}, cache: 'no-store',
  });
  if (!me.ok) throw new Error('Tài khoản chưa được cấp quyền tester.');
  const detail = await me.json();
  if (typeof detail.app_user_id !== 'string' || detail.historical_geolife_access !== false) {
    throw new Error('Invalid API principal.');
  }
  return {account: 'Cognito tester', token: tokens.access_token};
}

export function signOutBeta(): void {
  // Token is forgotten by caller. JWT itself remains usable until expiry;
  // Cognito hosted sign-out ends the SSO browser session.
  const cfg = options();
  const url = new URL('/logout', cfg.hosted);
  url.search = new URLSearchParams({
    client_id: cfg.clientId, logout_uri: cfg.redirect,
  }).toString();
  window.location.assign(url.toString());
}
