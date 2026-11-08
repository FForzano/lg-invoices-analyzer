import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Login from '../Login';
import Landing from './Landing';
import Register from './Register';
import Simulate from './Simulate';

/** Ciò che vede chi non ha una sessione (solo con il login attivo). Ogni altro indirizzo porta all'accesso. */
export default function PublicRoutes() {
  const { demo } = useAuth();
  return (
    <Routes>
      <Route index element={<Landing />} />
      <Route path="accedi" element={<Login />} />
      <Route path="registrati" element={<Register />} />
      <Route path="simulazione" element={demo ? <Simulate /> : <Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/accedi" replace />} />
    </Routes>
  );
}
