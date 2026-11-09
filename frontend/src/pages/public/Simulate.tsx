import { useRef, useState, type DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { FileUp, Flame, Zap } from 'lucide-react';
import { api, ApiError } from '../../lib/api';
import { commodityLabel, eur, num, unitOf } from '../../lib/format';
import type { Simulation } from '../../lib/types';
import { useAuth } from '../../context/AuthContext';
import AdSlot from '../../components/AdSlot';
import PublicShell from '../../components/public/PublicShell';
import { Card, Notice, VerdictBlock } from '../../components/ui';
import { FOCUS_RING, PRIMARY_BUTTON, SOFT_BUTTON } from '../../components/styles';

const iconBox = 'box-content h-[1.35rem] w-[1.35rem] rounded-full bg-accent-soft p-[.45rem] text-accent';
const day = (iso: string) => iso.split('-').reverse().join('/');

function Dropzone({ onFile, busy }: { onFile: (f: File) => void; busy: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const drop = (e: DragEvent) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); };
  return (
    <div onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={drop}
      className={`flex flex-col items-center gap-4 rounded-card border-2 border-dashed px-6 py-12 text-center transition-colors ${over ? 'border-accent bg-accent-soft' : 'border-line bg-surface'}`}>
      <FileUp className="box-content h-8 w-8 rounded-full bg-accent-soft p-3 text-accent" aria-hidden />
      <p className="m-0 max-w-[40ch] text-lg">Scegli il PDF della tua <strong>ultima bolletta</strong> di luce o gas.</p>
      <input ref={input} type="file" accept="application/pdf,.pdf" className="sr-only" aria-label="PDF della bolletta" tabIndex={-1}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ''; }} />
      <button type="button" disabled={busy} onClick={() => input.current?.click()} className={`${PRIMARY_BUTTON} min-h-[3.5rem] !rounded-full px-8 text-xl disabled:opacity-70`}>{busy ? 'Leggo la bolletta…' : 'Scegli il PDF'}</button>
      <p className="m-0 text-sm text-muted">Oppure trascinalo qui. Il file viene letto e subito scartato: non lo salviamo. <Link to="/privacy" className="font-bold text-accent underline underline-offset-4">Privacy</Link></p>
    </div>
  );
}

function Result({ sim, onAgain }: { sim: Simulation; onAgain: () => void }) {
  const { registrationOpen } = useAuth();
  const a = sim.analysis, c = a.consumption, v = a.verdict;
  const label = commodityLabel(sim.commodity), unit = unitOf(sim.commodity), index = sim.commodity === 'power' ? 'PUN' : 'PSV';
  return (
    <>
      <Card>
        <h2 className="mb-1 mt-3 flex items-center gap-2.5 text-2xl font-extrabold tracking-tight">
          {sim.commodity === 'power' ? <Zap className={iconBox} aria-hidden /> : <Flame className={iconBox} aria-hidden />}{label}
        </h2>
        <p className="m-0 mb-3 text-sm text-muted">
          Letto dalla bolletta{sim.bill.supplier ? ` di ${sim.bill.supplier}` : ''}: {day(sim.bill.period_start)} – {day(sim.bill.period_end)}
          {sim.bill.consumption != null && <> · {num(sim.bill.consumption, 0)} {unit}</>}{sim.bill.total_eur != null && <> · {eur(sim.bill.total_eur)}</>}
        </p>
        {c && <p className="m-0 mb-3">Consumo annuo stimato: <strong>{num(c.total, 0)} {unit}</strong></p>}
        {c?.partial && <Notice level="warn">Parto da una sola bolletta ({c.days_covered} giorni): il consumo annuo è una proiezione con un profilo stagionale tipico, quindi la stima è approssimativa.</Notice>}
        {v ? <>
          <VerdictBlock good={v.worthwhile} label={v.worthwhile ? 'Conviene cambiare' : 'Non conviene cambiare'} figure={`${eur(v.saving)} l'anno`}
            note={v.worthwhile ? `Risparmio stimato del ${num(v.saving_pct, 0)}%.` : `Risparmio massimo ${eur(v.saving)} l'anno (${num(v.saving_pct, 0)}%): troppo poco per cambiare.`} />
          <p>Migliore alternativa: <strong>{v.best.offer.name}</strong> – {v.best.offer.supplier}.<br />
            Costo annuo stimato <strong>{eur(v.best.estimate.total)}</strong> contro <strong>{eur(v.current.estimate.total)}</strong> con la tua offerta{sim.current_offer ? <> «{sim.current_offer.name}»</> : ''}.</p>
          {v.worthwhile && !v.robust && <Notice level="warn">Il vantaggio dipende dall'andamento del {index}: con l'indice ±20% il risparmio va da {eur(v.saving_range[0])} a {eur(v.saving_range[1])}.</Notice>}
        </> : <>
          <Notice>{sim.current_offer ? 'Non ci sono alternative da confrontare.' : "In questa bolletta non riconosco con certezza la tua offerta attuale, quindi non posso dirti quanto risparmieresti. Ecco intanto le più convenienti per il tuo consumo."}</Notice>
        </>}
        {sim.alternatives.length > 0 && <>
          <h3 className="mb-2 mt-5 text-lg font-bold">Le più convenienti per il tuo consumo</h3>
          <ul className="m-0 list-none divide-y divide-edge p-0">
            {sim.alternatives.map((r, i) => (
              <li key={`${r.offer.id}-${i}`} className="flex items-baseline justify-between gap-4 py-2.5">
                <span><strong>{r.offer.name}</strong><br /><span className="text-sm text-muted">{r.offer.supplier} · {r.offer.price_type === 'fixed' ? 'prezzo fisso' : 'indicizzato'}</span></span>
                <span className="whitespace-nowrap text-right font-bold tabular-nums">{eur(r.estimate.total)}<span className="block text-xs font-normal text-muted">l'anno</span></span>
              </li>))}
          </ul>
        </>}
        <p className="mb-3 mt-4 text-sm text-muted">Stima, non preventivo. Considero le {sim.catalog_size} offerte del catalogo valide in tutta Italia, con {index} medio assunto di {num(sim.commodity === 'power' ? (a.assumptions?.pun ?? 0) : (a.assumptions?.psv ?? 0), 3)} €/{unit}. Verifica le condizioni sul sito del venditore.</p>
      </Card>

      <AdSlot slot="simulation-result" />

      <Card className="border-accent/40">
        <h2 className="mb-1 mt-3 text-2xl font-extrabold tracking-tight">Vuoi una stima più precisa?</h2>
        <p className="mt-0 max-w-[56ch]">Con una sola bolletta posso solo proiettare. {registrationOpen ? 'Registrati' : 'Accedi'} e carica più bollette (ideale gli ultimi 12 mesi): uso i tuoi consumi reali, ricordo la tua offerta attuale, confronto luce e gas insieme e ti avviso prima che scada.</p>
        <div className="mb-3 flex flex-wrap items-center gap-3">
          {registrationOpen && <Link to="/registrati" className={`${PRIMARY_BUTTON} !rounded-full px-7`}>Registrati e carica altre bollette</Link>}
          <Link to="/accedi" className={registrationOpen ? SOFT_BUTTON : `${PRIMARY_BUTTON} !rounded-full px-7`}>{registrationOpen ? 'Ho già un account' : 'Accedi'}</Link>
          <button type="button" onClick={onAgain} className={`inline-flex min-h-[44px] items-center rounded font-bold text-accent underline-offset-4 hover:underline ${FOCUS_RING}`}>Prova un'altra bolletta</button>
        </div>
      </Card>
    </>
  );
}

export default function Simulate() {
  const [sim, setSim] = useState<Simulation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (file: File) => {
    setBusy(true); setError(null);
    const body = new FormData(); body.set('pdf', file);
    try { setSim(await api.post<Simulation>('/simulate', body)); window.scrollTo({ top: 0 }); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Qualcosa è andato storto: riprova.'); }
    finally { setBusy(false); }
  };

  return (
    <PublicShell title="La tua simulazione">
      <main className="mx-auto max-w-[44rem] px-4 pb-16 pt-8 lg:pt-12">
        <h1 className="mb-1 mt-0 text-4xl font-extrabold leading-tight tracking-tight text-accent-deep">{sim ? 'La tua simulazione' : 'Carica la tua ultima bolletta'}</h1>
        {!sim && <p className="mb-6 mt-1 max-w-[56ch] text-muted">Ti diciamo se conviene cambiare e di quanto. Nessun account, nessun dato da inserire.</p>}
        <div aria-live="polite">{error && <Notice level="warn">{error}</Notice>}</div>
        {sim ? <Result sim={sim} onAgain={() => { setSim(null); setError(null); }} /> : <Dropzone onFile={(f) => void run(f)} busy={busy} />}
      </main>
    </PublicShell>
  );
}
