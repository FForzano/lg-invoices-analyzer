import type { ReactNode } from 'react';
import { useAuth } from '../context/AuthContext';
import PublicRoutes from '../pages/public/PublicRoutes';
import ChangePassword from '../pages/ChangePassword';

/** Con il login attivo mostra le pagine pubbliche (landing e accesso) finché non c'è una sessione, e il cambio password se è provvisoria.
 *  Con il login spento (predefinito) lascia passare tutto. Il backend controlla comunque ogni richiesta (`authenticate()`). */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const { enabled, user } = useAuth();
  if (!enabled) return <>{children}</>;
  if (!user) return <PublicRoutes />;  // landing, simulazione, accesso e registrazione
  if (user.must_change_password) return <ChangePassword forced />;
  return <>{children}</>;
}
