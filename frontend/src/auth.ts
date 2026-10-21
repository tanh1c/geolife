const region = import.meta.env.VITE_COGNITO_REGION || 'ap-southeast-1';
const poolId = import.meta.env.VITE_COGNITO_POOL_ID || 'ap-southeast-1_82m9sJb9P';
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || '6g3nfj725fmfo56uc87f4a1e5l';
const domain = import.meta.env.VITE_COGNITO_DOMAIN || 'geolife-mentor-beta-939169265033.auth.ap-southeast-1.amazoncognito.com';
export const issuer = `https://cognito-idp.${region}.amazonaws.com/${poolId}`;
export const callbackUrl = import.meta.env.VITE_COGNITO_CALLBACK_URL || 'https://dxyhw0cktlmvt.cloudfront.net/';
export const logoutUrl = import.meta.env.VITE_COGNITO_LOGOUT_URL || callbackUrl;
export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
export const hostedLoginUrl = `https://${domain}`;

const verifierKey = 'geolife.pkce.verifier';
const stateKey = 'geolife.pkce.state';
const nonceKey = 'geolife.pkce.nonce';

export type AuthSession = {
  account: string;
  accessToken: string;
  expiresAt: number;
};

function base64Url(bytes: Uint8Array) {
  let binary = '';
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export async function createPkceChallenge(verifier: string) {
  return base64Url(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
}

function randomToken(size = 32) {
  return base64Url(crypto.getRandomValues(new Uint8Array(size)));
}

export function createLoginUrl(verifier: string, state: string, nonce: string) {
  const url = new URL('/oauth2/authorize', hostedLoginUrl);
  url.search = new URLSearchParams({
    client_id: clientId,
    response_type: 'code',
    scope: 'openid geolife-demo/read',
    redirect_uri: callbackUrl,
    code_challenge_method: 'S256',
    code_challenge: verifier,
    state,
    nonce,
  }).toString();
  return url;
}

export async function beginLogin(): Promise<void> {
  const verifier = randomToken(64);
  const state = randomToken();
  const nonce = randomToken();
  sessionStorage.setItem(verifierKey, verifier);
  sessionStorage.setItem(stateKey, state);
  sessionStorage.setItem(nonceKey, nonce);
  const challenge = await createPkceChallenge(verifier);
  window.location.assign(createLoginUrl(challenge, state, nonce));
}

export function decodePayload(token: string): Record<string, unknown> {
  const payload = token.split('.')[1];
  if (!payload) throw new Error('Invalid identity token');
  const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
  return JSON.parse(atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')));
}

export async function finishLogin(url = new URL(window.location.href)): Promise<AuthSession | null> {
  const code = url.searchParams.get('code');
  if (url.searchParams.has('error')) {
    sessionStorage.removeItem(verifierKey);
    sessionStorage.removeItem(stateKey);
    sessionStorage.removeItem(nonceKey);
    window.history.replaceState({}, document.title, url.pathname);
    throw new Error('Sign-in was cancelled or could not be verified. Please try again.');
  }
  if (!code) return null;
  const returnedState = url.searchParams.get('state');
  const verifier = sessionStorage.getItem(verifierKey);
  const expectedState = sessionStorage.getItem(stateKey);
  const expectedNonce = sessionStorage.getItem(nonceKey);
  sessionStorage.removeItem(verifierKey);
  sessionStorage.removeItem(stateKey);
  sessionStorage.removeItem(nonceKey);
  window.history.replaceState({}, document.title, url.pathname);
  if (!verifier || !expectedState || returnedState !== expectedState || !expectedNonce) {
    throw new Error('Sign-in was cancelled or could not be verified. Please try again.');
  }
  const response = await fetch(`${hostedLoginUrl}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: clientId,
      code,
      redirect_uri: callbackUrl,
      code_verifier: verifier,
    }),
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Sign-in failed. Please try again.');
  const tokens: { access_token: string; id_token: string; expires_in: number } = await response.json();
  const claims = decodePayload(tokens.id_token);
  if (claims.iss !== issuer || claims.aud !== clientId || claims.token_use !== 'id' ||
      claims.nonce !== expectedNonce || typeof claims.sub !== 'string' || !claims.sub ||
      typeof claims.exp !== 'number' || claims.exp <= Date.now() / 1000 ||
      typeof tokens.access_token !== 'string' || !tokens.access_token ||
      !Number.isFinite(tokens.expires_in) || tokens.expires_in <= 0) {
    throw new Error('Sign-in response is invalid or expired. Please try again.');
  }
  return { account: claims.sub, accessToken: tokens.access_token, expiresAt: Math.min(claims.exp, Date.now() / 1000 + tokens.expires_in) };
}

export function isSessionValid(session: AuthSession | null) {
  return !!session && session.expiresAt > Date.now() / 1000;
}

export function logout() {
  sessionStorage.removeItem(verifierKey);
  sessionStorage.removeItem(stateKey);
  sessionStorage.removeItem(nonceKey);
  const url = new URL('/logout', hostedLoginUrl);
  url.search = new URLSearchParams({ client_id: clientId, logout_uri: logoutUrl }).toString();
  window.location.assign(url);
}
