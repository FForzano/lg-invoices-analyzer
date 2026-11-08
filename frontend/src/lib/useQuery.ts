import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from './api';
import { useProfileId } from '../context/AppContext';

/** GET con stato di caricamento; si rilegge se cambiano percorso, parametri o profilo attivo. */
export function useQuery<T>(path: string | null, params?: Record<string, string | number | undefined>) {
  const profileId = useProfileId();
  const key = JSON.stringify([path, params, profileId]);
  const [state, setState] = useState<{ data: T | null; error: ApiError | null; loading: boolean }>({ data: null, error: null, loading: path !== null });
  const seq = useRef(0);
  const load = useCallback(async () => {
    if (path === null) return;
    const mine = ++seq.current;
    setState((s) => ({ ...s, loading: true }));
    try {
      const data = await api.get<T>(path, params);
      if (mine === seq.current) setState({ data, error: null, loading: false });
    } catch (e) {
      if (mine === seq.current) setState({ data: null, error: e instanceof ApiError ? e : new ApiError(String(e), 0), loading: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  useEffect(() => { void load(); }, [load]);
  return { ...state, reload: load };
}
