import type { Message } from './types';

/** Errore di un'chiamata a /api: `status` HTTP e messaggio già leggibile in italiano. */
export class ApiError extends Error {
  constructor(message: string, public status: number, public data?: any) { super(message); }
}

// --- login (opzionale: AUTH_ENABLED sul server) -------------------------------------------------
// Il token sta in localStorage (in un'app nativa basterà sostituire queste tre funzioni con lo storage sicuro del sistema).
// Se il server ha il login spento il token non esiste e non viene mandato nulla.
const TOKEN_KEY = 'bollette.token';
export const getToken = (): string | null => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
export const setToken = (token: string | null) => {
  try { if (token) localStorage.setItem(TOKEN_KEY, token); else localStorage.removeItem(TOKEN_KEY); } catch { /* storage non disponibile */ }
};
let authHeaders = (): Record<string, string> => { const t = getToken(); return t ? { Authorization: `Bearer ${t}` } : {}; };
let onUnauthorized: () => void = () => {};
export const setAuthHeaders = (fn: () => Record<string, string>) => { authHeaders = fn; };
/** Chiamata quando una richiesta riceve 401 (token scaduto o revocato): l'app torna alla schermata di accesso. */
export const setOnUnauthorized = (fn: () => void) => { onUnauthorized = fn; };

// --- profilo attivo: lo manda ogni richiesta (i cookie non sono affidabili in un'app nativa) -----
const PROFILE_KEY = 'bollette.profile';
export const getProfileId = (): number | null => {
  try { return Number(localStorage.getItem(PROFILE_KEY)) || null; } catch { return null; }
};
export const setProfileId = (id: number) => { try { localStorage.setItem(PROFILE_KEY, String(id)); } catch { /* storage non disponibile */ } };

function headers(extra: Record<string, string> = {}): Record<string, string> {
  const profile = getProfileId();
  return { ...(profile ? { 'X-Profile-Id': String(profile) } : {}), ...authHeaders(), ...extra };
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isForm = body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: headers(body && !isForm ? { 'Content-Type': 'application/json' } : {}),
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Server non raggiungibile: controlla la connessione.', 0);
  }
  const data = await res.json().catch(() => null);
  if (res.status === 401 && path !== '/auth/login') onUnauthorized();
  if (!res.ok) throw new ApiError(data?.error ?? `Errore ${res.status}`, res.status, data);
  return data as T;
}

export const api = {
  get: <T>(path: string, params?: Record<string, string | number | undefined>) => {
    const q = params ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => [k, String(v)])) : '';
    return request<T>('GET', path + (q === '?' ? '' : q));
  },
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body ?? {}),
  del: <T>(path: string) => request<T>('DELETE', path),
};

/** Apre un PDF protetto (richiede header): lo scarica come blob e lo mostra in una scheda. */
export async function openPdf(path: string): Promise<void> {
  const res = await fetch(`/api${path}`, { headers: headers() });
  if (!res.ok) throw new ApiError('PDF non disponibile.', res.status);
  const url = URL.createObjectURL(await res.blob());
  window.open(url, '_blank', 'noopener');
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export const fetchPdfData = async (path: string): Promise<ArrayBuffer> => {
  const res = await fetch(`/api${path}`, { headers: headers() });
  if (!res.ok) throw new ApiError('PDF non disponibile.', res.status);
  return res.arrayBuffer();
};

export type WithMessages<T = object> = T & { messages?: Message[] };
