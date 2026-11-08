import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AppProvider } from './context/AppContext';
import { ConfirmProvider } from './context/ConfirmContext';
import Layout from './components/Layout';
import RequireAuth from './components/RequireAuth';
import { H1, Loading, Muted } from './components/ui';
import Home from './pages/Home';
import { Compare, CompareDual } from './pages/Compare';
import Bills from './pages/Bills';
import BillForm from './pages/BillForm';
import Offers from './pages/Offers';
import OfferForm from './pages/OfferForm';
import { Proposal, ProposalSaved, ProposalShow } from './pages/Proposal';
import Settings from './pages/Settings';
import Profiles from './pages/Profiles';
import Account from './pages/Account';
import Users from './pages/Users';
import Guide from './pages/Guide';
import Layouts from './pages/Layouts';
import LayoutReport from './pages/LayoutReport';

// Grafici e lettura dei PDF sono librerie pesanti: si scaricano solo aprendo quelle pagine.
const History = lazy(() => import('./pages/History'));
const Teach = lazy(() => import('./pages/Teach'));

const NotFound = () => <><H1>Pagina non trovata</H1><Muted>Questo indirizzo non esiste.</Muted></>;

export default function App() {
  return (
    <AuthProvider>
    <BrowserRouter>
      <RequireAuth>
        <AppProvider>
          <ConfirmProvider>
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route element={<Layout />}>
                  <Route index element={<Home />} />
                  <Route path="bills" element={<Bills />} />
                  <Route path="bills/new" element={<BillForm />} />
                  <Route path="history" element={<Navigate to="/history/power" replace />} />
                  <Route path="history/:commodity" element={<History />} />
                  <Route path="offers" element={<Offers />} />
                  <Route path="offers/new" element={<OfferForm />} />
                  <Route path="offers/:id" element={<OfferForm />} />
                  <Route path="compare" element={<Navigate to="/compare/power" replace />} />
                  <Route path="compare/dual" element={<CompareDual />} />
                  <Route path="compare/:commodity" element={<Compare />} />
                  <Route path="proposal" element={<Proposal />} />
                  <Route path="proposal/saved" element={<ProposalSaved />} />
                  <Route path="proposal/:id" element={<ProposalShow />} />
                  <Route path="guide" element={<Guide />} />
                  <Route path="settings" element={<Settings />} />
                  <Route path="profiles" element={<Profiles />} />
                  <Route path="account" element={<Account />} />
                  <Route path="users" element={<Users />} />
                  <Route path="layouts" element={<Layouts />} />
                  <Route path="layouts/teach" element={<Teach />} />
                  <Route path="layouts/:id/report" element={<LayoutReport />} />
                  <Route path="verdict" element={<Navigate to="/" replace />} />
                  {["accedi", "registrati", "simulazione"].map((p) => <Route key={p} path={p} element={<Navigate to="/" replace />} />)}
                  <Route path="*" element={<NotFound />} />
                </Route>
              </Routes>
            </Suspense>
          </ConfirmProvider>
        </AppProvider>
      </RequireAuth>
    </BrowserRouter>
    </AuthProvider>
  );
}
