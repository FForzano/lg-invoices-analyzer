import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '../lib/useQuery';
import { eur, num, unitOf } from '../lib/format';
import type { Analysis, Bundle, PageInfo, Ranked } from '../lib/types';
import AdSlot from '../components/AdSlot';
import OfferDetail from '../components/OfferDetail';
import { FOCUS_RING } from '../components/styles';
import { ErrorBox, good, H1, InfoButton, Loading, Muted, Notice, Pager, Scroll, Tabs, Tag, usePage } from '../components/ui';

const TABS = [{ to: '/compare/power', label: 'Luce' }, { to: '/compare/gas', label: 'Gas' }, { to: '/compare/dual', label: 'Luce + gas insieme' }];
const th = 'px-3.5 py-2.5 text-left text-[.8rem] font-bold uppercase tracking-wide text-muted bg-calm';
const td = 'px-3.5 py-2.5 border-b border-edge whitespace-nowrap';
/** Il nome dell'offerta è il pulsante che ne apre il dettaglio. */
const NameButton = ({ onClick, children }: { onClick: () => void; children: React.ReactNode }) => (
  <button type="button" onClick={onClick} className={`min-h-[44px] rounded-block text-left font-bold text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent ${FOCUS_RING}`}>{children}</button>
);
const NOTE = 'Stima della sola parte decisa dal fornitore (energia, quote fisse, potenza, sconti): trasporto, oneri, imposte, bonus sociali e canone TV sono esclusi. Non è un preventivo.';

export function Compare() {
  const { commodity = 'power' } = useParams();
  const page = usePage();
  const [open, setOpen] = useState<Ranked | null>(null);
  const { data, error, loading } = useQuery<{ analysis: Analysis; items: Ranked[]; page: PageInfo }>(`/compare/${commodity}`, { page });
  const title = <H1>Confronto {commodity === 'power' ? 'luce' : 'gas'}</H1>;
  if (loading && !data) return <>{title}<Tabs items={TABS} /><Loading /></>;
  if (error || !data) return <>{title}<Tabs items={TABS} /><ErrorBox error={error!} /></>;
  const a = data.analysis, c = a.consumption, s = a.settings, as = a.assumptions;
  const unit = unitOf(commodity);
  return (
    <>
      {title}<Tabs items={TABS} />
      {!c ? <Notice>Servono bollette di questa fornitura per stimare il consumo annuo.</Notice> : <>
        <div className="space-y-1">
          <p>Consumo annuo: <strong>{num(c.total, 0)} {unit}</strong> <span className="text-sm text-muted">({c.source})</span></p>
          {c.partial && <Notice level="warn">Solo {c.days_covered} giorni di bollette: consumo annuo proiettato con un profilo stagionale tipico, stima poco affidabile.</Notice>}
          {commodity === 'power' && !c.bands && <Muted>Fasce non presenti: ripartizione tipica 33% F1, 30% F2, 37% F3.</Muted>}
          <Muted>Ipotesi per le offerte indicizzate: {commodity === 'power'
            ? <>PUN<InfoButton term="pun" name="PUN" /> medio annuo {num(s.pun as number, 3)} €/kWh × {num(a.season_multiplier, 2)} (stagionalità sui tuoi consumi) = {num(as!.pun, 3)} €/kWh, perdite di rete {num(as!.loss_pct, 1)}% se non indicate</>
            : <>PSV<InfoButton term="psv" name="PSV" /> medio annuo {num(s.psv as number, 3)} €/Smc × {num(a.season_multiplier, 2)} (stagionalità sui tuoi consumi) = {num(as!.psv, 3)} €/Smc</>}
            {' '}(<Link className="font-bold text-accent underline" to="/settings">modifica</Link>). Zona: regione {s.region || '–'}, provincia {s.province || '–'}, comune {s.comune || '–'}.</Muted>
        </div>
        <Pager page={data.page} />
        <Scroll><table className="w-full">
          <thead><tr><th className={th}>Offerta</th>
            <th className={`${th} text-right`}>Energia<InfoButton term="t_energy" /></th><th className={`${th} text-right`}>Quote fisse<InfoButton term="t_fixed" /></th>
            <th className={`${th} text-right`}>Sconti<InfoButton term="t_discount" /></th><th className={`${th} text-right`}>Costo annuo<InfoButton term="t_total" /></th><th className={`${th} text-right`}>Risparmio<InfoButton term="t_saving" /></th></tr></thead>
          <tbody>{data.items.map((r, i) => (
            <tr key={i} className={r.offer.is_current ? 'bg-accent-soft' : 'hover:bg-calm'}>
              <td className={`${td} whitespace-normal`}><NameButton onClick={() => setOpen(r)}>{r.offer.supplier} – {r.offer.name}</NameButton>{r.offer.is_current && <> <Tag kind="current">attuale</Tag></>}</td>
              <td className={`${td} text-right`}>{eur(r.estimate.energy)}</td><td className={`${td} text-right`}>{eur(r.estimate.fixed_fee + r.estimate.power_fee)}</td>
              <td className={`${td} text-right`}>{eur(r.estimate.discount)}</td><td className={`${td} text-right`}><strong>{eur(r.estimate.total)}</strong></td>
              <td className={`${td} text-right ${good(r.saving)}`}>{r.saving == null || r.offer.is_current ? (r.saving == null ? '–' : '') : eur(r.saving)}</td>
            </tr>))}
            {!data.items.length && <tr><td colSpan={6} className={`${td} text-muted`}>Nessuna offerta valida.</td></tr>}
          </tbody></table></Scroll>
        <Pager page={data.page} />
        <OfferDetail ranked={open} consumption={c} assumptions={as} onClose={() => setOpen(null)} />
        {a.skipped.length > 0 && <Muted>{a.skipped.length} offerte non valutabili per dati incompleti.</Muted>}
      </>}
      <Muted className="mt-3">{NOTE}</Muted>
      <AdSlot slot="compare-end" />
    </>
  );
}

export function CompareDual() {
  const page = usePage();
  const [open, setOpen] = useState<Ranked | null>(null);
  const { data, error, loading } = useQuery<{ power: Analysis; gas: Analysis; items: Bundle[]; page: PageInfo }>('/compare-dual', { page });
  const title = <H1>Confronto luce + gas insieme</H1>;
  if (loading && !data) return <>{title}<Tabs items={TABS} /><Loading /></>;
  if (error || !data) return <>{title}<Tabs items={TABS} /><ErrorBox error={error!} /></>;
  return (
    <>
      {title}<Tabs items={TABS} />
      {!(data.power.consumption && data.gas.consumption) ? <Notice>Servono bollette sia di luce sia di gas per stimare i consumi annui.</Notice> : <>
        <Muted>Offerte con luce e gas dello stesso fornitore, da sottoscrivere insieme. Costo = parte decisa dal fornitore per luce e gas. Il risparmio è rispetto alle due offerte attuali{!(data.power.has_current && data.gas.has_current) ? ': manca l\'offerta attuale di una delle due, quindi non posso calcolarlo' : ''}.</Muted>
        <Pager page={data.page} />
        <Scroll><table className="w-full">
          <thead><tr><th className={th}>Offerta luce</th><th className={th}>Offerta gas</th><th className={`${th} text-right`}>Luce</th><th className={`${th} text-right`}>Gas</th>
            <th className={`${th} text-right`}>Costo annuo<InfoButton term="t_total" /></th><th className={`${th} text-right`}>Risparmio<InfoButton term="t_saving" /></th></tr></thead>
          <tbody>{data.items.map((b, i) => (
            <tr key={i} className="hover:bg-calm">
              <td className={`${td} whitespace-normal`}><NameButton onClick={() => setOpen(b.power)}>{b.power.offer.supplier} – {b.power.offer.name}</NameButton></td><td className={`${td} whitespace-normal`}><NameButton onClick={() => setOpen(b.gas)}>{b.gas.offer.name}</NameButton></td>
              <td className={`${td} text-right`}>{eur(b.power.estimate.total)}</td><td className={`${td} text-right`}>{eur(b.gas.estimate.total)}</td>
              <td className={`${td} text-right`}><strong>{eur(b.total)}</strong></td><td className={`${td} text-right ${good(b.saving)}`}>{eur(b.saving)}</td>
            </tr>))}
            {!data.items.length && <tr><td colSpan={6} className={`${td} text-muted`}>Nessuna offerta luce+gas valida nella tua zona. <Link className="font-bold text-accent underline" to="/offers">Importa le offerte</Link>.</td></tr>}
          </tbody></table></Scroll>
        <Pager page={data.page} />
        <OfferDetail ranked={open} consumption={open?.offer.commodity === 'gas' ? data.gas.consumption : data.power.consumption} assumptions={open?.offer.commodity === 'gas' ? data.gas.assumptions : data.power.assumptions} onClose={() => setOpen(null)} />
      </>}
      <Muted className="mt-3">Sconti e bonus una tantum non sono inclusi. Trasporto, oneri, imposte, bonus sociali e canone TV sono esclusi. Non è un preventivo.</Muted>
      <AdSlot slot="compare-end" />
    </>
  );
}
