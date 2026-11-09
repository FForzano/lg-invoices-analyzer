import { useState, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../lib/api';
import { BrandMark } from './Layout';
import { Button, Notice } from './ui';
import { fieldClass } from './styles';

/** Schermata a tutto campo per accesso e cambio password obbligatorio (fuori dal layout dell'app, che richiede una sessione). */
export function AuthCard({ title, intro, children }: { title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <main className="grid min-h-screen place-items-center px-4 py-8">
      <div className="w-full max-w-sm rounded-card border border-edge bg-surface p-6 shadow-panel sm:p-8">
        <div className="mb-5 flex items-center gap-2.5 text-xl font-extrabold tracking-tight"><BrandMark /><span>Bollette</span></div>
        <h1 className="text-2xl font-extrabold leading-tight text-accent-deep">{title}</h1>
        {intro && <p className="mt-1 text-sm text-muted">{intro}</p>}
        {children}
        <p className="mb-0 mt-6 border-t border-edge pt-3 text-xs text-muted">
          <Link to="/termini" className="font-bold underline underline-offset-4">Termini d'uso</Link> · <Link to="/privacy" className="font-bold underline underline-offset-4">Privacy e cookie</Link>
        </p>
      </div>
    </main>
  );
}

export const errorText = (e: unknown) => (e instanceof ApiError ? e.message : 'Qualcosa è andato storto: riprova.');

export function TextInput({ label, ...p }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex flex-col gap-1 text-sm font-medium">{label}
      <input {...p} className={fieldClass} /></label>
  );
}

/** Form con errore in linea e pulsante in attesa: serve dove `useAction` (che dipende dall'app già avviata) non c'è ancora. */
export function SimpleForm({ onSubmit, cta, children }: { onSubmit: () => Promise<void>; cta: string; children: ReactNode }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null);
    try { await onSubmit(); } catch (err) { setError(errorText(err)); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={(e) => void submit(e)} className="mt-5 space-y-4">
      {error && <Notice level="warn">{error}</Notice>}
      {children}
      <Button type="submit" busy={busy} className="w-full">{cta}</Button>
    </form>
  );
}
