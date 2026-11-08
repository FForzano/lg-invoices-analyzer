import { useEffect, type FormEvent } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, type WithMessages } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import type { Offer } from '../lib/types';
import { useApp } from '../context/AppContext';
import { AreaField, Button, CheckField, ErrorBox, Field, FieldGrid, Group, H1, LinkButton, Loading, Muted, SelectField, useForm } from '../components/ui';

export default function OfferForm() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { flash } = useApp();
  const { run, busy } = useAction();
  const { data, error, loading } = useQuery<{ offer: Offer }>(id ? `/offers/${id}` : null);
  const form = useForm<Record<string, unknown>>({ commodity: params.get('commodity') === 'gas' ? 'gas' : 'power', price_type: 'fixed' });
  useEffect(() => { if (data) form.reset(data.offer as Record<string, unknown>); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [data]);

  const save = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const r = id ? await api.put<WithMessages>(`/offers/${id}`, form.values) : await api.post<WithMessages>('/offers', form.values);
      flash(r.messages); navigate('/offers');
    });
  };
  const title = <H1>{id ? 'Modifica' : 'Nuova'} offerta</H1>;
  if (id && loading) return <>{title}<Loading /></>;
  if (id && (error || !data)) return <>{title}<ErrorBox error={error!} /></>;
  return (
    <>
      {title}
      <form onSubmit={save}>
        <FieldGrid>
          <SelectField form={form} name="commodity" label="Fornitura" options={[['power', 'Luce'], ['gas', 'Gas']]} required help="commodity" />
          <Field form={form} name="supplier" label="Fornitore" required help="supplier" />
          <Field form={form} name="name" label="Nome offerta" required help="name" />
          <SelectField form={form} name="price_type" label="Tipo di prezzo" options={[['fixed', 'Fisso'], ['indexed', 'Indicizzato']]} required help="price_type" />
          <Field form={form} name="expires_on" label="Scadenza" type="date" help="expires_on" />
          <CheckField form={form} name="is_current" label="Offerta attuale" help="is_current" />
          <Group legend="Prezzo energia (€/kWh o €/Smc)">
            <Field form={form} name="price" label="Prezzo fisso" type="number" help="price" /><Field form={form} name="price_f1" label="Fisso F1 (luce)" type="number" help="price_f1" />
            <Field form={form} name="price_f2" label="Fisso F2 (luce)" type="number" help="price_f2" /><Field form={form} name="price_f3" label="Fisso F3 (luce)" type="number" help="price_f3" />
            <Field form={form} name="spread" label="Spread su PUN/PSV (indicizzato)" type="number" help="spread" /><Field form={form} name="avg_price" label="Prezzo medio (se non c'è formula)" type="number" help="avg_price" />
          </Group>
          <Group legend="Formula indicizzata">
            <Field form={form} name="loss_pct" label="Perdite di rete (%) – luce" type="number" help="loss_pct" /><Field form={form} name="dispatching" label="Dispacciamento (€/kWh) – luce" type="number" help="dispatching" />
            <Field form={form} name="capacity" label="Oneri di capacità (€/kWh) – luce" type="number" help="capacity" /><CheckField form={form} name="dispatching_extra" label="Dispacciamento/capacità fatturati a parte" help="dispatching_extra" />
            <Field form={form} name="gas_mgmt" label="Gestione variabile (€/Smc) – gas" type="number" help="gas_mgmt" /><Field form={form} name="pcs_adjustment" label="Adeguamento PCS (€/Smc) – gas" type="number" help="pcs_adjustment" />
          </Group>
          <Group legend="Quote fisse e sconti">
            <Field form={form} name="fixed_fee_month" label="Quota fissa (€/mese)" type="number" help="fixed_fee_month" /><Field form={form} name="power_fee_kw_month" label="Quota potenza (€/kW/mese)" type="number" help="power_fee_kw_month" />
            <Field form={form} name="one_off_discount" label="Sconti/bonus una tantum (€)" type="number" help="one_off_discount" /><Field form={form} name="source" label="Fonte" help="source" />
            <Field form={form} name="dual_with" label="Offerta luce+gas: fonte dell'altra metà" help="dual_with" /><Field form={form} name="zones" label="Zone di validità (vuoto = ovunque)" help="zones" />
          </Group>
          <Group legend="Durata e condizioni" hint={<Muted>Con durata e data di attivazione, se l'offerta è «attuale» ti avviso prima che finiscano le condizioni economiche.</Muted>}>
            <Field form={form} name="duration_months" label="Durata delle condizioni (mesi)" type="number" step="1" help="duration_months" /><Field form={form} name="started_on" label="Attivata il (offerta attuale)" type="date" help="started_on" />
            <AreaField form={form} name="conditions" label="Condizioni del venditore (una per riga)" help="conditions" /><AreaField form={form} name="after_term" label="Cosa cambia a fine periodo" help="after_term" />
          </Group>
        </FieldGrid>
        <div className="my-5 flex gap-3"><Button type="submit" busy={busy}>Salva</Button><LinkButton to="/offers" soft>Annulla</LinkButton></div>
      </form>
    </>
  );
}
