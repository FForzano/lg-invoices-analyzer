import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Check, ChevronDown, SlidersHorizontal, Star, X } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { FOCUS_RING, fieldClass } from './styles';
import { api, type WithMessages } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import { useApp } from '../context/AppContext';
import type { FilterPreset } from '../lib/types';

const KEYS = ['type', 'no_exit', 'bonus', 'no_domic', 'online', 'power'] as const;
type Key = (typeof KEYS)[number];
const TYPES: [string, string][] = [['', 'Tutte'], ['fixed', 'Prezzo fisso'], ['indexed', 'Indicizzate']];
const POWERS = [1.5, 3, 4.5, 6, 7.5, 10, 15];
const SWITCHES: { key: Key; group: string; label: string; chip: string }[] = [
  { key: 'no_exit', group: 'Escludi', label: 'Con oneri di uscita', chip: 'Senza oneri di uscita' },
  { key: 'no_domic', group: 'Escludi', label: 'Con domiciliazione obbligatoria', chip: 'Pagabile senza domiciliazione' },
  { key: 'online', group: 'Mostra solo', label: 'Attivabile online', chip: 'Attivabile online' },
  { key: 'bonus', group: 'Mostra solo', label: 'Con bonus o sconti', chip: 'Con bonus o sconti' },
];
const kw = (n: number) => `${String(n).replace('.', ',')} kW`;
const pill = (on: boolean) => `inline-flex min-h-[44px] items-center gap-1.5 rounded-full px-4 py-1.5 shadow-panel transition duration-200 hover:-translate-y-px hover:shadow-lift ${FOCUS_RING} ${on ? 'bg-accent font-bold text-on-accent' : 'bg-surface font-medium text-fg'}`;

/** I filtri stanno nell'indirizzo (?type=fixed&no_exit=1…): si possono condividere e il tasto indietro funziona. */
export function useOfferFilters() {
  const [params] = useSearchParams();
  return Object.fromEntries(KEYS.map((k) => [k, params.get(k) ?? undefined])) as Record<Key, string | undefined>;
}

export const filtersActive = (f: Record<string, string | undefined>) => KEYS.some((k) => f[k]);

function Group({ title, children }: { title: string; children: ReactNode }) {
  return <div><h3 className="mb-2 text-[.8rem] font-bold uppercase tracking-wider text-muted">{title}</h3><div className="flex flex-wrap gap-2">{children}</div></div>;
}

/**
 * Restringe offerte e confronto. Barra con ricerca e un solo pulsante «Filtri» (con il conteggio) che apre il pannello a gruppi;
 * i filtri attivi restano sempre visibili come etichette da togliere con un tocco.
 * `power` (solo confronto luce): la potenza del contratto, di default quella del profilo o delle bollette.
 */
export default function OfferFilters({ search = false, power }: { search?: boolean; power?: number }) {
  const [params, setParams] = useSearchParams();
  const [term, setTerm] = useState(params.get('q') ?? '');
  const [open, setOpen] = useState(false);
  const panel = useId();
  const { flash } = useApp();
  const { run, busy } = useAction();
  const presets = useQuery<{ items: FilterPreset[] }>('/filter-presets');
  const [naming, setNaming] = useState('');
  const appliedDefault = useRef(false);
  const change = (key: string, value: string | null) => {
    const p = new URLSearchParams(params);
    if (value) p.set(key, value); else p.delete(key);
    p.delete('page');
    setParams(p);
  };
  const current = () => { const p = new URLSearchParams(); KEYS.forEach((k) => params.get(k) && p.set(k, params.get(k)!)); return p.toString(); };
  const apply = (query: string, replace = false) => { const p = new URLSearchParams(query); if (params.get('q')) p.set('q', params.get('q')!); setParams(p, { replace }); };
  // all'apertura, senza filtri nell'indirizzo, vale il preferito segnato come predefinito (una volta sola per pagina)
  useEffect(() => {
    if (appliedDefault.current || !presets.data) return;
    appliedDefault.current = true;
    const d = presets.data.items.find((p) => p.is_default);
    if (d && !KEYS.some((k) => params.get(k))) apply(d.query, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presets.data]);
  const save = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => { const r = await api.post<WithMessages>('/filter-presets', { name: naming, query: current() }); flash(r.messages); setNaming(''); presets.reload(); });
  };
  const remove = (p: FilterPreset) => void run(async () => { await api.del(`/filter-presets/${p.id}`); presets.reload(); });
  const makeDefault = (p: FilterPreset) => void run(async () => { await api.put('/filter-presets/default', { id: p.is_default ? null : p.id }); presets.reload(); });
  const type = params.get('type') ?? '';
  const chosenPower = Number(params.get('power')) || null;
  const chips: { key: Key; label: string }[] = [];
  if (type) chips.push({ key: 'type', label: TYPES.find(([v]) => v === type)?.[1] ?? type });
  SWITCHES.forEach((s) => params.get(s.key) === '1' && chips.push({ key: s.key, label: s.chip }));
  if (chosenPower) chips.push({ key: 'power', label: `Potenza ${kw(chosenPower)}` });
  const count = chips.length;
  const powerOptions = [...new Set([...POWERS, ...(power ? [power] : []), ...(chosenPower ? [chosenPower] : [])])].sort((a, b) => a - b);

  return (
    <div className="my-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {search && <form role="search" className="flex min-w-0 flex-1 gap-2" onSubmit={(e) => { e.preventDefault(); change('q', term.trim() || null); }}>
          <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Cerca fornitore o offerta" aria-label="Cerca fornitore o offerta" className={`${fieldClass} max-w-xs flex-1`} />
          <button type="submit" className={pill(false)}>Cerca</button>
        </form>}
        <button type="button" aria-expanded={open} aria-controls={panel} onClick={() => setOpen(!open)} className={pill(open)}>
          <SlidersHorizontal className="h-4 w-4" aria-hidden />Filtri
          {count > 0 && <span className={`ml-0.5 inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1.5 text-[.8rem] font-bold ${open ? 'bg-on-accent text-accent' : 'bg-accent text-on-accent'}`} aria-label={`${count} attivi`}>{count}</span>}
          <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} aria-hidden />
        </button>
      </div>

      {open && <div id={panel} role="group" aria-label="Filtri" className="grid gap-5 rounded-card border border-edge bg-surface p-4 shadow-panel sm:grid-cols-2">
        <Group title="Tipo di prezzo">
          <div role="radiogroup" aria-label="Tipo di prezzo" className="flex flex-wrap gap-2">
            {TYPES.map(([v, label]) => <button key={v} type="button" role="radio" aria-checked={type === v} onClick={() => change('type', v || null)} className={pill(type === v)}>{label}</button>)}
          </div>
        </Group>
        {power !== undefined && <Group title="Potenza del contratto">
          <label className="flex items-center gap-2 text-sm font-medium">
            <select value={chosenPower ?? ''} onChange={(e) => change('power', e.target.value || null)} aria-label="Potenza del contratto" className={`${fieldClass} w-auto`}>
              <option value="">La tua: {kw(power)}</option>
              {powerOptions.filter((p) => p !== power).map((p) => <option key={p} value={p}>{kw(p)}</option>)}
            </select>
          </label>
          <p className="basis-full max-w-[40ch] text-sm text-muted">Le offerte e i costi valgono per questa potenza. Cambiala per vedere cosa succede con un contatore diverso.</p>
        </Group>}
        {(['Escludi', 'Mostra solo'] as const).map((g) => (
          <Group key={g} title={g}>
            {SWITCHES.filter((s) => s.group === g).map((s) => {
              const on = params.get(s.key) === '1';
              return <button key={s.key} type="button" aria-pressed={on} onClick={() => change(s.key, on ? null : '1')} className={pill(on)}>{on && <Check className="h-4 w-4" strokeWidth={3} aria-hidden />}{g === 'Escludi' ? s.label : s.chip}</button>;
            })}
          </Group>
        ))}
        <div className="border-t border-edge pt-4 sm:col-span-2">
          <h3 className="mb-2 text-[.8rem] font-bold uppercase tracking-wider text-muted">Preferiti</h3>
          {presets.data?.items.length ? <ul className="mb-3 flex flex-wrap gap-2">
            {presets.data.items.map((p) => (
              <li key={p.id} className="inline-flex items-center rounded-full bg-calm shadow-panel">
                <button type="button" onClick={() => apply(p.query)} className={`min-h-[44px] rounded-l-full pl-4 pr-2 font-bold ${FOCUS_RING}`}>{p.name}</button>
                <button type="button" onClick={() => makeDefault(p)} aria-pressed={p.is_default} aria-label={p.is_default ? `Non applicare «${p.name}» all'apertura` : `Applica «${p.name}» all'apertura`} title="Applica all'apertura"
                  className={`flex min-h-[44px] w-10 items-center justify-center ${FOCUS_RING} ${p.is_default ? 'text-accent' : 'text-muted hover:text-accent'}`}><Star className="h-5 w-5" fill={p.is_default ? 'currentColor' : 'none'} aria-hidden /></button>
                <button type="button" onClick={() => remove(p)} aria-label={`Elimina «${p.name}»`} className={`flex min-h-[44px] w-10 items-center justify-center rounded-r-full text-muted hover:text-bad ${FOCUS_RING}`}><X className="h-4 w-4" aria-hidden /></button>
              </li>))}
          </ul> : <p className="mb-3 max-w-[58ch] text-sm text-muted">Salva una combinazione di filtri per riusarla con un tocco. La stella indica quella da applicare quando apri la pagina.</p>}
          <form onSubmit={save} className="flex flex-wrap gap-2">
            <input value={naming} onChange={(e) => setNaming(e.target.value)} maxLength={40} placeholder="Nome, es. «Solo fisso, senza penali»" aria-label="Nome dei filtri da salvare" className={`${fieldClass} max-w-xs flex-1`} />
            <button type="submit" disabled={!naming.trim() || count === 0 || busy} className={`${pill(false)} disabled:pointer-events-none disabled:opacity-50`}>Salva i filtri attuali</button>
          </form>
        </div>
      </div>}

      {count > 0 && <ul className="flex flex-wrap items-center gap-2" aria-label="Filtri attivi">
        {chips.map((c) => (
          <li key={c.key}><button type="button" onClick={() => change(c.key, null)} aria-label={`Togli: ${c.label}`}
            className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-full bg-accent-soft px-3.5 text-sm font-bold text-accent-deep transition-colors hover:bg-accent hover:text-on-accent ${FOCUS_RING}`}>{c.label}<X className="h-4 w-4" strokeWidth={3} aria-hidden /></button></li>
        ))}
        <li><button type="button" onClick={() => { const p = new URLSearchParams(params); KEYS.forEach((k) => p.delete(k)); p.delete('page'); setParams(p); }} className={`min-h-[44px] rounded px-2 text-sm font-bold text-accent underline-offset-4 hover:underline ${FOCUS_RING}`}>Azzera filtri</button></li>
      </ul>}
    </div>
  );
}
