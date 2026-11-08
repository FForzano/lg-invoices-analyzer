import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import * as pdfjs from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { api, ApiError, fetchPdfData } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import type { Prefill, TeachInfo } from '../lib/types';
import { useApp } from '../context/AppContext';
import { Button, ErrorBox, H1, Loading, Muted, Notice, SoftButton } from '../components/ui';
import { fieldClass, SOFT_BUTTON } from '../components/styles';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

// Valori riquadrati: numeri e date sono cliccabili; per i campi a scelta (luce/gas, effettiva/stimata) basta toccare la riga.
const DATE = /\d{1,2}[/.-]\d{1,2}[/.-]\d{4}/g;
const NUMBER = /(?<![\w.,/-])(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)(?![\w/])(?![.,]\d)/g;
const GUESS: [RegExp, string][] = [[/elettric|luce/i, 'power'], [/\bgas\b/i, 'gas'], [/effettiv/i, 'effettiva'], [/stimat/i, 'stimata']];

function markCandidates(layer: HTMLElement) {
  layer.querySelectorAll('span').forEach((span) => {
    const text = span.textContent ?? '';
    const parts: { start: number; end: number; cls: string }[] = [];
    for (const [re, cls] of [[DATE, 'date'], [NUMBER, 'num']] as const)
      for (const m of text.matchAll(re)) {
        const start = m.index!, end = start + m[0].length;
        if (!parts.some((p) => start < p.end && end > p.start)) parts.push({ start, end, cls });
      }
    if (!parts.length) return;
    parts.sort((a, b) => a.start - b.start);
    const frag = document.createDocumentFragment();
    let pos = 0;
    for (const p of parts) {
      frag.append(text.slice(pos, p.start));
      const mark = document.createElement('mark');
      mark.className = `cand ${p.cls}`; mark.textContent = text.slice(p.start, p.end);
      frag.append(mark); pos = p.end;
    }
    frag.append(text.slice(pos));
    span.replaceChildren(frag);
  });
}

export default function Teach() {
  const [params] = useSearchParams();
  const pdf = params.get('pdf');
  const { data, error, loading } = useQuery<TeachInfo>('/layouts/teach', { pdf: pdf ?? undefined });
  if (!pdf) return <ErrorBox error={new Error('Manca il PDF da cui insegnare.')} />;
  if (loading && !data) return <><H1>Insegna a leggere la bolletta</H1><Loading /></>;
  if (error || !data) return <><H1>Insegna a leggere la bolletta</H1><ErrorBox error={error!} /></>;
  return <TeachForm info={data} />;
}

function TeachForm({ info }: { info: TeachInfo }) {
  const navigate = useNavigate();
  const { flash } = useApp();
  const { run, busy } = useAction();
  const required = useMemo(() => new Set(info.required), [info.required]);
  const fields = useMemo(() => Object.entries(info.kinds), [info.kinds]);
  const main = fields.filter(([f]) => required.has(f) || f === 'supplier');
  const extra = fields.filter(([f]) => !required.has(f) && f !== 'supplier');

  const [values, setValues] = useState<Record<string, string>>(() => ({ ...info.samples }));
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [skipped, setSkipped] = useState<Set<string>>(new Set());
  const [signature, setSignature] = useState(info.supplier);
  const [name, setName] = useState(info.supplier);
  const [errors, setErrors] = useState(info.errors);
  const [active, setActive] = useState<string | null>(null);
  const [pdfOk, setPdfOk] = useState<boolean | null>(null);
  const [showText, setShowText] = useState(true);
  const pages = useRef<HTMLDivElement>(null);
  const src = useRef<HTMLPreElement>(null);
  const activeRef = useRef<string | null>(null);
  const last = useRef('');

  const pending = useCallback((vals: Record<string, string>, skip: Set<string>) =>
    fields.map(([f]) => f).filter((f) => required.has(f) && !(f in info.found) && !skip.has(f) && !vals[f]), [fields, required, info.found]);
  const advance = useCallback((vals: Record<string, string>, skip: Set<string>) => { const n = pending(vals, skip)[0] ?? null; activeRef.current = n; setActive(n); }, [pending]);
  useEffect(() => { advance(values, skipped); /* solo all'apertura */ // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const choose = (f: string) => { activeRef.current = f; setActive(f); };

  // `fill` legge sempre lo stato più recente tramite ref: i listener del PDF vivono fuori da React.
  const state = useRef({ values, skipped, choices });
  state.current = { values, skipped, choices };
  const fill = useCallback((text: string) => {
    const f = activeRef.current;
    if (!f) return;
    const vals = { ...state.current.values, [f]: text };
    setValues(vals);
    if (info.kinds[f] === 'keyword') {
      const g = GUESS.find(([re, v]) => re.test(text) && info.choices[f]?.includes(v));
      if (g) setChoices((c) => ({ ...c, [f]: g[1] }));
    }
    advance(vals, state.current.skipped);
  }, [advance, info.kinds, info.choices]);

  const kind = active ? info.kinds[active] : '';

  // PDF: pagine disegnate su canvas, con il livello di testo sopra per cliccare i valori
  useEffect(() => {
    let cancelled = false;
    const host = pages.current!;
    (async () => {
      try {
        const doc = await pdfjs.getDocument({ data: new Uint8Array(await fetchPdfData(`/layouts/pdf/${info.pdf}`)) }).promise;
        if (cancelled) return;
        host.replaceChildren();
        const width = host.clientWidth - 2;
        for (let n = 1; n <= doc.numPages; n++) {
          const page = await doc.getPage(n);
          const viewport = page.getViewport({ scale: width / page.getViewport({ scale: 1 }).width });
          const box = document.createElement('div');
          box.className = 'pdf-page';
          box.style.cssText = `width:${viewport.width}px;height:${viewport.height}px;--scale-factor:${viewport.scale};--total-scale-factor:${viewport.scale}`;
          const canvas = document.createElement('canvas'), ratio = window.devicePixelRatio || 1;
          canvas.width = viewport.width * ratio; canvas.height = viewport.height * ratio;
          canvas.style.cssText = `width:${viewport.width}px;height:${viewport.height}px`;
          const text = document.createElement('div');
          text.className = 'textLayer';
          box.append(canvas, text); host.append(box);
          await page.render({ canvas, canvasContext: canvas.getContext('2d')!, viewport, transform: [ratio, 0, 0, ratio, 0, 0] }).promise;
          await new pdfjs.TextLayer({ textContentSource: page.streamTextContent(), container: text, viewport }).render();
          markCandidates(text);
        }
        if (!cancelled) { setPdfOk(true); setShowText(false); }
      } catch { if (!cancelled) setPdfOk(false); }  // il testo sotto resta disponibile
    })();
    return () => { cancelled = true; };
  }, [info.pdf]);

  useEffect(() => {
    const host = pages.current;
    if (!host) return;
    const onClick = (e: MouseEvent) => {
      if (window.getSelection()?.toString().trim()) return;  // sta selezionando a mano
      const k = activeRef.current ? info.kinds[activeRef.current] : '';
      const el = e.target as HTMLElement;
      const cand = el.closest('.cand');
      if (cand && (k === 'date' ? cand.classList.contains('date') : k === 'number' && cand.classList.contains('num'))) fill(cand.textContent ?? '');
      else if (k === 'keyword' || k === 'text') { const s = el.closest('.textLayer span'); if (s) fill((s.textContent ?? '').replace(/\s+/g, ' ').trim()); }
    };
    host.addEventListener('click', onClick);
    let timer: number;
    const onSel = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {  // aspetta che la selezione sia finita
        const s = window.getSelection(), t = (s?.toString() ?? '').replace(/\s+/g, ' ').trim();
        const inArea = s?.anchorNode && (host.contains(s.anchorNode) || src.current?.contains(s.anchorNode));
        if (t && inArea && t !== last.current) { last.current = t; fill(t); }
      }, 350);
    };
    document.addEventListener('selectionchange', onSel);
    return () => { host.removeEventListener('click', onClick); document.removeEventListener('selectionchange', onSel); window.clearTimeout(timer); };
  }, [fill, info.kinds]);

  const save = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      try {
        const r = await api.post<{ prefill: Prefill }>('/layouts/teach', { pdf: info.pdf, name, signature, values, choices });
        flash(r.prefill.messages);
        navigate('/bills/new', { state: { prefill: r.prefill } });
      } catch (err) {
        if (err instanceof ApiError && err.data?.errors) { setErrors(err.data.errors); window.scrollTo({ top: 0 }); return; }
        throw err;
      }
    });
  };

  const row = ([f, k]: [string, string]) => (
    <div key={f} onFocusCapture={() => choose(f)} className={`rounded-field p-2 ${active === f ? 'bg-accent-soft ring-2 ring-accent' : ''}`}>
      <label className="flex flex-col gap-1 text-sm font-medium">
        <span>{info.help[f] ?? f}{required.has(f) ? ' *' : ''}{f in info.found && <span className="ml-2 font-normal text-muted">già letto: {info.found[f]}</span>}</span>
        <span className="flex flex-wrap gap-1.5">
          <input name={`v_${f}`} value={values[f] ?? ''} autoComplete="off" onChange={(e) => setValues((v) => ({ ...v, [f]: e.target.value }))}
            placeholder={k === 'keyword' ? 'testo che compare nella bolletta' : 'valore come appare'} className={`${fieldClass} min-w-0 flex-1 basis-40`} />
          {k === 'keyword' && <select aria-label="Valore corrispondente" value={choices[f] ?? info.choices[f]?.[0] ?? ''} onChange={(e) => setChoices((c) => ({ ...c, [f]: e.target.value }))} className={`${fieldClass} w-auto`}>
            {info.choices[f]?.map((c) => <option key={c} value={c}>{info.labels[c] ?? c}</option>)}</select>}
        </span>
      </label>
    </div>
  );

  return (
    <>
      <H1>Insegna a leggere la bolletta</H1>
      <p>Segui i passaggi: <strong>tocca nella bolletta</strong> il dato richiesto: i valori possibili sono già riquadrati (puoi anche selezionare il testo a mano). L'app capisce da sola dove si trova e lo riconoscerà anche nelle prossime bollette dello stesso fornitore, con valori diversi.</p>
      <Muted>Il documento resta in questo server: non viene inviato da nessuna parte. Puoi saltare i dati che non trovi.</Muted>
      {Object.entries(errors).map(([k, m]) => <Notice key={k} level="warn">{k === '_all' || k === '_signature' ? m : `${info.help[k] ?? k}: ${m}`}</Notice>)}

      {pdfOk !== false && (
        <div role="status" aria-live="polite" className="sticky top-0 z-10 my-4 flex flex-wrap items-center justify-between gap-2 rounded-card border-2 border-accent bg-surface px-4 py-2.5 shadow-lift">
          <strong>{active ? `Tocca nella bolletta: ${info.help[active] ?? active}` : 'Fatto: controlla i dati qui sotto e salva.'}</strong>
          {active && <SoftButton onClick={() => { const s = new Set(skipped).add(active); setSkipped(s); advance(values, s); }}>Salta</SoftButton>}
        </div>
      )}
      <div ref={pages} data-kind={kind} hidden={pdfOk === false} className="pdf-pages max-h-[65vh] overflow-auto rounded-card border border-edge bg-calm p-2" />
      {pdfOk === null && <Loading />}
      <details open={showText} onToggle={(e) => setShowText((e.target as HTMLDetailsElement).open)} className="my-3">
        <summary className="flex min-h-[44px] cursor-pointer items-center font-bold text-accent">Vedi come testo</summary>
        <pre ref={src} tabIndex={0} aria-label="Testo della bolletta" className="my-3 max-h-[40vh] overflow-auto whitespace-pre-wrap rounded-card border border-edge bg-surface p-4 font-mono text-sm shadow-panel">{info.text}</pre>
        <Muted>Se il documento non si vede bene, seleziona qui il valore e scrivilo nel campo.</Muted>
      </details>

      <form onSubmit={save}>
        <h2 className="mt-4 text-[.8rem] font-bold uppercase tracking-wider text-muted">Fornitore</h2>
        <div className="my-2 grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-3">
          <label className="flex flex-col gap-1 text-sm font-medium">Nome del fornitore, come scritto nella bolletta<input value={signature} onChange={(e) => setSignature(e.target.value)} required className={fieldClass} /></label>
          <label className="flex flex-col gap-1 text-sm font-medium">Nome del layout (a tua scelta)<input value={name} onChange={(e) => setName(e.target.value)} className={fieldClass} /></label>
        </div>
        <h2 className="mt-4 text-[.8rem] font-bold uppercase tracking-wider text-muted">Dati da leggere</h2>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(18rem,1fr))] gap-2">{main.map(row)}</div>
        <details className="my-3"><summary className="flex min-h-[44px] cursor-pointer items-center font-bold text-accent">Altri dati, facoltativi</summary>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(18rem,1fr))] gap-2">{extra.map(row)}</div></details>
        <div className="my-5 flex flex-wrap gap-3"><Button type="submit" busy={busy}>Salva il layout e rileggi la bolletta</Button><Link className={SOFT_BUTTON} to="/bills/new">Annulla</Link></div>
      </form>
    </>
  );
}
