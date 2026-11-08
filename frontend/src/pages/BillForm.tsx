import { useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { api, type WithMessages } from '../lib/api';
import { useAction } from '../lib/useAction';
import type { Prefill } from '../lib/types';
import { useApp } from '../context/AppContext';
import { Button, Field, FieldGrid, GroupTitle, H1, LinkButton, Muted, Notice, SelectField, useForm } from '../components/ui';
import { fieldClass } from '../components/styles';

const COMMODITIES: [string, string][] = [['power', 'Luce'], ['gas', 'Gas']];

export default function BillForm() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { flash, canExtract } = useApp();
  const { run, busy } = useAction();
  const passed = (useLocation().state as { prefill?: Prefill } | null)?.prefill;  // arriva da «Insegna»: bolletta riletta col nuovo layout
  const form = useForm<Record<string, unknown>>(passed?.values ?? { commodity: params.get('commodity') === 'gas' ? 'gas' : 'power' });
  const [teachPdf, setTeachPdf] = useState<string | null>(passed?.teach_pdf ?? null);
  const file = useRef<HTMLInputElement>(null);
  const [uploadCommodity, setUploadCommodity] = useState(String(form.values.commodity));
  const v = form.values;
  const power = v.commodity !== 'gas';
  const hasPdf = Boolean(v.pdf_path);

  const upload = (e: FormEvent) => {
    e.preventDefault();
    const files = file.current?.files;
    if (!files?.length) return;
    const body = new FormData();
    body.set('commodity', uploadCommodity);
    [...files].forEach((f) => body.append('pdf', f));
    void run(async () => {
      const r = await api.post<{ prefill?: Prefill; bulk?: { imported: number; messages: WithMessages['messages'] } }>('/bills/upload', body);
      if (r.prefill) { form.reset(r.prefill.values); setTeachPdf(r.prefill.teach_pdf); flash(r.prefill.messages); }
      else if (r.bulk) { flash(r.bulk.messages); if (r.bulk.imported) navigate('/'); }
    });
  };
  const save = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const r = await api.post<WithMessages>('/bills', v);
      flash(r.messages);
      navigate(v.pdf_path ? '/' : '/bills');
    });
  };

  return (
    <>
      <H1>Nuova bolletta</H1>
      {teachPdf && <Notice>Questo formato di bolletta non è ancora riconosciuto. <Link className="font-bold text-accent underline" to={`/layouts/teach?pdf=${teachPdf}`}>Insegna all'app a leggerlo</Link>: indichi dove sono i dati una volta sola e le prossime bollette dello stesso fornitore si leggeranno da sole.</Notice>}
      {!hasPdf && (
        <fieldset className="my-4 rounded-card border border-edge bg-surface px-4 pb-4 pt-2 shadow-panel">
          <legend className="px-1 font-bold">Da PDF, consigliato <span className="text-sm font-normal text-muted">(lettura locale a regole{canExtract ? ', con LLM come ripiego' : ''})</span></legend>
          <form onSubmit={upload}>
            <FieldGrid>
              <div><label className="flex flex-col gap-1 text-sm font-medium">Fornitura
                <select value={uploadCommodity} onChange={(e) => setUploadCommodity(e.target.value)} className={fieldClass}>{COMMODITIES.map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select></label></div>
              <div><label className="flex flex-col gap-1 text-sm font-medium">PDF (anche più di uno)
                <input ref={file} type="file" accept="application/pdf" multiple required className={`${fieldClass} file:mr-3 file:rounded-block file:border-0 file:bg-accent-soft file:px-3 file:py-1 file:font-bold file:text-accent`} /></label></div>
              <div className="flex items-end"><Button type="submit" busy={busy}>{busy ? 'Lettura in corso…' : 'Carica e leggi'}</Button></div>
            </FieldGrid>
          </form>
          <Muted className="mt-2">Con più PDF la fornitura è riconosciuta dal testo e le bollette lette per intero vengono salvate subito; le altre sono segnalate e vanno inserite una per una. Già presenti (stessa fornitura e periodo) = saltate.</Muted>
          {canExtract && <Muted>Solo se la lettura locale non basta, il testo della bolletta (dati personali) viene inviato all'API del modello.</Muted>}
        </fieldset>
      )}
      <form onSubmit={save}>
        <FieldGrid>
          <GroupTitle>Bolletta</GroupTitle>
          <SelectField form={form} name="commodity" label="Fornitura" options={COMMODITIES} required />
          <Field form={form} name="supplier" label="Fornitore" />
          <Field form={form} name="period_start" label="Inizio periodo" type="date" required />
          <Field form={form} name="period_end" label="Fine periodo" type="date" required />
          <SelectField form={form} name="reading_type" label="Tipo di lettura" options={[['effettiva', 'Effettiva'], ['stimata', 'Stimata']]} />
          <Field form={form} name="total_eur" label="Totale da pagare (€)" type="number" />
          <GroupTitle>Consumi</GroupTitle>
          {power ? <><Field form={form} name="kwh_f1" label="kWh F1" type="number" /><Field form={form} name="kwh_f2" label="kWh F2" type="number" /><Field form={form} name="kwh_f3" label="kWh F3" type="number" /></>
            : <><Field form={form} name="mc" label="Metri cubi (mc)" type="number" /><Field form={form} name="coeff_c" label="Coefficiente C" type="number" /></>}
          <Field form={form} name="consumption" label="Consumo fatturato (kWh o Smc)" type="number" />
          {power && <><GroupTitle>Potenza</GroupTitle>
            <Field form={form} name="power_kw" label="Potenza impegnata (kW)" type="number" />
            <Field form={form} name="max_power_kw" label="Picco di potenza del mese (kW)" type="number" />
            <Field form={form} name="annual_max_power_kw" label="Picco di potenza ultimi 12 mesi (kW)" type="number" />
            <Field form={form} name="power_rate_kw_month" label="Quota potenza (€/kW/mese)" type="number" /></>}
          <GroupTitle>Dati annui stampati in bolletta</GroupTitle>
          {power && <><Field form={form} name="annual_f1" label="Annuo F1 (kWh)" type="number" /><Field form={form} name="annual_f2" label="Annuo F2 (kWh)" type="number" /><Field form={form} name="annual_f3" label="Annuo F3 (kWh)" type="number" /></>}
          <Field form={form} name="annual_consumption" label="Consumo annuo in bolletta" type="number" />
          <Field form={form} name="annual_spend" label="Spesa annua in bolletta (€)" type="number" />
          <Field form={form} name="social_bonus_expires_on" label="Scadenza bonus sociale" type="date" />
        </FieldGrid>
        <div className="my-5 flex flex-wrap items-center gap-3">
          <Button type="submit" busy={busy}>Salva</Button>
          <LinkButton to="/bills" soft>Annulla</LinkButton>
          <span className="text-sm text-muted">Se lasci vuoto il consumo fatturato viene ricavato da fasce o mc × C.</span>
        </div>
      </form>
    </>
  );
}
