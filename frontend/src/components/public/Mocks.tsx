import { Check, FileText } from 'lucide-react';
import { VerdictBlock } from '../ui';

/** Ricostruzioni dell'interfaccia con dati d'esempio (non sono bollette né offerte reali): illustrano i passi della landing. */
const Frame = ({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) => (
  <figure role="img" aria-label={label} className={`m-0 w-full max-w-sm rounded-card border border-edge bg-surface p-5 shadow-panel ${className}`}>{children}</figure>
);
const Bar = ({ w, className = '' }: { w: string; className?: string }) => <span className={`block h-2 rounded-full bg-calm ${className}`} style={{ width: w }} />;
const Tag = ({ children }: { children: React.ReactNode }) => <span className="absolute -top-2 right-3 rounded-full bg-accent px-2.5 py-0.5 text-xs font-bold text-on-accent">{children}</span>;
const hit = 'rounded-block bg-accent-soft px-2 py-1 font-bold text-accent-deep ring-1 ring-accent/40';

/** 1 · il PDF della bolletta, con i valori che l'app va a cercare evidenziati */
export function MockBill() {
  return (
    <Frame label="Esempio: una bolletta della luce in PDF, con periodo, consumo, totale e offerta evidenziati">
      <div className="relative" aria-hidden>
        <Tag>PDF</Tag>
        <div className="mb-4 flex items-center gap-2 text-muted"><FileText className="h-5 w-5" /><span className="text-sm font-bold">Bolletta luce · Fornitore Esempio</span></div>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-3"><span className="text-muted">Periodo</span><span className={hit}>01/03 – 30/04/2026</span></div>
          <div className="flex items-center justify-between gap-3"><span className="text-muted">Consumo fatturato</span><span className={hit}>412 kWh</span></div>
          <div className="flex items-center justify-between gap-3"><span className="text-muted">Offerta</span><span className={hit}>Prezzo Fisso 12</span></div>
          <div className="flex items-center justify-between gap-3 border-t border-edge pt-3"><span className="font-bold">Totale da pagare</span><span className={hit}>98,40 €</span></div>
        </div>
        <div className="mt-5 space-y-2"><Bar w="92%" /><Bar w="78%" /><Bar w="64%" /></div>
      </div>
    </Frame>
  );
}

/** 2 · i valori letti, con la spunta */
export function MockRead() {
  const rows: [string, string][] = [['Fornitura', 'Luce'], ['Periodo', '60 giorni'], ['Consumo', '412 kWh'], ['Totale', '98,40 €'], ['Offerta attuale', 'Prezzo Fisso 12']];
  return (
    <Frame label="Esempio: i valori letti dalla bolletta, ciascuno con la spunta">
      <ul aria-hidden className="m-0 list-none space-y-2.5 p-0">
        {rows.map(([k, v]) => (
          <li key={k} className="flex items-center gap-3 rounded-block bg-calm px-3 py-2.5">
            <span className="grid h-6 w-6 flex-none place-items-center rounded-full bg-accent text-on-accent"><Check className="h-4 w-4" strokeWidth={3} /></span>
            <span className="text-sm text-muted">{k}</span><span className="ml-auto font-bold">{v}</span>
          </li>))}
      </ul>
      <p aria-hidden className="mb-0 mt-4 text-xs text-muted">Letto con regole sul testo del PDF: niente intelligenza artificiale esterna nella simulazione.</p>
    </Frame>
  );
}

/** 3 · il costo annuo stimato delle offerte, in ordine */
export function MockRank() {
  const rows = [{ n: 'Offerta A', c: 918, best: true }, { n: 'Offerta B', c: 947 }, { n: 'Offerta C', c: 981 }, { n: 'La tua offerta', c: 1062, mine: true }];
  return (
    <Frame label="Esempio: il costo annuo stimato di tre offerte a confronto con quella attuale">
      <div aria-hidden className="space-y-3.5">
        <p className="m-0 text-xs font-bold uppercase tracking-wider text-muted">Costo annuo stimato sul tuo consumo</p>
        {rows.map((r) => (
          <div key={r.n}>
            <div className="mb-1 flex items-baseline justify-between text-sm"><span className={r.mine ? 'font-bold' : ''}>{r.n}{r.mine && <span className="ml-2 rounded-full bg-calm px-2 py-0.5 text-xs font-bold text-muted">attuale</span>}</span><span className="font-bold tabular-nums">{r.c.toLocaleString('it-IT')} €</span></div>
            <div className="h-2.5 rounded-full bg-calm"><div className={`h-full rounded-full ${r.best ? 'bg-accent' : r.mine ? 'bg-muted' : 'bg-accent/40'}`} style={{ width: `${(r.c / 1062) * 100}%` }} /></div>
          </div>))}
      </div>
    </Frame>
  );
}

/** 4 · il verdetto, con il vero componente (e il timbro) dell'app */
export function MockVerdict() {
  return (
    <Frame label="Esempio: il verdetto «Conviene cambiare», con il risparmio annuo stimato">
      <div aria-hidden>
        <VerdictBlock good label="Conviene cambiare" figure="144 € l'anno" note="Risparmio stimato del 14%." />
        <p className="m-0 text-sm">Migliore alternativa: <strong>Offerta A</strong>. Costo annuo stimato <strong>918 €</strong> contro <strong>1.062 €</strong> con l'offerta attuale.</p>
        <p className="mb-0 mt-3 text-xs text-muted">Il consiglio arriva solo se il risparmio vale lo sforzo: almeno 30 € e il 5%.</p>
      </div>
    </Frame>
  );
}
