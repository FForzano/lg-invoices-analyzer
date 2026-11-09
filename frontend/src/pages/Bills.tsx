import { useNavigate } from 'react-router-dom';
import { api, openPdf, type WithMessages } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import { eur, num, commodityLabel, unitOf } from '../lib/format';
import type { Bill, PageInfo } from '../lib/types';
import { useApp } from '../context/AppContext';
import { useConfirm } from '../context/ConfirmContext';
import AdSlot from '../components/AdSlot';
import { Actions, DangerLink, ErrorBox, H1, InfoButton, LinkButton, Loading, Pager, Scroll, usePage } from '../components/ui';
import { TEXT_BUTTON } from '../components/styles';

const th = 'px-3.5 py-2.5 text-left text-[.8rem] font-bold uppercase tracking-wide text-muted bg-calm whitespace-nowrap';
const td = 'px-3.5 py-2.5 border-b border-edge whitespace-nowrap';

export default function Bills() {
  const page = usePage();
  const { flash } = useApp();
  const confirm = useConfirm();
  const { run } = useAction();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useQuery<{ items: Bill[]; page: PageInfo }>('/bills', { page });

  const remove = async (b: Bill) => {
    if (!(await confirm({ title: 'Eliminare la bolletta?', message: `${commodityLabel(b.commodity)} dal ${b.period_start} al ${b.period_end}. L'azione non si può annullare.` }))) return;
    await run(async () => { await api.del(`/bills/${b.id}`); reload(); });
  };
  const detect = (b: Bill) => run(async () => { const r = await api.post<WithMessages>(`/bills/${b.id}/detect-offer`); flash(r.messages); navigate('/'); });

  return (
    <>
      <H1>Bollette</H1>
      <Actions>
        <LinkButton to="/bills/new?commodity=power" soft>+ Luce</LinkButton>
        <LinkButton to="/bills/new?commodity=gas" soft>+ Gas</LinkButton>
        <LinkButton to="/layouts" soft>Layout di lettura</LinkButton>
      </Actions>
      {loading && !data ? <Loading /> : error || !data ? <ErrorBox error={error!} /> : <>
        <Scroll><table className="w-full">
          <thead><tr><th className={th}>Fornitura</th><th className={th}>Periodo</th><th className={`${th} text-right`}>Consumo<InfoButton term="t_consumption" /></th>
            <th className={th}>Lettura<InfoButton term="t_reading" /></th><th className={`${th} text-right`}>Totale<InfoButton term="total_eur" /></th><th className={th} /></tr></thead>
          <tbody>{data.items.map((b) => (
            <tr key={b.id} className="hover:bg-calm">
              <td className={td}>{commodityLabel(b.commodity)}</td><td className={td}>{b.period_start} → {b.period_end}</td>
              <td className={`${td} text-right`}>{num(b.consumption)} {unitOf(b.commodity)}</td><td className={td}>{b.reading_type ?? '–'}</td>
              <td className={`${td} text-right`}>{b.total_eur != null ? eur(b.total_eur) : '–'}</td>
              <td className={`${td} flex items-center gap-4`}>
                {b.pdf_path && <><button type="button" className={TEXT_BUTTON} onClick={() => void run(() => openPdf(`/bills/${b.id}/pdf`))}>PDF</button>
                  <button type="button" className={TEXT_BUTTON} title="Imposta come offerta attuale quella descritta in questa bolletta" onClick={() => void detect(b)}>usa come offerta attuale</button></>}
                <DangerLink onClick={() => void remove(b)}>elimina</DangerLink>
              </td>
            </tr>))}
            {!data.items.length && <tr><td colSpan={6} className={`${td} text-muted`}>Nessuna bolletta.</td></tr>}
          </tbody></table></Scroll>
        <Pager page={data.page} />
        <AdSlot slot="bills-list" />
      </>}
    </>
  );
}
