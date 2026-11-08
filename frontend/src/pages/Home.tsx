import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Flame, Gauge, Zap } from 'lucide-react';
import { useQuery } from '../lib/useQuery';
import { commodityLabel, eur, num, unitOf } from '../lib/format';
import type { Analysis, DualVerdict, Message } from '../lib/types';
import { Actions, Card, ErrorBox, H1, InfoButton, LinkButton, Loading, Muted, Notice, VerdictBlock } from '../components/ui';
import { Modal } from '../components/Modal';
import { useApp } from '../context/AppContext';
import { TEXT_BUTTON } from '../components/styles';

interface HomeData { alerts: Message[]; analyses: Record<'power' | 'gas', Analysis>; dual: { verdict: DualVerdict | null } }
const iconBox = 'box-content h-[1.35rem] w-[1.35rem] rounded-full bg-accent-soft p-[.45rem] text-accent';

function CardTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-1 mt-3 flex items-center gap-2.5 text-2xl font-extrabold tracking-tight">{children}</h2>;
}

function CalcDetails({ a }: { a: Analysis }) {
  const [open, setOpen] = useState(false);
  const v = a.verdict!;
  const o = v.best.offer;
  const index = a.commodity === 'power' ? 'PUN' : 'PSV';
  const unit = unitOf(a.commodity);
  const price = o.price_type === 'fixed' ? `prezzo fisso ${num((o.price ?? o.price_f1) as number, 4)} €/${unit}` : `indicizzato, spread ${num(o.spread as number, 4)}`;
  return (
    <>
      <button type="button" className={TEXT_BUTTON} onClick={() => setOpen(true)} aria-haspopup="dialog">Dettagli del calcolo</button>
      <Modal open={open} onClose={() => setOpen(false)} title="Dettagli del calcolo" compact>
        <div className="space-y-3 pb-4 text-sm text-muted">
          {o.duration_months && <p>Condizioni economiche valide {String(o.duration_months)} mesi: dopo, il venditore può cambiare il prezzo. Se la attivi, marcala come «attuale» con la data di attivazione: ti avviso prima della fine.</p>}
          <p>Con {index}<InfoButton term={index.toLowerCase()} name={index} /> ±20%: risparmio da {eur(v.saving_range[0])} a {eur(v.saving_range[1])} l'anno.</p>
          <p>Condizioni importate: {price}, quota fissa {eur((o.fixed_fee_month as number) || 0)}/mese{o.expires_on ? `, valida fino al ${o.expires_on}` : ''}. Verificale sul sito del venditore.</p>
          {o.conditions && <><p><strong>Condizioni dichiarate dal venditore</strong> (da verificare sul suo sito):</p><ul className="list-disc pl-5">{o.conditions.split('\n').map((l, i) => <li key={i}>{l}</li>)}</ul></>}
          {o.after_term && <p><strong>Dopo il periodo</strong>: {o.after_term.replace(/\n/g, ' ')}</p>}
          <p><strong>{index}</strong>: prezzo all'ingrosso {a.commodity === 'power' ? "dell'energia elettrica" : 'del gas'} in Italia. Un'offerta «indicizzata» lo segue, quindi la bolletta sale e scende con il mercato. Il consumo è in {unit}{a.commodity === 'gas' ? ' (standard metri cubi)' : ''}.</p>
        </div>
      </Modal>
    </>
  );
}

function VerdictCard({ a }: { a: Analysis }) {
  const label = commodityLabel(a.commodity), index = a.commodity === 'power' ? 'PUN' : 'PSV', unit = unitOf(a.commodity);
  const v = a.verdict, c = a.consumption;
  return (
    <Card>
      <CardTitle>{a.commodity === 'power' ? <Zap className={iconBox} aria-hidden /> : <Flame className={iconBox} aria-hidden />}{label}</CardTitle>
      {!c ? <p>Carica una bolletta di {label.toLowerCase()} per stimare il consumo annuo.</p> : <>
        <Muted className="mb-3">Consumo annuo {num(c.total, 0)} {unit}{c.days_covered < 365 ? ` · da ${c.days_covered} giorni di bollette` : ''}</Muted>
        {c.partial && <Notice level="warn">Ho solo {c.days_covered} giorni di bollette: il consumo annuo è una proiezione con un profilo stagionale tipico e il verdetto è poco affidabile. Carica altre bollette (ideale 12 mesi, oppure una che riporti il consumo annuo).</Notice>}
        {!a.has_current ? <p>Manca l'offerta attuale. Se carichi il PDF della bolletta la rilevo da sola; altrimenti <Link className="font-bold text-accent underline" to={`/offers/new?commodity=${a.commodity}`}>inseriscila a mano</Link>.</p>
          : !v ? <p>Nessuna offerta alternativa da confrontare. <Link className="font-bold text-accent underline" to="/offers">Importa le offerte</Link>.</p>
          : <>
            <VerdictBlock good={v.worthwhile} label={v.worthwhile ? 'Conviene cambiare' : 'Non conviene cambiare'} figure={`${eur(v.saving)} l'anno`}
              note={v.worthwhile ? <>Risparmio stimato<InfoButton term="t_saving" name="Risparmio stimato" /> del {num(v.saving_pct, 0)}%.</> : `Risparmio massimo ${eur(v.saving)} l'anno (${num(v.saving_pct, 0)}%): troppo poco per cambiare.`} />
            <p>Migliore alternativa: <strong>{v.best.offer.name}</strong> – {v.best.offer.supplier}.<br />
              Costo annuo<InfoButton term="t_total" name="Costo annuo" /> stimato <strong>{eur(v.best.estimate.total)}</strong> contro <strong>{eur(v.current.estimate.total)}</strong> con l'offerta attuale.</p>
            {v.saving_range[1] - v.saving_range[0] < 1
              ? <Muted>Il risparmio non dipende dall'andamento del {index}<InfoButton term={index.toLowerCase()} name={index} />: anche l'offerta attuale è indicizzata.</Muted>
              : v.worthwhile && !v.robust && <Notice level="warn">Il vantaggio dipende dall'andamento del {index}: con prezzi dell'indice ±20%<InfoButton term="t_sensitivity" name="Sensibilità ±20%" /> il risparmio va da {eur(v.saving_range[0])} a {eur(v.saving_range[1])}.</Notice>}
            <div className="flex flex-wrap items-center gap-x-6">
              <CalcDetails a={a} />
              <Link className={TEXT_BUTTON} to={`/compare/${a.commodity}`}>Vedi tutte le offerte {label.toLowerCase()}</Link>
            </div>
          </>}
      </>}
    </Card>
  );
}

function DualCard({ v }: { v: DualVerdict }) {
  return (
    <Card>
      <CardTitle><Zap className={iconBox} aria-hidden /><Flame className={`${iconBox} -ml-1`} aria-hidden />Luce e gas insieme</CardTitle>
      <VerdictBlock good={v.worthwhile} label={v.worthwhile ? "Conviene un'offerta luce+gas" : 'Nessuna offerta luce+gas conviene'} figure={`${eur(v.saving)} l'anno`}
        note={v.worthwhile ? `Risparmio stimato del ${num(v.saving_pct, 0)}%.` : `Risparmio massimo ${eur(v.saving)} l'anno (${num(v.saving_pct, 0)}%): troppo poco per cambiare.`} />
      <p>Migliore alternativa: <strong>{v.best.power.offer.name}</strong> + <strong>{v.best.gas.offer.name}</strong> – {v.best.power.offer.supplier}.<br />
        Costo annuo<InfoButton term="t_total" name="Costo annuo" /> stimato <strong>{eur(v.best.total)}</strong> (luce {eur(v.best.power.estimate.total)}, gas {eur(v.best.gas.estimate.total)}).</p>
      {v.separate_saving > 0 && <>
        <div className="my-2 grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-2" role="group" aria-label="Insieme o separate">
          <div className="rounded-block bg-calm px-3 py-2"><span className="text-sm text-muted">Risparmio insieme</span><br /><span className="text-xl font-extrabold tabular-nums">{eur(v.saving)}</span></div>
          <div className="rounded-block bg-calm px-3 py-2"><span className="text-sm text-muted">Risparmio separate</span><br /><span className="text-xl font-extrabold tabular-nums">{eur(v.separate_saving)}</span></div>
        </div>
        <Muted>{v.beats_separate ? 'Cambiare insieme rende più che cambiare separatamente le due forniture.' : 'Cambiando luce e gas separatamente, con le migliori offerte singole, risparmieresti di più.'}</Muted>
      </>}
      <Link className={TEXT_BUTTON} to="/compare/dual">Vedi tutte le offerte luce+gas</Link>
    </Card>
  );
}

function PowerCard({ a }: { a: Analysis }) {
  const pw = a.power_advice;
  const [open, setOpen] = useState(false);
  if (!pw) return null;
  return (
    <Card>
      <CardTitle><Gauge className={iconBox} aria-hidden />Potenza impegnata<InfoButton term="power_kw" name="Potenza impegnata" /></CardTitle>
      {pw.suggested ? <>
        <p>Hai <strong>{num(pw.contracted, 1)} kW</strong> e in {pw.months} mesi il picco è stato <strong>{num(pw.peak, 1)} kW</strong>: potresti scendere a <strong>{num(pw.suggested, 1)} kW</strong>{pw.saving_year ? <>, risparmiando circa <strong>{eur(pw.saving_year)} l'anno</strong> di quota potenza</> : null}.</p>
        {pw.tight && <Notice level="warn">Margine ridotto: il picco è vicino al limite del nuovo livello e un forno, un phon e una lavatrice insieme potrebbero far staccare il contatore.</Notice>}
        {pw.partial && <Notice level="warn">Ho solo {pw.months} mesi di picchi: carica una bolletta che riporti lo storico annuale prima di decidere (d'inverno i picchi sono di solito più alti).</Notice>}
        <button type="button" className={TEXT_BUTTON} onClick={() => setOpen(true)} aria-haspopup="dialog">Cosa tenere presente</button>
        <Modal open={open} onClose={() => setOpen(false)} title="Cosa tenere presente" compact>
          <p className="pb-4 text-muted">La quota potenza è regolata e uguale per tutti i fornitori; l'importo è senza IVA. Il cambio di potenza può avere costi una tantum: chiedi al fornitore.</p>
        </Modal>
      </> : <Muted>Hai {num(pw.contracted, 1)} kW e il picco degli ultimi {pw.months} mesi è {num(pw.peak, 1)} kW: non c'è margine per ridurre la potenza.</Muted>}
    </Card>
  );
}

export default function Home() {
  const { profiles, profile } = useApp();
  const { data, error, loading } = useQuery<HomeData>('/home');
  const title = <H1 sub={profiles.length > 1 ? `Profilo ${profile.name}` : undefined}>Bollette luce e gas</H1>;
  if (loading && !data) return <>{title}<Loading /></>;
  if (error || !data) return <>{title}<ErrorBox error={error!} /></>;
  const list = [data.analyses.power, data.analyses.gas];
  if (!list.some((a) => a.consumption)) return (
    <>{title}
      <Card><h2 className="mb-1 mt-3 text-2xl font-extrabold tracking-tight">Comincia da una bolletta</h2>
        <p>Carica il PDF di una bolletta di luce o gas: leggo i consumi e l'offerta attuale, poi ti dico se conviene cambiare.</p>
        <Actions><LinkButton to="/bills/new">Carica la prima bolletta</LinkButton></Actions></Card>
      <Muted>Stima della sola parte decisa dal fornitore: restano fuori trasporto, oneri, imposte, bonus e canone TV.</Muted>
    </>
  );
  const judged = list.filter((a) => a.verdict);
  const dual = data.dual.verdict;
  return (
    <>
      {title}
      {(judged.length > 0 || dual) && (
        <p className="mb-4 max-w-[40rem] text-xl font-bold leading-snug">
          {judged.map((a) => `${commodityLabel(a.commodity)}: ${a.verdict!.worthwhile ? `conviene cambiare (${eur(a.verdict!.saving)} l'anno)` : 'non conviene'}. `)}
          {dual && dual.worthwhile && dual.beats_separate ? `Luce+gas insieme: conviene (${eur(dual.saving)} l'anno).` : ''}
        </p>
      )}
      {data.alerts.map((m, i) => <Notice key={i} level={m.level}>{m.text}</Notice>)}
      {list.map((a) => <VerdictCard key={a.commodity} a={a} />)}
      {dual && <DualCard v={dual} />}
      {list.map((a) => a.commodity === 'power' ? <PowerCard key="p" a={a} /> : null)}
      <Actions><LinkButton to="/bills/new">Carica bolletta</LinkButton><LinkButton to="/offers/new" soft>Nuova offerta</LinkButton></Actions>
      <Muted>Stima della sola parte decisa dal fornitore: restano fuori trasporto, oneri, imposte, bonus e canone TV. Verifica le condizioni sul sito del venditore prima di cambiare. <Link className="font-bold text-accent underline" to="/guide">Come leggere i numeri</Link></Muted>
    </>
  );
}
