import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, setOnUnauthorized, setToken, type WithMessages } from '../lib/api';
import type { User } from '../lib/types';

interface AuthState {
  /** Il server richiede l'accesso (AUTH_ENABLED). Se no, l'app funziona come sempre, senza account. */
  enabled: boolean;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
}
const Ctx = createContext<AuthState | null>(null);
export const useAuth = () => { const v = useContext(Ctx); if (!v) throw new Error('useAuth fuori da AuthProvider'); return v; };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ enabled: boolean; user: User | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await api.get<{ auth_enabled: boolean; user: User | null }>('/auth/session');
      if (!s.user) setToken(null);
      setState({ enabled: s.auth_enabled, user: s.user }); setError(null);
    } catch (e) { setError(e instanceof Error ? e.message : 'Errore'); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  // token scaduto o revocato mentre si usa l'app: si torna alla schermata di accesso
  useEffect(() => setOnUnauthorized(() => { setToken(null); setState((s) => s && { ...s, user: null }); }), []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api.post<{ token: string; user: User }>('/auth/login', { email, password });
    setToken(r.token);
    setState((s) => s && { ...s, user: r.user });
  }, []);
  const logout = useCallback(async () => {
    try { await api.post('/auth/logout'); } catch { /* il token va tolto comunque */ }
    setToken(null);
    setState((s) => s && { ...s, user: null });
  }, []);
  const setUser = useCallback((user: User) => setState((s) => s && { ...s, user }), []);

  const value = useMemo<AuthState | null>(() => state && ({ ...state, login, logout, setUser }), [state, login, logout, setUser]);

  if (error && !state) return (
    <div className="mx-auto mt-24 max-w-md rounded-card bg-surface p-8 text-center shadow-panel">
      <h1 className="text-xl font-extrabold text-accent-deep">Non riesco a contattare il server</h1>
      <p className="mt-2 text-muted">{error}</p>
      <button className="mt-4 rounded-field bg-accent px-6 py-3 font-bold text-on-accent" onClick={() => void load()}>Riprova</button>
    </div>
  );
  if (!value) return <div className="grid min-h-screen place-items-center text-muted" role="status">Caricamento…</div>;
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export type { WithMessages };
