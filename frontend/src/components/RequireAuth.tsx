import type { ReactNode } from 'react';
import { useAuth } from '../context/AuthContext';
import Login from '../pages/Login';
import ChangePassword from '../pages/ChangePassword';

/** Con il login attivo mostra l'accesso finché non c'è una sessione, e il cambio password se è provvisoria.
 *  Con il login spento (predefinito) lascia passare tutto. Il backend controlla comunque ogni richiesta (`authenticate()`). */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const { enabled, user } = useAuth();
  if (!enabled) return <>{children}</>;
  if (!user) return <Login />;
  if (user.must_change_password) return <ChangePassword forced />;
  return <>{children}</>;
}
