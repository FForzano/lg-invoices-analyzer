import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Check, Copy } from 'lucide-react';
import { fetchPdfData } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import type { Layout } from '../lib/types';
import { Actions, ErrorBox, H1, Loading, Muted, Notice, SoftButton } from '../components/ui';
import { PRIMARY_BUTTON, SOFT_BUTTON } from '../components/styles';

export default function LayoutReport() {
  const { id } = useParams();
  const { data, error, loading } = useQuery<{ layout: Layout; raw: string; dropped: string[]; issue: string | null }>(`/layouts/${id}/report`);
  const [copied, setCopied] = useState(false);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox error={error!} />;
  const download = async () => {
    const buf = await fetchPdfData(`/layouts/${id}/report?download=1`);  // stesso fetch con header; è JSON, non un PDF
    const url = URL.createObjectURL(new Blob([buf], { type: 'application/json' }));
    Object.assign(document.createElement('a'), { href: url, download: `layout-${id}.json` }).click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  };
  return (
    <>
      <H1>Segnala il layout «{data.layout.name}»</H1>
      <p>Questo è <strong>tutto</strong> quello che verrebbe condiviso. Controllalo: non parte nulla da solo, sei tu a inviarlo.</p>
      <ul className="my-2 list-disc pl-5">
        <li><strong>Contiene:</strong> il nome del fornitore come scritto in bolletta, e per ogni dato l'etichetta accanto a cui si trova.</li>
        <li><strong>Non contiene:</strong> importi, consumi, date, nomi, indirizzi, codici cliente o POD/PDR, né il PDF o il suo testo.</li>
      </ul>
      {data.dropped.length > 0 && <Notice level="warn">Escluse perché l'etichetta sembra contenere dati personali: {data.dropped.join(', ')}.</Notice>}
      <pre className="my-4 max-h-[40vh] overflow-auto whitespace-pre-wrap rounded-card border border-edge bg-surface p-4 font-mono text-sm shadow-panel">{data.raw}</pre>
      <Actions>
        <button type="button" className={PRIMARY_BUTTON} onClick={() => void download()}>Scarica il file .json</button>
        <SoftButton onClick={() => void navigator.clipboard.writeText(data.raw).then(() => setCopied(true))}>{copied ? <><Check className="h-4 w-4" aria-hidden />Copiato</> : <><Copy className="h-4 w-4" aria-hidden />Copia</>}</SoftButton>
        {data.issue && <a className={SOFT_BUTTON} href={data.issue} target="_blank" rel="noopener noreferrer">Apri una segnalazione su GitHub</a>}
      </Actions>
      <Muted>La segnalazione si apre sul sito di GitHub già compilata: la rivedi e la invii tu, con il tuo account. Dopo una verifica (con un test su un testo di esempio) il layout entra nell'app per tutti.</Muted>
    </>
  );
}
