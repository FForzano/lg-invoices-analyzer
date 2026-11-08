import { useEffect, type FormEvent } from 'react';
import { api, type WithMessages } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import { num } from '../lib/format';
import type { Settings as SettingsT } from '../lib/types';
import { useApp } from '../context/AppContext';
import { Button, Card, ErrorBox, Field, FieldGrid, GroupTitle, H1, InfoButton, Loading, Muted, SoftButton, useForm } from '../components/ui';

export default function Settings() {
  const { profile, flash } = useApp();
  const { data, error, loading, reload } = useQuery<{ settings: SettingsT }>('/settings');
  const form = useForm<Record<string, unknown>>({});
  const { run, busy } = useAction();
  useEffect(() => { if (data) form.reset(data.settings); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [data]);
  const save = (e: FormEvent) => { e.preventDefault(); void run(async () => { const r = await api.put<WithMessages>('/settings', form.values); flash(r.messages); reload(); }); };
  const useRecent = () => run(async () => { const r = await api.post<WithMessages>('/settings/use-recent'); flash(r.messages); reload(); });
  if (loading && !data) return <><H1>Impostazioni</H1><Loading /></>;
  if (error || !data) return <><H1>Impostazioni</H1><ErrorBox error={error!} /></>;
  const s = data.settings;
  return (
    <>
      <H1>Impostazioni</H1>
      <Muted>PUN<InfoButton term="pun" />, PSV<InfoButton term="psv" />, perdite e dispacciamento valgono per tutti i profili. Potenza di default e località sono del profilo <strong>{profile.name}</strong>.</Muted>
      <form onSubmit={save}>
        <FieldGrid>
          <GroupTitle>Prezzi assunti per le offerte indicizzate</GroupTitle>
          <Field form={form} name="pun" label="PUN medio annuo assunto (€/kWh)" type="number" />
          <Field form={form} name="psv" label="PSV medio annuo assunto (€/Smc)" type="number" />
          <Field form={form} name="loss_pct" label="Perdite di rete assunte (%)" type="number" help="loss_pct_setting" />
          <Field form={form} name="dispatching_extra" label="Dispacciamento + capacità a parte (€/kWh)" type="number" help="dispatching_extra_cost" />
          <Muted className="col-span-full">PUN e PSV sono medie annue assunte per stimare le offerte indicizzate (il valore futuro non è noto). Il confronto le adatta ai mesi in cui consumi (il gas soprattutto d'inverno) con la stagionalità storica; si aggiorna con «Aggiorna dal Portale Offerte».</Muted>
          <GroupTitle>Profilo {profile.name}: potenza e località</GroupTitle>
          <Field form={form} name="default_power_kw" label="Potenza di default (kW)" type="number" />
          <Field form={form} name="region" label="Regione (ISTAT, es. 08)" />
          <Field form={form} name="province" label="Provincia (ISTAT, es. 038)" />
          <Field form={form} name="comune" label="Comune (ISTAT, es. 038008)" />
          <Muted className="col-span-full">Le offerte limitate a certe zone compaiono nel confronto solo se coprono questa regione, provincia o comune. Codici su <a className="font-bold text-accent underline" href="https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/" target="_blank" rel="noopener noreferrer">istat.it</a>.</Muted>
        </FieldGrid>
        <div className="my-5"><Button type="submit" busy={busy}>Salva</Button></div>
      </form>
      {s.pun_recent !== undefined && (
        <Card>
          <h2 className="mb-2 mt-3 text-xl font-bold">Prezzi recenti dal Portale Offerte</h2>
          <p>Fino a {String(s.recent_until)}, media degli ultimi 3 mesi destagionalizzata: <strong>PUN {num(s.pun_recent as number, 3)} €/kWh</strong>, <strong>PSV {num(s.psv_recent as number, 3)} €/Smc</strong>.</p>
          <div className="my-3"><SoftButton busy={busy} onClick={() => void useRecent()}>Usa questi valori</SoftButton></div>
          <Muted>Sono più freschi del mese in bolletta ma estrapolano il trend recente: se i prezzi rientrano, le offerte indicizzate costeranno meno di quanto stimato.</Muted>
        </Card>
      )}
    </>
  );
}
