import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, setOnUnauthorized } from '../lib/api';
import { NO_SITE, type Site, type User } from '../lib/types';

interface AuthState {
  /** Il server richiede l'accesso (AUTH_ENABLED). Se no, l'app funziona come sempre, senza account. */
  enabled: boolean;
  user: User | null;
  /** Chiunque può registrarsi (ALLOW_REGISTRATION) / c'è un catalogo su cui fare la simulazione pubblica. */
  registrationOpen: boolean;
  demo: boolean;
  /** Gestore e funzioni opzionali dell'installazione (posta, pubblicità...): vale anche a login spento. */
  site: Site;
  register: (name: string, email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
}
const Ctx = createContext<AuthState | null>(null);
export const useAuth = () => { const v = useContext(Ctx); if (!v) throw new Error('useAuth fuori da AuthProvider'); return v; };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ enabled: boolean; user: User | null; registrationOpen: boolean; demo: boolean; site: Site } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, site] = await Promise.all([
        api.get<{ auth_enabled: boolean; user: User | null; registration_open?: boolean; demo?: boolean }>('/auth/session'),
        api.get<Site>('/site').catch(() => NO_SITE),  // le informazioni sul gestore non devono impedire di usare l'app
      ]);
      let user = s.user;
      if (s.auth_enabled && !user) {  // l'access token dura pochi minuti: se c'è ancora il refresh token, si rientra senza password
        try { user = (await api.post<{ user: User }>('/auth/refresh')).user; } catch { user = null; }
      }
      setState({ enabled: s.auth_enabled, user, registrationOpen: Boolean(s.registration_open), demo: Boolean(s.demo), site });  setError(null);
    } catch (e) { setError(e instanceof Error ? e.message : 'Errore'); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  // sessione scaduta o revocata mentre si usa l'app: si torna alla schermata di accesso
  useEffect(() => setOnUnauthorized(() => setState((s) => s && { ...s, user: null })), []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api.post<{ user: User }>('/auth/login', { email, password });  // i token arrivano come cookie HttpOnly
    setState((s) => s && { ...s, user: r.user });
  }, []);
  const register = useCallback(async (name: string, email: string, password: string) => {
    const r = await api.post<{ user: User }>('/auth/register', { name, email, password });
    setState((s) => s && { ...s, user: r.user });
  }, []);
  const logout = useCallback(async () => {
    try { await api.post('/auth/logout'); } catch { /* si esce comunque dall'app; al prossimo contatto il server revocherà */ }
    setState((s) => s && { ...s, user: null });
  }, []);
  const setUser = useCallback((user: User) => setState((s) => s && { ...s, user }), []);

  const value = useMemo<AuthState | null>(() => state && ({ ...state, login, register, logout, setUser }), [state, login, register, logout, setUser]);

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

/** Con il login spento l'app è a utente unico e tutto è permesso; acceso, catalogo e ipotesi su PUN/PSV sono degli amministratori. */
export const useIsAdmin = () => { const { enabled, user } = useAuth(); return !enabled || Boolean(user?.is_admin); };
