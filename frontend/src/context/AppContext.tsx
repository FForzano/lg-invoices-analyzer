import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api, setProfileId } from '../lib/api';
import type { Message, Profile } from '../lib/types';

interface Bootstrap { profiles: Profile[]; profile: Profile; help: Record<string, string>; can_extract: boolean }
interface AppState {
  profiles: Profile[]; profile: Profile; help: Record<string, string>; canExtract: boolean;
  messages: Message[]; clearStale: () => void; flash: (m?: Message[] | Message | string) => void; dismiss: (i: number) => void;
  refresh: () => Promise<void>; switchProfile: (id: number) => Promise<void>;
}
const Ctx = createContext<AppState | null>(null);
export const useApp = () => { const v = useContext(Ctx); if (!v) throw new Error('useApp fuori da AppProvider'); return v; };

export function AppProvider({ children }: { children: ReactNode }) {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const stamp = useRef(0);

  const refresh = useCallback(async () => {
    try {
      const b = await api.get<Bootstrap>('/bootstrap');
      setProfileId(b.profile.id);  // se il profilo salvato non esiste più, il server ha scelto il primo
      setBoot(b); setError(null);
    } catch (e) { setError(e instanceof Error ? e.message : 'Errore'); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const flash = useCallback((m?: Message[] | Message | string) => {
    if (!m) return;
    const list: Message[] = typeof m === 'string' ? [{ level: 'info', text: m }] : Array.isArray(m) ? m : [m];
    stamp.current = Date.now();
    setMessages(list);
  }, []);
  const clearStale = useCallback(() => {
    if (Date.now() - stamp.current > 1500) setMessages((m) => (m.length ? [] : m));  // stesso array = nessun nuovo rendering
  }, []);
  const switchProfile = useCallback(async (id: number) => { setProfileId(id); await refresh(); }, [refresh]);

  const value = useMemo<AppState | null>(() => boot && ({
    profiles: boot.profiles, profile: boot.profile, help: boot.help, canExtract: boot.can_extract,
    messages, flash, refresh, switchProfile,
    dismiss: (i: number) => setMessages((l) => l.filter((_, j) => j !== i)),
    clearStale,
  }), [boot, messages, flash, clearStale, refresh, switchProfile]);

  if (error && !boot) return (
    <div className="mx-auto mt-24 max-w-md rounded-card bg-surface p-8 text-center shadow-panel">
      <h1 className="text-xl font-extrabold text-accent-deep">Non riesco a contattare il server</h1>
      <p className="mt-2 text-muted">{error}</p>
      <button className="mt-4 rounded-field bg-accent px-6 py-3 font-bold text-on-accent" onClick={() => void refresh()}>Riprova</button>
    </div>
  );
  if (!value) return <div className="grid min-h-screen place-items-center text-muted" role="status">Caricamento…</div>;
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/** Un'ultima parola sul profilo: serve alle pagine per ricaricare i dati quando cambia. */
export const useProfileId = () => useApp().profile.id;
