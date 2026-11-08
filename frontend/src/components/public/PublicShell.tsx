import { useEffect, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { BrandMark } from '../Layout';
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
      <footer className="border-t border-edge bg-surface">
        <div className="mx-auto max-w-6xl space-y-1 px-4 py-6 text-sm text-muted lg:px-8">
          <p>Le offerte vengono dagli <a className="font-bold text-accent underline" href="https://www.ilportaleofferte.it/portaleOfferte/it/open-data.page" target="_blank" rel="noopener noreferrer">open data del Portale Offerte</a> (ARERA / Acquirente Unico). L'app non è affiliata a nessun fornitore.</p>
          <p>Una stima non è un preventivo: prima di cambiare, controlla sempre le condizioni sul sito del venditore.</p>
        </div>
      </footer>
    </div>
  );
}
