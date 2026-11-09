import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Login from '../Login';
import Landing from './Landing';
import Register from './Register';
import Simulate from './Simulate';
import ForgotPassword from '../ForgotPassword';
import ResetPassword from '../ResetPassword';
import PublicShell from '../../components/public/PublicShell';
import Terms from '../legal/Terms';
import Privacy from '../legal/Privacy';

/** Ciò che vede chi non ha una sessione (solo con il login attivo). Ogni altro indirizzo porta all'accesso. */
export default function PublicRoutes() {
  const { demo } = useAuth();
  return (
    <Routes>
      <Route index element={<Landing />} />
      <Route path="accedi" element={<Login />} />
      <Route path="registrati" element={<Register />} />
      <Route path="password-dimenticata" element={<ForgotPassword />} />
      <Route path="reimposta-password" element={<ResetPassword />} />
      <Route path="termini" element={<PublicShell title="Termini d'uso"><main className="mx-auto max-w-[44rem] px-4 pb-16 pt-4"><Terms /></main></PublicShell>} />
      <Route path="privacy" element={<PublicShell title="Privacy e cookie"><main className="mx-auto max-w-[44rem] px-4 pb-16 pt-4"><Privacy /></main></PublicShell>} />
      <Route path="simulazione" element={demo ? <Simulate /> : <Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/accedi" replace />} />
    </Routes>
  );
}
