import type { ReactNode } from 'react';

/** Guscio per il login futuro: oggi lascia passare tutto (l'app è pensata per la rete di casa).
 *  Quando arriverà il login: se manca la sessione, `return <Navigate to="/login" replace />`;
 *  le richieste porteranno il token con `setAuthHeaders` (lib/api.ts) e il backend lo verificherà in `authenticate()`. */
export default function RequireAuth({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
