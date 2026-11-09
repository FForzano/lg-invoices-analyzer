import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BrandMark } from './Layout';
import { FOCUS_RING } from './styles';

const PORTALE = 'https://www.ilportaleofferte.it/portaleOfferte/it/open-data.page';
const SORGENTE = 'https://github.com/FForzano/lg-invoices-analyzer';
const link = `inline-flex min-h-[44px] items-center gap-1 rounded text-fg underline-offset-4 hover:text-accent hover:underline sm:min-h-[2rem] ${FOCUS_RING}`;
const title = 'mb-1 mt-0 text-[.8rem] font-bold uppercase tracking-wider text-muted';

const External = ({ href, children }: { href: string; children: ReactNode }) => (
  <a href={href} target="_blank" rel="noopener noreferrer" className={link}>{children}<ExternalLink className="h-3.5 w-3.5 flex-none text-muted" aria-hidden /><span className="sr-only">(si apre in una nuova scheda)</span></a>
);

/** Piè di pagina unico per l'app e per le pagine pubbliche: cosa è, dove leggere termini e privacy, da dove vengono i dati, chi gestisce il sito. */
export default function Footer({ className = '' }: { className?: string }) {
  const { site, user, demo, registrationOpen } = useAuth();
  const op = site.operator;
  const hasOperator = Boolean(op.name || op.email);
  return (
    <footer className={`border-t border-edge ${className}`}>
      <div className="mx-auto max-w-[60rem] px-3 py-8 sm:px-4 lg:px-8">
        <div className="grid gap-x-10 gap-y-6 sm:grid-cols-[1.3fr_1fr_1fr]">
          <div>
            <p className="m-0 flex items-center gap-2.5 text-lg font-extrabold tracking-tight"><BrandMark className="h-7 w-7" /><span>Bollette</span></p>
            <p className="mb-0 mt-2 max-w-[34ch] text-sm text-muted">Confronto onesto di luce e gas sul costo reale annuo. Software libero, fatto per stare a casa tua.</p>
          </div>

          <nav aria-label="Informazioni" className="flex flex-col items-start">
            <h2 className={title}>Informazioni</h2>
            <Link to="/termini" className={link}>Termini d'uso</Link>
            <Link to="/privacy" className={link}>Privacy e cookie</Link>
            {user ? <Link to="/guide" className={link}>Guida</Link>
              : <>
                {demo && <Link to="/simulazione" className={link}>Simulazione gratuita</Link>}
                <Link to="/accedi" className={link}>Accedi</Link>
                {registrationOpen && <Link to="/registrati" className={link}>Registrati</Link>}
              </>}
            <External href={PORTALE}>Fonte delle offerte: Portale Offerte</External>
            <External href={SORGENTE}>Codice sorgente (Apache-2.0)</External>
          </nav>

          <div>
            <h2 className={title}>Gestore del sito</h2>
            {hasOperator ? (
              <address className="m-0 space-y-0.5 text-sm not-italic">
                {op.name && <p className="m-0 font-bold">{op.name}</p>}
                {op.address && <p className="m-0 text-muted">{op.address}</p>}
                {op.vat && <p className="m-0 text-muted">P. IVA {op.vat}</p>}
                {op.registry && <p className="m-0 text-muted">Registro imprese / REA {op.registry}</p>}
                {op.email && <p className="m-0"><a href={`mailto:${op.email}`} className={`${link} !min-h-[2rem] font-bold text-accent`}>{op.email}</a></p>}
              </address>
            ) : <p className="m-0 max-w-[34ch] text-sm text-muted">Chi gestisce questo sito non ha ancora indicato i propri dati di contatto.</p>}
          </div>
        </div>

        <div className="mt-8 space-y-1 border-t border-edge pt-4 text-sm text-muted">
          <p className="m-0 max-w-none">Una stima non è un preventivo: prima di cambiare fornitore controlla le condizioni sul sito del venditore. Bollette non è affiliato ad ARERA, ad Acquirente Unico né a nessun fornitore.</p>
          {site.ads_enabled && <p className="m-0 max-w-none">Alcuni spazi ospitano contenuti sponsorizzati, sempre indicati come tali e mai mescolati ai risultati. Vedi i <Link to="/termini#pubblicita" className="font-bold text-accent underline underline-offset-4">termini d'uso</Link>.</p>}
          <p className="m-0 max-w-none">© {new Date().getFullYear()} Bollette</p>
        </div>
      </div>
    </footer>
  );
}
