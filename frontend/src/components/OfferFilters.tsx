import { useState } from 'react';
import { Check } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { FOCUS_RING, fieldClass } from './styles';

const KEYS = ['type', 'no_exit', 'bonus'] as const;
const TYPES: [string, string][] = [['', 'Tutte'], ['fixed', 'Prezzo fisso'], ['indexed', 'Indicizzate']];
const pill = (on: boolean) => `inline-flex min-h-[44px] items-center gap-1.5 rounded-full px-4 py-1.5 shadow-panel transition duration-200 hover:-translate-y-px hover:shadow-lift ${FOCUS_RING} ${on ? 'bg-accent font-bold text-on-accent' : 'bg-surface font-medium text-fg'}`;

/** I filtri stanno nell'indirizzo (?type=fixed&no_exit=1&bonus=1): si possono condividere e il tasto indietro funziona. */
export function useOfferFilters() {
  const [params] = useSearchParams();
  return Object.fromEntries(KEYS.map((k) => [k, params.get(k) ?? undefined])) as Record<(typeof KEYS)[number], string | undefined>;
}

export const filtersActive = (f: Record<string, string | undefined>) => KEYS.some((k) => f[k]);

/** Restringe offerte e confronto: tipo di prezzo, senza oneri di uscita, con bonus. `search` aggiunge la ricerca per fornitore (nell'elenco Offerte c'è già). */
export default function OfferFilters({ search = false }: { search?: boolean }) {
  const [params, setParams] = useSearchParams();
  const [term, setTerm] = useState(params.get('q') ?? '');
  const change = (key: string, value: string | null) => {
    const p = new URLSearchParams(params);
    if (value) p.set(key, value); else p.delete(key);
    p.delete('page');
    setParams(p);
  };
  const type = params.get('type') ?? '';
  const any = KEYS.some((k) => params.get(k)) || (search && params.get('q'));
  return (
    <div role="group" aria-label="Filtri" className="my-3 space-y-2">
      {search && <form role="search" className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); change('q', term.trim() || null); }}>
        <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Cerca fornitore o offerta" aria-label="Cerca fornitore o offerta" className={`${fieldClass} max-w-xs flex-1`} />
        <button type="submit" className={pill(false)}>Cerca</button>
      </form>}
      <div className="flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Tipo di prezzo" className="flex flex-wrap gap-2">
          {TYPES.map(([v, label]) => (
            <button key={v} type="button" role="radio" aria-checked={type === v} onClick={() => change('type', v || null)} className={pill(type === v)}>{label}</button>
          ))}
        </div>
        {([['no_exit', 'Senza oneri di uscita'], ['bonus', 'Con bonus o sconti']] as const).map(([k, label]) => {
          const on = params.get(k) === '1';
          return <button key={k} type="button" aria-pressed={on} onClick={() => change(k, on ? null : '1')} className={pill(on)}>{on && <Check className="h-4 w-4" strokeWidth={3} aria-hidden />}{label}</button>;
        })}
        {any && <button type="button" onClick={() => { setTerm(''); const p = new URLSearchParams(); setParams(p); }} className={`min-h-[44px] rounded px-2 font-bold text-accent underline-offset-4 hover:underline ${FOCUS_RING}`}>Azzera filtri</button>}
      </div>
    </div>
  );
}
