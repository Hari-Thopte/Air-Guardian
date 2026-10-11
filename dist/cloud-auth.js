import {config} from './cloud-config.js';
import {resilientFetch} from './assets/resilient-fetch.js';

let accessToken = '', refreshToken = '', expiresAt = 0;
export const configured = () => Boolean(config.apiUrl && config.clientId && config.authDomain && config.redirectUri);
const base64url = bytes => btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
const random = () => base64url(crypto.getRandomValues(new Uint8Array(32)));
const redirectUri = () => config.redirectUri;

async function tokenRequest(values) {
  const response = await fetch(config.authDomain + '/oauth2/token', {
    method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({client_id:config.clientId,...values}), signal:AbortSignal.timeout(20000)
  });
  if (!response.ok) throw new Error('Your sign-in session could not be refreshed. Sign in again.');
  const data = await response.json();
  if (!data.access_token || !Number.isFinite(data.expires_in)) throw new Error('Invalid sign-in response.');
  accessToken = data.access_token;
  refreshToken = data.refresh_token || refreshToken;
  expiresAt = Date.now() + data.expires_in * 1000;
}

export async function login() {
  if (!configured()) throw new Error('Cloud deployment settings have not been configured.');
  const verifier = random(), state = random();
  const challenge = base64url(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
  sessionStorage.setItem('airguardian.pkce', JSON.stringify({verifier,state,createdAt:Date.now()}));
  const params = new URLSearchParams({client_id:config.clientId, response_type:'code', redirect_uri:redirectUri(),
    scope:'openid email aws.cognito.signin.user.admin', state, code_challenge:challenge, code_challenge_method:'S256'});
  location.assign(config.authDomain + '/oauth2/authorize?' + params);
}

export async function completeLogin() {
  const params = new URLSearchParams(location.search);
  if (!params.has('code') && !params.has('error')) return false;
  const saved = sessionStorage.getItem('airguardian.pkce');
  sessionStorage.removeItem('airguardian.pkce');
  history.replaceState(null,'',location.pathname);
  if (params.has('error')) throw new Error('Sign-in was cancelled or rejected. Please retry.');
  let expected;
  try { expected = JSON.parse(saved); } catch { /* handled below */ }
  if (!expected || params.get('state') !== expected.state || Date.now() - expected.createdAt > 600000)
    throw new Error('Sign-in expired or did not match this browser. Please retry.');
  await tokenRequest({grant_type:'authorization_code', code:params.get('code'), redirect_uri:redirectUri(), code_verifier:expected.verifier});
  return true;
}

export async function logout() {
  const token = refreshToken;
  accessToken = ''; refreshToken = ''; expiresAt = 0;
  if (token) {
    try { await fetch(config.authDomain + '/oauth2/revoke', {method:'POST',
      headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({token,client_id:config.clientId}), signal:AbortSignal.timeout(5000)}); } catch { /* membership checks remain server-side */ }
  }
  location.assign(config.authDomain + '/logout?' + new URLSearchParams({client_id:config.clientId,logout_uri:redirectUri()}));
}

export async function api(path, {method='GET',body}={}) {
  if (refreshToken && Date.now() > expiresAt - 30000) await tokenRequest({grant_type:'refresh_token',refresh_token:refreshToken});
  if (!accessToken) throw new Error('Sign in to open the school workspace.');
  const response = await resilientFetch(config.apiUrl + path, {method, headers:{Authorization:'Bearer '+accessToken,'Content-Type':'application/json'},
    ...(body === undefined ? {} : {body:JSON.stringify(body)}), cache:'no-store', signal:AbortSignal.timeout(25000)});
  let result;
  try { result = await response.json(); } catch { throw new Error('The school service is unavailable. Please retry.'); }
  if (!response.ok) {const error=new Error(result.message || 'The request could not be completed.');error.status=response.status;throw error;}
  return result;
}

export const preview = false;
