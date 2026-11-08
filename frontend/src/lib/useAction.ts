import { useCallback, useState } from 'react';
import { ApiError } from './api';
import { useApp } from '../context/AppContext';

/** Esegue una chiamata che modifica dati: tiene `busy` e trasforma gli errori in un avviso. */
export function useAction() {
  const { flash } = useApp();
  const [busy, setBusy] = useState(false);
  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    try { return await fn(); }
    catch (e) { flash({ level: 'warn', text: e instanceof ApiError ? e.message : String(e) }); window.scrollTo({ top: 0 }); return undefined; }
    finally { setBusy(false); }
  }, [flash]);
  return { run, busy };
}
