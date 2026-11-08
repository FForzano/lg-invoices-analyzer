import type { Message } from './types';

/** Errore di un'chiamata a /api: `status` HTTP e messaggio già leggibile in italiano. */
export class ApiError extends Error {
  constructor(message: string, public status: number, public data?: any) { super(message); }
}

// --- login (opzionale: AUTH_ENABLED sul server) -------------------------------------------------
// La sessione sta in cookie HttpOnly (access JWT breve + refresh a rotazione): JavaScript non li vede né li conserva,
// il browser li manda da solo. Qui si fa solo il resto: l'header anti-CSRF e il rinnovo trasparente quando l'access scade.
let onUnauthorized: () => void = () => {};
/** Chiamata quando la sessione non è più rinnovabile (scaduta o revocata): l'app torna alla schermata di accesso. */
export const setOnUnauthorized = (fn: () => void) => { onUnauthorized = fn; };

// --- profilo attivo: lo manda ogni richiesta ------------------------------------------------------
const PROFILE_KEY = 'bollette.profile';
export const getProfileId = (): number | null => {
  try { return Number(localStorage.getItem(PROFILE_KEY)) || null; } catch { return null; }
};
export const setProfileId = (id: number) => { try { localStorage.setItem(PROFILE_KEY, String(id)); } catch { /* storage non disponibile */ } };

function headers(extra: Record<string, string> = {}): Record<string, string> {
  const profile = getProfileId();
  // X-Requested-With: un altro sito non può aggiungerlo alle sue richieste, quindi il server lo pretende per quelle che modificano
  return { 'X-Requested-With': 'bollette', ...(profile ? { 'X-Profile-Id': String(profile) } : {}), ...extra };
}

let refreshing: Promise<boolean> | null = null;
/** Rinnova la sessione. Una sola richiesta alla volta: con più chiamate in volo che scadono insieme, il refresh token
 *  (a rotazione, valido una volta) verrebbe usato più volte e il server lo scambierebbe per un furto. */
function refreshSession(): Promise<boolean> {
  refreshing ??= fetch('/api/auth/refresh', { method: 'POST', headers: headers() })
    .then((r) => r.ok).catch(() => false).finally(() => { refreshing = null; });
  return refreshing;
}

const NO_RETRY = ['/auth/login', '/auth/refresh', '/auth/session', '/auth/logout'];

/** fetch su /api: se risponde 401 prova a rinnovare la sessione e ripete la richiesta una volta. */
async function send(method: string, path: string, body?: unknown): Promise<Response> {
  const isForm = body instanceof FormData;
  const go = () => fetch(`/api${path}`, {
    method,
    headers: headers(body && !isForm ? { 'Content-Type': 'application/json' } : {}),
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  });
  const attempt = async () => { try { return await go(); } catch { throw new ApiError('Server non raggiungibile: controlla la connessione.', 0); } };
  let res = await attempt();
  if (res.status === 401 && !NO_RETRY.includes(path)) {
    if (await refreshSession()) res = await attempt();
    if (res.status === 401) onUnauthorized();
  }
  return res;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await send(method, path, body);
  const data = await res.json().catch(() => null);
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
  const res = await send('GET', path);
  if (!res.ok) throw new ApiError('PDF non disponibile.', res.status);
  const url = URL.createObjectURL(await res.blob());
  window.open(url, '_blank', 'noopener');
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export const fetchPdfData = async (path: string): Promise<ArrayBuffer> => {
  const res = await send('GET', path);
  if (!res.ok) throw new ApiError('PDF non disponibile.', res.status);
  return res.arrayBuffer();
};

export type WithMessages<T = object> = T & { messages?: Message[] };
