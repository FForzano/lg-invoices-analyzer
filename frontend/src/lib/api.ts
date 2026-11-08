import type { Message } from './types';

/** Errore di un'chiamata a /api: `status` HTTP e messaggio già leggibile in italiano. */
export class ApiError extends Error {
  constructor(message: string, public status: number, public data?: any) { super(message); }
}

// --- punti di estensione per il login (futuro) -----------------------------------------------
// Oggi l'app non ha login: nessun header di autenticazione e nessuna gestione speciale del 401.
// Quando servirà: `setAuthHeaders(() => ({ Authorization: `Bearer ${token}` }))` dopo l'accesso e
// `setOnUnauthorized(() => navigate('/login'))`; il resto del front-end non cambia.
let authHeaders: () => Record<string, string> = () => ({});
let onUnauthorized: () => void = () => {};
export const setAuthHeaders = (fn: () => Record<string, string>) => { authHeaders = fn; };
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
  if (res.status === 401) onUnauthorized();
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
