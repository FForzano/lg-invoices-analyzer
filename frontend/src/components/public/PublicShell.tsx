import { useEffect, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { BrandMark } from '../Layout';
import Footer from '../Footer';
import { FOCUS_RING, PRIMARY_BUTTON, SOFT_BUTTON, TEXT_BUTTON } from '../styles';

/** Cornice delle pagine pubbliche (landing, simulazione): testata con accesso e registrazione, piede con le fonti. */
export default function PublicShell({ children, title }: { children: ReactNode; title?: string }) {
  const { registrationOpen } = useAuth();
  useEffect(() => { document.title = title ? `${title} · Bollette` : 'Bollette · scopri se conviene cambiare luce e gas'; }, [title]);
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-t-4 border-accent bg-surface shadow-panel">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2 lg:px-8">
          <Link to="/" className={`mr-auto inline-flex items-center gap-2.5 text-xl font-extrabold tracking-tight text-fg no-underline ${FOCUS_RING}`}><BrandMark /><span>Bollette</span></Link>
          <Link to="/accedi" className={registrationOpen ? TEXT_BUTTON : SOFT_BUTTON}>Accedi</Link>
          {registrationOpen && <Link to="/registrati" className={`${PRIMARY_BUTTON} hidden sm:inline-flex`}>Registrati</Link>}
        </div>
      </header>
      {children}
      <Footer />
    </div>
  );
}
