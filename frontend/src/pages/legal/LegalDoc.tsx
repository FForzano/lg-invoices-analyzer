import { useEffect, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { H1, Notice } from '../../components/ui';

/** Da aggiornare a ogni modifica sostanziale di termini o informativa. */
export const LEGAL_UPDATED = '9 novembre 2026';

/** Chi risponde di questa installazione: il nome configurato (OPERATOR_NAME) o, finché manca, una formula neutra. */
export function useOperator() {
  const { site } = useAuth();
  const o = site.operator;
  const name = o.name || 'il gestore di questo sito';
  const contact = o.email ? <a href={`mailto:${o.email}`}>{o.email}</a> : <>il gestore del sito (i recapiti non sono ancora stati indicati)</>;
  return { site, o, name, contact };
}

/** Cornice dei testi legali: titolo, data, avviso se il gestore non ha indicato chi è, e scorrimento all'ancora (#sezione). */
export function LegalDoc({ title, children }: { title: string; children: ReactNode }) {
  const { site } = useAuth();
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return;
    const t = setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView(), 0);  // dopo lo scorrimento in cima del layout
    return () => clearTimeout(t);
  }, [hash]);
  return (
    <article className="guide">
      <H1 sub={`Ultimo aggiornamento: ${LEGAL_UPDATED}`}>{title}</H1>
      {!site.operator.name && <Notice level="warn">Chi gestisce questo sito non ha ancora indicato i propri dati (nome e recapiti): per ora il testo parla del «gestore del sito». L'amministratore può indicarli con OPERATOR_NAME, OPERATOR_EMAIL e OPERATOR_ADDRESS.</Notice>}
      {children}
    </article>
  );
}

export const Sec = ({ id, title, children }: { id?: string; title: string; children: ReactNode }) => (
  <section id={id} className="scroll-mt-4"><h2 className="text-xl font-bold">{title}</h2>{children}</section>
);
