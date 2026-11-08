import { useState, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link, NavLink, useSearchParams } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, Info, MinusCircle, X } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Modal } from './Modal';
import { CARD, DANGER_LINK, FOCUS_RING, PRIMARY_BUTTON, SOFT_BUTTON, fieldClass } from './styles';
import type { Message, PageInfo } from '../lib/types';

export const H1 = ({ children, sub }: { children: ReactNode; sub?: ReactNode }) => (
  <h1 className="mb-4 mt-5 text-[1.75rem] font-extrabold leading-tight tracking-tight text-accent-deep sm:text-[2rem]">
    {children}{sub && <span className="mt-1 block text-sm font-normal tracking-normal text-muted">{sub}</span>}
  </h1>
);
export const H2 = ({ children, id }: { children: ReactNode; id?: string }) => <h2 id={id} className="mb-2 mt-5 text-xl font-bold leading-snug">{children}</h2>;
export const Muted = ({ children, className = '' }: { children: ReactNode; className?: string }) => <p className={`max-w-[58ch] text-sm text-muted ${className}`}>{children}</p>;
export const Card = ({ children, className = '' }: { children: ReactNode; className?: string }) => <section className={`my-4 ${CARD} ${className}`}>{children}</section>;
export const Scroll = ({ children }: { children: ReactNode }) => <div className="my-2 mb-4 overflow-x-auto rounded-card border border-edge bg-surface shadow-panel">{children}</div>;

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean };
export const Button = ({ busy, className = '', children, ...p }: BtnProps) => <button type="button" {...p} aria-disabled={busy || p.disabled || undefined} disabled={p.disabled} onClick={busy ? undefined : p.onClick} className={`${PRIMARY_BUTTON} ${className}`}>{children}</button>;
export const SoftButton = ({ busy, className = '', children, ...p }: BtnProps) => <button type="button" {...p} aria-disabled={busy || undefined} onClick={busy ? undefined : p.onClick} className={`${SOFT_BUTTON} ${className}`}>{children}</button>;
export const LinkButton = ({ to, soft, children }: { to: string; soft?: boolean; children: ReactNode }) => <Link to={to} className={soft ? SOFT_BUTTON : PRIMARY_BUTTON}>{children}</Link>;
export const DangerLink = (p: ButtonHTMLAttributes<HTMLButtonElement>) => <button type="button" {...p} className={`${DANGER_LINK} min-h-[44px] px-1`} />;
export const Actions = ({ children }: { children: ReactNode }) => <div className="my-4 flex flex-wrap items-center gap-3">{children}</div>;

export function Tag({ kind = 'neutral', children }: { kind?: 'neutral' | 'current' | 'warn'; children: ReactNode }) {
  const c = kind === 'current' ? 'bg-accent-soft text-accent-deep' : kind === 'warn' ? 'bg-warn text-fg' : 'bg-calm';
  return <span className={`inline-block whitespace-nowrap rounded-full px-3 py-0.5 text-[.8rem] font-bold leading-6 ${c}`}>{children}</span>;
}

/** Cambio di vista dentro una pagina (Luce / Gas / insieme): pillole, la corrente piena. */
export function Tabs({ items }: { items: { to: string; label: string; end?: boolean }[] }) {
  return (
    <nav aria-label="Vista" className="my-2 mb-4 flex flex-wrap gap-2">
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.end}
          className={({ isActive }) => `inline-flex min-h-[44px] items-center rounded-full px-5 py-1.5 no-underline shadow-panel transition duration-200 hover:-translate-y-px hover:shadow-lift ${FOCUS_RING} ${isActive ? 'bg-accent font-bold text-on-accent' : 'bg-surface font-medium text-fg'}`}>{i.label}</NavLink>
      ))}
    </nav>
  );
}

export function Pager({ page }: { page: PageInfo }) {
  const [params, setParams] = useSearchParams();
  if (page.pages <= 1) return null;
  const go = (n: number) => { const p = new URLSearchParams(params); p.set('page', String(n)); setParams(p); window.scrollTo({ top: 0 }); };
  return (
    <p className="my-3 flex flex-wrap items-center gap-3">
      {page.number > 1 && <><button className="min-h-[44px] font-bold text-accent" onClick={() => go(1)} aria-label="Prima pagina">«</button><button className="min-h-[44px] font-bold text-accent" onClick={() => go(page.number - 1)}>← precedente</button></>}
      <span className="text-sm text-muted">Pagina {page.number} di {page.pages} · {page.total} elementi</span>
      {page.number < page.pages && <><button className="min-h-[44px] font-bold text-accent" onClick={() => go(page.number + 1)}>successiva →</button><button className="min-h-[44px] font-bold text-accent" onClick={() => go(page.pages)} aria-label="Ultima pagina">»</button></>}
    </p>
  );
}
export const usePage = () => Number(useSearchParams()[0].get('page') ?? 1) || 1;

/** Avviso: «warn» giallo con triangolo, «info» sobrio con filo. Mai solo colore: c'è sempre l'icona e il testo. */
export function Notice({ level = 'info', children, onDismiss }: { level?: 'info' | 'warn'; children: ReactNode; onDismiss?: () => void }) {
  const warn = level === 'warn';
  return (
    <div role={warn ? 'alert' : 'status'} className={`my-2 flex items-start gap-2 rounded-field px-4 py-3 ${warn ? 'bg-warn' : 'border border-line bg-surface text-sm text-muted'}`}>
      {warn ? <AlertTriangle className="mt-0.5 h-5 w-5 flex-none" aria-hidden /> : <Info className="mt-0.5 h-5 w-5 flex-none" aria-hidden />}
      <div className="min-w-0 flex-1">{children}</div>
      {onDismiss && <button type="button" onClick={onDismiss} aria-label="Chiudi avviso" className={`-m-2 flex h-11 w-11 flex-none items-center justify-center rounded-full ${FOCUS_RING}`}><X className="h-4 w-4" /></button>}
    </div>
  );
}
export function MessageList({ messages }: { messages?: Message[] }) {
  const { messages: shared, dismiss } = useApp();
  const list = messages ?? shared;
  return <>{list.map((m, i) => <Notice key={i} level={m.level} onDismiss={messages ? undefined : () => dismiss(i)}>{m.text}</Notice>)}</>;
}
export const Loading = () => <p className="my-8 text-center text-muted" role="status">Caricamento…</p>;
export const ErrorBox = ({ error }: { error: Error }) => <Notice level="warn">{error.message}</Notice>;

/** Tastino (i): apre una modale con la spiegazione in parole semplici (testi da app/glossary.py). */
export function InfoButton({ term, name }: { term: string; name?: string }) {
  const { help } = useApp();
  const [open, setOpen] = useState(false);
  if (!help[term]) return null;
  return (
    <>
      {'⁠'}
      <button type="button" onClick={() => setOpen(true)} aria-label={name ? `Cosa significa «${name}»?` : 'Cosa significa?'} aria-haspopup="dialog"
        className={`relative ml-0.5 inline-grid h-6 w-6 place-items-center rounded-full align-[-0.3em] normal-case text-accent hover:bg-accent-soft ${FOCUS_RING} before:absolute before:-inset-3 before:content-['']`}>
        <Info className="h-5 w-5" aria-hidden />
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title={name ?? 'Cosa significa?'} compact>
        <p className="pb-4 text-base normal-case tracking-normal">{help[term]}</p>
        <Link to="/guide" onClick={() => setOpen(false)} className="mb-2 inline-flex min-h-[44px] items-center font-bold text-accent underline underline-offset-4">Leggi la guida</Link>
      </Modal>
    </>
  );
}

// --- campi di form, legati a un oggetto di stato (useForm) --------------------------------------
export function useForm<T extends Record<string, unknown>>(initial: T) {
  const [values, setValues] = useState<T>(initial);
  return { values, set: (name: string, v: unknown) => setValues((s) => ({ ...s, [name]: v })), reset: (v: T) => setValues(v) };
}
export type Form = ReturnType<typeof useForm<Record<string, unknown>>>;
const str = (v: unknown) => (v === null || v === undefined ? '' : String(v));

interface FieldProps { form: Form; name: string; label: string; type?: 'text' | 'number' | 'date'; step?: string; required?: boolean; help?: string; placeholder?: string; full?: boolean; disabled?: boolean }
export function Field({ form, name, label, type = 'text', step = 'any', required, help, placeholder, full, disabled }: FieldProps) {
  return (
    <div className={full ? 'col-span-full' : ''}>
      <label className="flex flex-col gap-1 text-sm font-medium">
        <span>{label}{required && <span aria-hidden> *</span>}{help && <InfoButton term={help} name={label} />}</span>
        <input name={name} type={type} step={type === 'number' ? step : undefined} value={str(form.values[name])} required={required} placeholder={placeholder} disabled={disabled}
          onChange={(e) => form.set(name, e.target.value)} className={`${fieldClass} disabled:cursor-not-allowed disabled:bg-calm disabled:text-muted`} />
      </label>
    </div>
  );
}
export function SelectField({ form, name, label, options, help, required }: { form: Form; name: string; label: string; options: [string, string][]; help?: string; required?: boolean }) {
  return (
    <div>
      <label className="flex flex-col gap-1 text-sm font-medium">
        <span>{label}{help && <InfoButton term={help} name={label} />}</span>
        <select name={name} value={str(form.values[name])} required={required} onChange={(e) => form.set(name, e.target.value)} className={fieldClass}>
          {!required && <option value="" />}
          {options.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
        </select>
      </label>
    </div>
  );
}
export function CheckField({ form, name, label, help }: { form: Form; name: string; label: string; help?: string }) {
  return (
    <div>
      <label className="flex min-h-[44px] items-center gap-3 text-sm font-medium">
        <input type="checkbox" checked={Boolean(form.values[name])} onChange={(e) => form.set(name, e.target.checked)} className="h-5 w-5" />
        <span>{label}{help && <InfoButton term={help} name={label} />}</span>
      </label>
    </div>
  );
}
export function AreaField({ form, name, label, help, rows = 3 }: { form: Form; name: string; label: string; help?: string; rows?: number }) {
  return (
    <div className="col-span-full">
      <label className="flex flex-col gap-1 text-sm font-medium">
        <span>{label}{help && <InfoButton term={help} name={label} />}</span>
        <textarea name={name} rows={rows} value={str(form.values[name])} onChange={(e) => form.set(name, e.target.value)} className={fieldClass} />
      </label>
    </div>
  );
}
export const FieldGrid = ({ children, className = '' }: { children: ReactNode; className?: string }) => <div className={`grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-3 ${className}`}>{children}</div>;
export const GroupTitle = ({ children }: { children: ReactNode }) => <h2 className="col-span-full mt-4 text-[.8rem] font-bold uppercase tracking-wider text-muted">{children}</h2>;
export function Group({ legend, children, hint }: { legend: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <fieldset className="col-span-full my-4 rounded-card border border-edge bg-surface px-4 pb-4 pt-2 shadow-panel">
      <legend className="px-1 font-bold">{legend}</legend>
      <FieldGrid>{children}</FieldGrid>
      {hint && <div className="mt-2 text-sm text-muted">{hint}</div>}
    </fieldset>
  );
}

// --- verdetto -------------------------------------------------------------------------------
/** Esito = colore + testo + icona. Il timbro ambra compare solo quando il risparmio supera la soglia. */
export function VerdictBlock({ good, label, figure, note }: { good: boolean; label: string; figure?: string; note: ReactNode }) {
  return (
    <div className={`my-2 mb-3 rounded-block px-4 pb-4 pt-3.5 ${good ? 'bg-good-bg' : 'bg-calm'}`}>
      <p className={`m-0 flex items-center gap-1.5 text-xl font-extrabold ${good ? 'text-good' : ''}`}>
        {good ? <CheckCircle2 className="h-5 w-5" aria-hidden /> : <MinusCircle className="h-5 w-5" aria-hidden />}{label}
      </p>
      {good && figure && (
        <p className="my-2 origin-left -rotate-2 animate-stamp"><span className="inline-block rounded-block border-2 border-sticker-ink bg-sticker px-3 pb-1 pt-0.5 text-[2rem] font-extrabold leading-tight tracking-tight text-sticker-ink shadow-panel sm:text-[2.5rem]">{figure}</span></p>
      )}
      <p className={`m-0 ${!good ? 'mt-1' : ''}`}>{note}</p>
    </div>
  );
}
export const good = (x: number | null) => (x == null ? '' : x > 0 ? 'text-good' : 'text-bad');
export { fieldClass };
