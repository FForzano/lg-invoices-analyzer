import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, type WithMessages } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import { eur, num } from '../lib/format';
import type { Analysis, Estimate, ProposalValues, ProposalVerdict, Ranked } from '../lib/types';
import { useApp } from '../context/AppContext';
import { useConfirm } from '../context/ConfirmContext';
import { Actions, AreaField, Button, Card, CheckField, DangerLink, ErrorBox, Field, FieldGrid, Group, H1, H2, InfoButton, LinkButton, Loading, Muted, Notice, Scroll, SelectField, SoftButton, useForm } from '../components/ui';

interface Evaluation { analysis: Analysis; estimate: Estimate | null; verdict: ProposalVerdict | null; best: Ranked | null }
const th = 'px-3.5 py-2.5 text-left text-[.8rem] font-bold uppercase tracking-wide text-muted bg-calm whitespace-nowrap';
const td = 'px-3.5 py-2.5 border-b border-edge whitespace-nowrap';
const link = 'font-bold text-accent underline';

function Result({ ev, commodity, duration }: { ev: Evaluation; commodity: string; duration?: number | null }) {
  const { analysis: a, estimate: est, verdict: v, best } = ev;
  const unit = commodity === 'power' ? 'kWh' : 'Smc';
  return (
    <div className="space-y-2">
      {!est || !a.consumption ? <Notice>Servono bollette di questa fornitura per stimare il consumo annuo.</Notice> : <>
        <p>Consumo annuo usato: <strong>{num(a.consumption.total, 0)} {unit}</strong> <span className="text-sm text-muted">({a.consumption.source})</span></p>
        {v ? <>
          <Notice level={v.worthwhile ? 'info' : 'warn'}>
            {v.worthwhile && v.robust ? <><strong>Conviene</strong>: risparmieresti circa {eur(v.saving)} il primo anno ({num(v.saving_pct, 1)}%), anche con PUN/PSV ±20%<InfoButton term="t_sensitivity" />.</>
              : v.worthwhile ? <><strong>Conviene, ma non con certezza</strong>: circa {eur(v.saving)} il primo anno ({num(v.saving_pct, 1)}%); con PUN/PSV ±20%<InfoButton term="t_sensitivity" /> il risparmio va da {eur(v.saving_range[0])} a {eur(v.saving_range[1])}.</>
              : v.saving > 0 ? <><strong>Guadagno troppo piccolo</strong>: circa {eur(v.saving)} il primo anno, sotto la soglia che giustifica il cambio.</>
              : <><strong>Non conviene</strong>: costerebbe circa {eur(-v.saving)} in più della tua offerta attuale.</>}
          </Notice>
          <Scroll><table className="w-full">
            <thead><tr><th className={th} /><th className={`${th} text-right`}>Energia<InfoButton term="t_energy" /></th><th className={`${th} text-right`}>Quote fisse<InfoButton term="t_fixed" /></th><th className={`${th} text-right`}>Sconti<InfoButton term="t_discount" /></th><th className={`${th} text-right`}>Costo annuo<InfoButton term="t_total" /></th></tr></thead>
            <tbody>{([['Proposta', v.proposal, false], ['Offerta attuale', v.current, true]] as const).map(([n, e, cur]) => (
              <tr key={n} className={cur ? 'bg-accent-soft' : ''}><td className={td}>{n}</td><td className={`${td} text-right`}>{eur(e.energy)}</td><td className={`${td} text-right`}>{eur(e.fixed_fee + e.power_fee)}</td><td className={`${td} text-right`}>{eur(e.discount)}</td><td className={`${td} text-right`}><strong>{eur(e.total)}</strong></td></tr>))}</tbody></table></Scroll>
          <p>Senza i bonus una tantum<InfoButton term="t_saving_steady" /> (dal secondo anno) la differenza è di <strong>{eur(v.saving_steady)}</strong> l'anno{v.saving_steady <= 0 ? ': il vantaggio sta tutto nel bonus' : ''}. {duration ? `Le condizioni durano ${duration} mesi: chiedi cosa succede dopo.` : 'Chiedi per quanto tempo valgono questi prezzi.'}</p>
        </> : <>
          <p>Costo annuo stimato della proposta: <strong>{eur(est.total)}</strong> (energia {eur(est.energy)}, quote fisse {eur(est.fixed_fee + est.power_fee)}, sconti {eur(est.discount)}).</p>
          <Notice>Manca un'offerta attuale per questa fornitura (si rileva dalla bolletta o si marca in <Link className={link} to="/offers">Offerte</Link>): non posso dire se conviene.</Notice>
        </>}
        {best && <Muted>Per confronto, la migliore offerta pubblicata costa {eur(best.estimate.total)} l'anno ({best.offer.supplier} – {best.offer.name}).</Muted>}
        <Muted>Ipotesi per le offerte indicizzate: {commodity === 'power' ? <>PUN<InfoButton term="pun" /> {num(a.assumptions!.pun, 3)} €/kWh</> : <>PSV<InfoButton term="psv" /> {num(a.assumptions!.psv, 3)} €/Smc</>} (<Link className={link} to="/settings">modifica</Link>).</Muted>
      </>}
      <Muted>Stima della sola parte decisa dal fornitore: trasporto, oneri, imposte, bonus sociali e canone TV sono esclusi. Controlla di avere i prezzi senza IVA e che «fisso» non sia un prezzo scontato a tempo.</Muted>
    </div>
  );
}

export function Proposal() {
  const [params] = useSearchParams();
  const from = params.get('from');
  const navigate = useNavigate();
  const { flash } = useApp();
  const { run, busy } = useAction();
  const { data: loaded } = useQuery<{ proposal: ProposalValues }>(from ? `/proposals/${from}` : null);
  const { data: saved } = useQuery<{ items: unknown[] }>('/proposals');
  const form = useForm<Record<string, unknown>>({ commodity: params.get('commodity') === 'gas' ? 'gas' : 'power', price_type: 'fixed' });
  const [ev, setEv] = useState<Evaluation | null>(null);
  useEffect(() => { if (loaded) form.reset(loaded.proposal as Record<string, unknown>); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [loaded]);

  const evaluate = () => run(async () => { setEv(await api.post<Evaluation>('/proposals/evaluate', form.values)); });
  const save = () => run(async () => { const r = await api.post<WithMessages & { id: number }>('/proposals', form.values); flash(r.messages); navigate(`/proposal/${r.id}`); });

  return (
    <>
      <H1>Valuta una proposta</H1>
      <Muted>Un operatore ti propone un'offerta che non trovi nel catalogo? Inserisci quello che ti dice (anche solo i campi che conosci) e la confronto con la tua offerta attuale. Salvala per ritrovarla e controllare il contratto prima di firmare.</Muted>
      <form onSubmit={(e) => { e.preventDefault(); void evaluate(); }} className="mt-3">
        <FieldGrid>
          <SelectField form={form} name="commodity" label="Fornitura" options={[['power', 'Luce'], ['gas', 'Gas']]} required help="commodity" />
          <Field form={form} name="supplier" label="Fornitore (facoltativo)" help="supplier" />
          <SelectField form={form} name="price_type" label="Tipo di prezzo" options={[['fixed', 'Fisso'], ['indexed', 'Indicizzato (PUN/PSV + spread)']]} required help="price_type" />
          <Field form={form} name="duration_months" label="Durata delle condizioni (mesi)" type="number" step="1" help="duration_months" />
          <Group legend="Prezzo energia (€/kWh o €/Smc, IVA e imposte escluse)" hint={<Muted>Indicizzato: per la luce, se te li comunicano, aggiungi anche dispacciamento, perdite di rete e oneri di capacità qui sotto.</Muted>}>
            <Field form={form} name="price" label="Prezzo fisso" type="number" help="price" /><Field form={form} name="price_f1" label="Fisso F1 (luce)" type="number" help="price_f1" />
            <Field form={form} name="price_f2" label="Fisso F2 (luce)" type="number" help="price_f2" /><Field form={form} name="price_f3" label="Fisso F3 (luce)" type="number" help="price_f3" />
            <Field form={form} name="spread" label="Spread su PUN/PSV (indicizzato)" type="number" help="spread" /><Field form={form} name="avg_price" label="Prezzo medio dichiarato (se dato)" type="number" help="avg_price" />
          </Group>
          <Group legend="Altre voci">
            <Field form={form} name="fixed_fee_month" label="Quota fissa (€/mese)" type="number" help="fixed_fee_month" /><Field form={form} name="power_fee_kw_month" label="Quota potenza (€/kW/mese)" type="number" help="power_fee_kw_month" />
            <Field form={form} name="one_off_discount" label="Sconti/bonus una tantum (€, primo anno)" type="number" help="one_off_discount" /><Field form={form} name="loss_pct" label="Perdite di rete (%) – luce" type="number" help="loss_pct" />
            <Field form={form} name="dispatching" label="Dispacciamento (€/kWh) – luce" type="number" help="dispatching" /><Field form={form} name="capacity" label="Oneri di capacità (€/kWh) – luce" type="number" help="capacity" />
            <CheckField form={form} name="dispatching_extra" label="Dispacciamento/capacità fatturati a parte" help="dispatching_extra" />
            <Field form={form} name="gas_mgmt" label="Gestione variabile (€/Smc) – gas" type="number" help="gas_mgmt" /><Field form={form} name="pcs_adjustment" label="Adeguamento PCS (€/Smc) – gas" type="number" help="pcs_adjustment" />
          </Group>
          <Group legend="Da ricordare per il contratto">
            <Field form={form} name="contact" label="Chi l'ha proposta / riferimento chiamata" help="contact" /><Field form={form} name="received_on" label="Data della proposta" type="date" help="received_on" />
            <AreaField form={form} name="notes" label="Cos'altro ti hanno promesso a voce" help="notes" />
          </Group>
        </FieldGrid>
        <Actions>
          <Button type="submit" busy={busy}>Valuta</Button>
          <SoftButton busy={busy} onClick={() => void save()}>{form.values.id ? 'Aggiorna' : 'Salva'} la proposta</SoftButton>
          <Link className={link} to="/proposal/saved">Proposte salvate{saved?.items.length ? ` (${saved.items.length})` : ''}</Link>
        </Actions>
      </form>
      {ev && <><H2>Risultato</H2><Card><Result ev={ev} commodity={String(form.values.commodity)} duration={Number(form.values.duration_months) || null} /></Card></>}
    </>
  );
}

export function ProposalSaved() {
  const confirm = useConfirm();
  const { run } = useAction();
  const { data, error, loading, reload } = useQuery<{ items: (ProposalValues & { supplier: string; commodity: string })[] }>('/proposals');
  const remove = async (p: { id: number | null; supplier: string }) => {
    if (!(await confirm({ title: 'Eliminare la proposta?', message: `Proposta ${p.supplier}.` }))) return;
    await run(async () => { await api.del(`/proposals/${p.id}`); reload(); });
  };
  return (
    <>
      <H1>Proposte salvate</H1>
      <Actions><LinkButton to="/proposal" soft>+ Valuta una proposta</LinkButton></Actions>
      {loading && !data ? <Loading /> : error || !data ? <ErrorBox error={error!} /> : (
        <Scroll><table className="w-full">
          <thead><tr><th className={th}>Data</th><th className={th}>Fornitura</th><th className={th}>Fornitore</th><th className={th}>Riferimento</th><th className={th} /><th className={th} /></tr></thead>
          <tbody>{data.items.map((p) => (
            <tr key={p.id} className="hover:bg-calm">
              <td className={td}>{p.received_on || (p.created_at ?? '').slice(0, 10)}</td><td className={td}>{p.commodity === 'power' ? 'Luce' : 'Gas'}</td>
              <td className={td}><Link className={link} to={`/proposal/${p.id}`}>{p.supplier}</Link></td><td className={td}>{p.contact || '–'}</td>
              <td className={td}><Link className={link} to={`/proposal/${p.id}`}>controlla contratto</Link></td>
              <td className={td}><DangerLink onClick={() => void remove(p)}>elimina</DangerLink></td>
            </tr>))}
            {!data.items.length && <tr><td colSpan={6} className={`${td} text-muted`}>Nessuna proposta salvata.</td></tr>}
          </tbody></table></Scroll>)}
    </>
  );
}

export function ProposalShow() {
  const { id } = useParams();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const { flash } = useApp();
  const { run } = useAction();
  const { data, error, loading } = useQuery<Partial<Evaluation> & { proposal: ProposalValues; checklist: [string, string][]; always_check: string[]; messages: { level: 'info' | 'warn'; text: string }[] }>(`/proposals/${id}`);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox error={error!} />;
  const p = data.proposal;
  const remove = async () => {
    if (!(await confirm({ title: 'Eliminare la proposta?', message: `Proposta ${String(p.supplier)}.` }))) return;
    await run(async () => { await api.del(`/proposals/${id}`); flash('Proposta eliminata.'); navigate('/proposal/saved'); });
  };
  return (
    <>
      <H1>Proposta {String(p.supplier)} · {p.commodity === 'power' ? 'luce' : 'gas'}</H1>
      <Muted>{p.received_on ? `Ricevuta il ${p.received_on}. ` : ''}{p.contact ? `Riferimento: ${p.contact}.` : ''}</Muted>
      {data.messages.map((m, i) => <Notice key={i} level={m.level}>{m.text}</Notice>)}
      <Actions><LinkButton to={`/proposal?from=${id}`} soft>Modifica</LinkButton><Link className={link} to="/proposal/saved">Tutte le proposte</Link><DangerLink onClick={() => void remove()}>elimina</DangerLink></Actions>
      <H2>Da verificare nel contratto</H2>
      <Muted>Prima di firmare, controlla che ogni voce coincida con quanto ti hanno detto.</Muted>
      <Scroll><table className="w-full"><thead><tr><th className={th}>Voce</th><th className={th}>Detto a voce</th></tr></thead>
        <tbody>{data.checklist.map(([l, val]) => <tr key={l}><td className={td}>☐ {l}</td><td className={td}>{val}</td></tr>)}</tbody></table></Scroll>
      {p.notes && <><h3 className="mt-4 font-bold">Promesse a voce</h3><p className="whitespace-pre-line">{p.notes}</p></>}
      <h3 className="mt-4 font-bold">Da chiedere comunque</h3>
      <ul className="list-none space-y-1">{data.always_check.map((q) => <li key={q}>☐ {q}</li>)}</ul>
      {data.analysis && <><H2>Conviene?</H2><Card><Result ev={data as Evaluation} commodity={String(p.commodity)} duration={Number(p.duration_months) || null} /></Card></>}
    </>
  );
}
