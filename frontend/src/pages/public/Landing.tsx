import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Landmark, Lock, Upload } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import PublicShell from '../../components/public/PublicShell';
import Reveal from '../../components/public/Reveal';
import { MockBill, MockRank, MockRead, MockVerdict } from '../../components/public/Mocks';
import { FOCUS_RING, PRIMARY_BUTTON, SOFT_BUTTON } from '../../components/styles';

const STEPS: { title: string; text: ReactNode; visual: ReactNode }[] = [
  { title: 'Carichi la bolletta', visual: <MockBill />,
    text: <>Il PDF di luce o gas, così come lo scarichi dall'area clienti del tuo fornitore. Basta il file digitale, non serve la scansione. Ti basta <strong>l'ultima</strong>.</> },
  { title: "L'app la legge", visual: <MockRead />,
    text: <>Periodo, consumo, totale e offerta che hai oggi vengono letti dal testo del PDF. Se vedi un valore sbagliato lo correggi: nessuna sorpresa, nessun modulo da compilare.</> },
  { title: 'Confronta le offerte', visual: <MockRank />,
    text: <>Le offerte pubbliche del Portale Offerte vengono stimate sul <strong>tuo</strong> consumo annuo. Per quelle a prezzo indicizzato si assume un PUN/PSV medio e si prova anche con ±20%.</> },
  { title: 'Ricevi il consiglio giusto', visual: <MockVerdict />,
    text: <>Ti diciamo se <strong>conviene cambiare</strong> e di quanto, oppure che non ne vale la pena. Il verdetto positivo arriva solo se il risparmio supera una soglia: meglio un «no» onesto che un cambio inutile.</> },
];

function Step({ n, title, text, visual, flip }: { n: number; title: string; text: ReactNode; visual: ReactNode; flip: boolean }) {
  return (
    <Reveal>
      <li className={`grid list-none items-center gap-6 md:grid-cols-2 md:gap-14 ${flip ? 'md:[&>*:first-child]:order-2' : ''}`}>
        <div>
          <p className="mb-3 flex items-center gap-3 text-sm font-bold uppercase tracking-wider text-muted">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-accent text-base text-on-accent" aria-hidden>{n}</span>Passo {n} di {STEPS.length}
          </p>
          <h3 className="m-0 text-3xl font-extrabold leading-tight tracking-tight text-fg md:text-4xl">{title}</h3>
          <p className="mt-3 max-w-[46ch] text-lg text-muted">{text}</p>
        </div>
        <div className="flex justify-center md:justify-start md:[&:nth-child(2)]:justify-center">{visual}</div>
      </li>
    </Reveal>
  );
}

export default function Landing() {
  const { registrationOpen, demo } = useAuth();
  return (
    <PublicShell>
      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-12 lg:grid-cols-[1.1fr_1fr] lg:gap-16 lg:px-8 lg:py-20" aria-label="Introduzione">
          <div>
            <h1 className="m-0 text-4xl font-extrabold leading-[1.05] tracking-tight text-fg sm:text-5xl lg:text-6xl">
              Scopri se <span className="text-accent">conviene cambiare</span> luce e gas
            </h1>
            <p className="mt-5 max-w-[42ch] text-xl text-muted">Carica la tua ultima bolletta: in pochi secondi ti diciamo se esiste un'offerta migliore e quanto risparmieresti in un anno.</p>
            {demo ? (
              <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
                <Link to="/simulazione" className={`${PRIMARY_BUTTON} min-h-[3.5rem] gap-3 !rounded-full px-8 text-xl shadow-lift`}><Upload className="h-6 w-6" aria-hidden />Carica la tua ultima bolletta</Link>
                <Link to="/accedi" className={`inline-flex min-h-[44px] items-center gap-1.5 rounded font-bold text-accent no-underline hover:underline ${FOCUS_RING}`}>Ho già un account<ArrowRight className="h-4 w-4" aria-hidden /></Link>
              </div>
            ) : (
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/accedi" className={`${PRIMARY_BUTTON} min-h-[3.5rem] !rounded-full px-8 text-xl`}>Accedi</Link>
                {registrationOpen && <Link to="/registrati" className={`${SOFT_BUTTON} min-h-[3.5rem] !rounded-full px-8 text-xl`}>Registrati</Link>}
              </div>
            )}
            {demo && <p className="mt-4 flex items-center gap-2 text-sm text-muted"><Lock className="h-4 w-4 flex-none" aria-hidden />Gratis, senza registrazione. Il PDF viene letto e subito scartato: non lo salviamo.</p>}
          </div>
          <Reveal className="flex justify-center lg:justify-end"><MockVerdict /></Reveal>
        </section>

        <section className="border-y border-edge bg-surface" aria-labelledby="come-funziona">
          <div className="mx-auto max-w-6xl px-4 py-14 lg:px-8 lg:py-20">
            <h2 id="come-funziona" className="m-0 mb-12 text-center text-3xl font-extrabold tracking-tight text-fg md:text-5xl">Dalla bolletta al consiglio, <span className="text-accent">in quattro passi</span></h2>
            <ol className="m-0 flex list-none flex-col gap-14 p-0 md:gap-20">
              {STEPS.map((s, i) => <Step key={s.title} n={i + 1} flip={i % 2 === 1} {...s} />)}
            </ol>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-14 lg:px-8" aria-label="Perché fidarti">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              [Lock, 'Il tuo PDF non resta qui', 'Nella simulazione viene letto in memoria e scartato. Con un account lo conservi tu, per i tuoi confronti.'],
              [Landmark, 'Solo dati pubblici', "Le offerte sono quelle ufficiali del Portale Offerte: niente classifiche pagate, nessun fornitore dietro l'app."],
              [ArrowRight, 'Stima onesta', 'Con una sola bolletta il consumo annuo è una proiezione e te lo diciamo. Con più bollette il confronto diventa preciso.'],
            ].map(([Icon, title, text]) => {
              const I = Icon as typeof Lock;
              return <Reveal key={title as string}><div className="h-full rounded-card border border-edge bg-surface p-6 shadow-panel"><I className="mb-3 box-content h-6 w-6 rounded-full bg-accent-soft p-2 text-accent" aria-hidden /><h3 className="m-0 mb-1 text-xl font-bold">{title as string}</h3><p className="m-0 text-muted">{text as string}</p></div></Reveal>;
            })}
          </div>
        </section>

        {demo && (
          <section className="mx-auto max-w-6xl px-4 pb-20 lg:px-8" aria-label="Inizia">
            <Reveal>
              <div className="rounded-card bg-accent px-6 py-10 text-center text-on-accent shadow-panel md:px-12">
                <h2 className="m-0 text-3xl font-extrabold tracking-tight md:text-4xl">Provalo con la tua ultima bolletta</h2>
                <p className="mx-auto mb-6 mt-2 max-w-[48ch] text-lg opacity-90">Ci vogliono pochi secondi, senza registrarti.</p>
                <Link to="/simulazione" className={`inline-flex min-h-[3.5rem] items-center gap-3 rounded-full bg-surface px-8 text-xl font-bold text-accent-deep no-underline shadow-lift hover:bg-accent-soft ${FOCUS_RING} focus-visible:ring-offset-accent`}><Upload className="h-6 w-6" aria-hidden />Carica la tua ultima bolletta</Link>
              </div>
            </Reveal>
          </section>
        )}
      </main>
    </PublicShell>
  );
}
