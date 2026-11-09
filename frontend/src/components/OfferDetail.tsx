import { ExternalLink } from 'lucide-react';
import { Modal } from './Modal';
import { FOCUS_RING, PRIMARY_BUTTON } from './styles';
import { eur, num, unitOf } from '../lib/format';
import { Notice, Tag } from './ui';
import type { Assumptions, Consumption, Offer, Ranked } from '../lib/types';

/** Solo http/https: l'indirizzo viene dal venditore (o da un CSV) e non va mai eseguito. */
export const safeUrl = (u: unknown): string | null => {
  if (typeof u !== 'string') return null;
  try { const p = new URL(u); return p.protocol === 'https:' || p.protocol === 'http:' ? p.href : null; } catch { return null; }
};

/** Le righe del testo con il contenuto degli oneri: scarta le sole intestazioni («Oneri di recesso anticipato»), se c'è altro. */
export const exitLines = (text: string | null | undefined): string[] => {
  const all = (text ?? '').split('\n').map((l) => l.trim()).filter(Boolean);
  const body = all.filter((l) => /\d/.test(l) || l.length > 60);
  return body.length ? body : all;
};

/** Etichette (oneri di uscita, bonus) e, sotto il nome, il testo del venditore sugli oneri: si legge senza aprire l'offerta. */
export const Flags = ({ o }: { o: Offer }) => (
  <>
    {(o.exit_terms || o.bonus_terms) && <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
      {o.exit_terms && <Tag kind="warn">oneri di uscita</Tag>}{o.bonus_terms && <Tag>bonus</Tag>}</span>}
    {o.exit_terms && <span className="mt-1 line-clamp-5 max-w-[60ch] text-sm font-normal text-muted">{exitLines(o.exit_terms).join(' ')}</span>}
  </>
);

const n = (x: unknown): number | null => (typeof x === 'number' ? x : null);
const dateIt = (iso: string) => iso.split('-').reverse().join('/');

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-edge py-2 last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className={`text-right tabular-nums ${strong ? 'text-lg font-extrabold' : 'font-bold'}`}>{value}</dd>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mt-5"><h3 className="mb-1 text-[.8rem] font-bold uppercase tracking-wider text-muted">{title}</h3>{children}</section>;
}

/** Dettaglio di un'offerta del confronto: i prezzi come li dichiara il venditore, la stima sul tuo consumo e il link all'offerta. */
export default function OfferDetail({ ranked, consumption, assumptions, onClose }: { ranked: Ranked | null; consumption: Consumption | null; assumptions: Assumptions | null; onClose: () => void }) {
  const o = ranked?.offer;
  const power = o?.commodity === 'power';
  const unit = o ? unitOf(o.commodity) : '';
  const rows: [string, string][] = [];
  if (o) {
    const add = (label: string, v: unknown, suffix: string, d = 4) => { const x = n(v); if (x != null) rows.push([label, `${num(x, d)} ${suffix}`]); };
    if (o.price_type === 'fixed') {
      if (n(o.price_f1) != null && n(o.price_f2) != null && n(o.price_f3) != null) {
        add('Prezzo F1', o.price_f1, `€/${unit}`); add('Prezzo F2', o.price_f2, `€/${unit}`); add('Prezzo F3', o.price_f3, `€/${unit}`);
      } else add('Prezzo dell’energia', o.price, `€/${unit}`);
      add('Prezzo medio di vendita', o.avg_price, `€/${unit}`);
    } else {
      add(`Spread sopra ${power ? 'PUN' : 'PSV'}`, o.spread, `€/${unit}`);
      add('Dispacciamento', o.dispatching, `€/${unit}`); add('Capacità', o.capacity, `€/${unit}`);
      add('Gestione', o.gas_mgmt, `€/${unit}`); add('Adeguamento PCS', o.pcs_adjustment, `€/${unit}`);
      if (power) rows.push(['Perdite di rete', n(o.loss_pct) != null ? `${num(n(o.loss_pct), 1)}%` : assumptions ? `${num(assumptions.loss_pct, 1)}% (ipotesi)` : '–']);
    }
  }
  const perUnit = ranked && consumption && consumption.total > 0 ? ranked.estimate.energy / consumption.total : null;
  const url = safeUrl(o?.offer_url);
  const conditions = typeof o?.conditions === 'string' ? o.conditions.split('\n').filter(Boolean) : [];
  const exitTerms = exitLines(typeof o?.exit_terms === 'string' ? o.exit_terms : null);
  const bonuses = typeof o?.bonus_terms === 'string' ? o.bonus_terms.split('\n').filter(Boolean) : [];
  const code = typeof o?.source === 'string' && o.source.startsWith('arera:') && o.source !== 'arera:?' ? o.source.slice(6) : null;
  const range = (lo: unknown, hi: unknown, u: string) => (n(lo) != null && n(hi) != null ? `da ${num(n(lo), 0)} a ${num(n(hi), 0)} ${u}` : n(lo) != null ? `da ${num(n(lo), 0)} ${u}` : n(hi) != null ? `fino a ${num(n(hi), 0)} ${u}` : null);
  const who: [string, string][] = [];
  if (o?.residency) who.push(['Residenza', o.residency === 'resident' ? 'Solo residenti' : 'Solo non residenti']);
  const pw = range(o?.power_min, o?.power_max, 'kW'), cs = range(o?.consumption_min, o?.consumption_max, unit);
  if (pw) who.push(['Potenza ammessa', pw]);
  if (cs) who.push(['Consumo annuo ammesso', cs]);
  const activation = typeof o?.activation_terms === 'string' ? o.activation_terms.split('\n').filter(Boolean) : [];
  const afterTerm = typeof o?.after_term === 'string' ? o.after_term : null;
  const monthly = n(o?.fixed_fee_month), powerFee = n(o?.power_fee_kw_month), once = n(o?.one_off_discount);

  return (
    <Modal open={!!ranked} onClose={onClose} title={o ? `${o.supplier} – ${o.name}` : ''} wide>
      {ranked && o && <div className="pb-4">
        {!!o.is_current && <p className="mb-2 text-sm font-bold text-accent-deep">È la tua offerta attuale.</p>}
        {exitTerms.length > 0 && <div className="mt-3"><Notice level="warn">
          <strong>Se esci prima della scadenza potresti pagare un onere.</strong>
          {exitTerms.map((t, i) => <span key={i} className="mt-1 block">{t}</span>)}
          <span className="mt-1 block text-sm text-muted">Testo del venditore sul Portale Offerte ARERA: leggi le condizioni sul suo sito prima di firmare.</span>
        </Notice></div>}
        <Section title="Prezzo dell'energia">
          {rows.length ? <dl>{rows.map(([l, v]) => <Row key={l} label={l} value={v} strong={l === rows[0][0]} />)}</dl> : <p className="text-muted">Il prezzo non è indicato in modo semplice.</p>}
          {o.price_type === 'indexed' && <p className="mt-1 max-w-[58ch] text-sm text-muted">Offerta indicizzata: il prezzo segue il {power ? 'PUN' : 'PSV'} di mese in mese, qui c&rsquo;è solo la parte aggiunta dal venditore.</p>}
          {perUnit != null && <dl className="mt-2 rounded-block bg-calm px-3"><Row label={`Stima sul tuo consumo (media, solo energia)`} value={`${num(perUnit, 4)} €/${unit}`} strong /></dl>}
        </Section>
        {(monthly != null || powerFee != null || once != null) && <Section title="Quote fisse e sconti">
          <dl>
            {monthly != null && <Row label="Quota fissa" value={`${eur(monthly)} al mese`} />}
            {powerFee != null && <Row label="Quota potenza" value={`${num(powerFee, 4)} €/kW al mese`} />}
            {once != null && <Row label="Sconto una tantum" value={eur(once)} />}
          </dl>
        </Section>}
        {bonuses.length > 0 && <Section title="Bonus e sconti">
          <ul className="list-disc space-y-1 pl-5">{bonuses.map((t, i) => <li key={i}>{t}</li>)}</ul>
          <p className="mt-1 max-w-[58ch] text-sm text-muted">Come li descrive il venditore. Non sono nel costo annuo stimato qui sotto: controlla a quali condizioni valgono e per quanto tempo.</p>
        </Section>}
        <Section title="Stima per il tuo consumo">
          <dl>
            <Row label="Energia" value={eur(ranked.estimate.energy)} /><Row label="Quote fisse" value={eur(ranked.estimate.fixed_fee + ranked.estimate.power_fee)} />
            <Row label="Sconti" value={eur(ranked.estimate.discount)} /><Row label="Costo annuo" value={eur(ranked.estimate.total)} strong />
          </dl>
          <p className="mt-1 max-w-[58ch] text-sm text-muted">Solo la parte decisa dal fornitore: trasporto, oneri, imposte, bonus sociali e canone TV sono esclusi.</p>
        </Section>
        <Section title="Condizioni">
          <dl>
            {o.duration_months != null && <Row label="Durata delle condizioni" value={`${o.duration_months} mesi`} />}
            {o.expires_on && <Row label="Offerta valida fino al" value={dateIt(o.expires_on)} />}
          </dl>
          {conditions.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5">{conditions.map((c, i) => <li key={i}>{c}</li>)}</ul>}
          {afterTerm && <p className="mt-2"><strong>A fine periodo: </strong>{afterTerm}</p>}
          {!conditions.length && !afterTerm && !exitTerms.length && o.duration_months == null && !o.expires_on && <p className="text-muted">Nessuna condizione indicata.</p>}
        </Section>
        {(code || who.length > 0 || o.payment_methods || activation.length > 0 || o.phone) && <Section title="Per chi vale e come si sottoscrive">
          <dl>
            {code && <Row label="Codice offerta" value={code} />}
            {who.map(([l, v]) => <Row key={l} label={l} value={v} />)}
            {typeof o.payment_methods === 'string' && <Row label="Pagamento" value={o.payment_methods} />}
            {typeof o.phone === 'string' && <Row label="Telefono del venditore" value={o.phone} />}
          </dl>
          {activation.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5">{activation.map((t, i) => <li key={i}>{t}</li>)}</ul>}
          {code && <p className="mt-1 max-w-[58ch] text-sm text-muted">Il codice offerta è quello del Portale Offerte ARERA: confrontalo con quello riportato sul sito o sul contratto per essere certo che sia proprio questa offerta.</p>}
        </Section>}
        <div className="mt-6">
          {url ? <>
            <a href={url} target="_blank" rel="noopener noreferrer" className={`${PRIMARY_BUTTON} inline-flex items-center gap-2 ${FOCUS_RING}`}>Vai all&rsquo;offerta sul sito del venditore<ExternalLink className="h-4 w-4" aria-hidden /></a>
            <p className="mt-2 max-w-[58ch] text-sm text-muted">Si apre il sito di {o.supplier}, all&rsquo;indirizzo indicato sul Portale Offerte ARERA. Le condizioni valide sono quelle scritte lì.</p>
          </> : <p className="max-w-[58ch] text-sm text-muted">{String(o.source ?? '').startsWith('arera:') ? 'Il venditore non ha indicato su ARERA una pagina per questa offerta.' : 'Offerta inserita a mano: nessun link.'}</p>}
        </div>
      </div>}
    </Modal>
  );
}
