import { useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { BarController, BarElement, CategoryScale, Chart, LineController, LineElement, LinearScale, PointElement, Tooltip } from 'chart.js';
import { useQuery } from '../lib/useQuery';
import { eur, num, pctSigned } from '../lib/format';
import type { ChartData, HistoryRow } from '../lib/types';
import { ErrorBox, H1, H2, InfoButton, Loading, Muted, Notice, Scroll, Tabs, Tag } from '../components/ui';

Chart.register(BarController, BarElement, CategoryScale, LinearScale, LineController, LineElement, PointElement, Tooltip);
const TABS = [{ to: '/history/power', label: 'Luce' }, { to: '/history/gas', label: 'Gas' }];
const th = 'px-3.5 py-2.5 text-left text-[.8rem] font-bold uppercase tracking-wide text-muted bg-calm whitespace-nowrap';
const td = 'px-3.5 py-2.5 border-b border-edge whitespace-nowrap';
const MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];

/** Una serie per grafico, nel colore accento (dati, non decorazione); barre più chiare = lettura stimata. I colori vengono dai token CSS. */
function SeriesChart({ title, type, data, labels, estimated, decimals }: { title: string; type: 'bar' | 'line'; data: (number | null)[]; labels: string[]; estimated: boolean[]; decimals: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const css = getComputedStyle(document.documentElement);
    const accent = css.getPropertyValue('--accent').trim(), line = css.getPropertyValue('--edge').trim(), muted = css.getPropertyValue('--muted').trim();
    Chart.defaults.font.family = 'Figtree, system-ui, sans-serif'; Chart.defaults.color = muted;
    const fmt = (d: number) => new Intl.NumberFormat('it-IT', { minimumFractionDigits: d, maximumFractionDigits: d });
    const chart = new Chart(canvas.current!, {
      type,
      data: { labels: labels.map((l) => `${MONTHS[+l.slice(5) - 1]} ${l.slice(2, 4)}`),
        datasets: [{ data, borderColor: accent, borderWidth: 2, pointRadius: 4, pointBackgroundColor: accent, borderRadius: 4, backgroundColor: data.map((_, i) => (estimated[i] ? accent + '66' : accent)) }] },
      options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => fmt(decimals).format(c.parsed.y ?? 0) + (estimated[c.dataIndex] ? ' (stimata)' : '') } } },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } }, y: { beginAtZero: true, grid: { color: line }, border: { display: false }, ticks: { maxTicksLimit: 6, callback: (v) => new Intl.NumberFormat('it-IT', { maximumFractionDigits: 3 }).format(Number(v)) } } } },
    });
    return () => chart.destroy();
  }, [type, data, labels, estimated, decimals]);
  return (
    <figure className="m-0 min-w-0 rounded-card border border-edge bg-surface px-5 pb-4 pt-3 shadow-panel">
      <figcaption className="mb-2 font-bold">{title}</figcaption>
      <div className="relative h-56"><canvas ref={canvas} role="img" aria-label={`${title}: tabella con gli stessi dati qui sotto`} /></div>
    </figure>
  );
}

export default function History() {
  const { commodity = 'power' } = useParams();
  const { data, error, loading } = useQuery<{ unit: string; rows: HistoryRow[]; chart: ChartData }>(`/history/${commodity}`);
  const title = <H1>Storico {commodity === 'power' ? 'luce' : 'gas'}</H1>;
  if (loading && !data) return <>{title}<Tabs items={TABS} /><Loading /></>;
  if (error || !data) return <>{title}<Tabs items={TABS} /><ErrorBox error={error!} /></>;
  const { unit, rows, chart } = data;
  const delta = (x: number | null) => { const t = pctSigned(x); return t === null ? '–' : <span className={x! > 0 ? 'text-bad' : 'text-good'}>{t}</span>; };
  return (
    <>
      {title}<Tabs items={TABS} />
      {rows.length > 1 && <>
        <section className="mb-4 grid gap-4" aria-label="Grafici dello storico">
          <SeriesChart title={`Consumo per bolletta (${unit})`} type="bar" data={chart.consumption} labels={chart.labels} estimated={chart.estimated} decimals={0} />
          <SeriesChart title="Spesa per bolletta (€)" type="bar" data={chart.total} labels={chart.labels} estimated={chart.estimated} decimals={2} />
          <SeriesChart title={`Costo medio (€/${unit})`} type="line" data={chart.unit_cost} labels={chart.labels} estimated={chart.estimated} decimals={3} />
          <Muted>Barre più chiare: lettura stimata. Spesa e costo medio includono trasporto, imposte e canone TV.</Muted>
        </section>
        <H2>Dettaglio bollette</H2>
      </>}
      <Scroll><table className="w-full">
        <thead><tr><th className={th}>Periodo</th><th className={`${th} text-right`}>Consumo ({unit})<InfoButton term="t_consumption" /></th><th className={`${th} text-right`}>vs anno prima<InfoButton term="t_vs_prev" /></th>
          <th className={`${th} text-right`}>Costo medio (€/{unit})<InfoButton term="t_avg_cost" /></th><th className={`${th} text-right`}>vs anno prima<InfoButton term="t_vs_prev" /></th><th className={th}>Lettura<InfoButton term="t_reading" /></th><th className={`${th} text-right`}>Totale</th></tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.bill.id} className="hover:bg-calm">
            <td className={td}>{r.bill.period_start} → {r.bill.period_end}</td><td className={`${td} text-right`}>{num(r.bill.consumption)}</td><td className={`${td} text-right`}>{delta(r.consumption_yoy)}</td>
            <td className={`${td} text-right`}>{num(r.unit_cost, 3)}</td><td className={`${td} text-right`}>{delta(r.unit_cost_yoy)}</td>
            <td className={td}>{r.bill.reading_type === 'stimata' ? <Tag kind="warn">stimata</Tag> : r.bill.reading_type || '–'}</td><td className={`${td} text-right`}>{eur(r.bill.total_eur)}</td>
          </tr>))}
          {!rows.length && <tr><td colSpan={7} className={`${td} text-muted`}>Nessuna bolletta.</td></tr>}
        </tbody></table></Scroll>
      <Muted>Il costo medio è il totale in bolletta diviso il consumo: include trasporto, imposte e voci come il canone TV.</Muted>
      {rows.some((r) => r.bill.reading_type === 'stimata') && <Notice>Alcune letture sono stimate: fai l'autolettura dal 1 al 5 del mese.</Notice>}
    </>
  );
}
