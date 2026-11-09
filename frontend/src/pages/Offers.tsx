import { useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, type WithMessages } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import { commodityLabel } from '../lib/format';
import type { Offer, PageInfo } from '../lib/types';
import { useApp } from '../context/AppContext';
import { useIsAdmin } from '../context/AuthContext';
import { useConfirm } from '../context/ConfirmContext';
import { Actions, Button, DangerLink, ErrorBox, H1, LinkButton, Loading, Muted, Pager, Scroll, SoftButton, Tag, usePage } from '../components/ui';
import { Modal } from '../components/Modal';
import OfferFilters, { filtersActive, useOfferFilters } from '../components/OfferFilters';
import { Flags } from '../components/OfferDetail';
import { fieldClass } from '../components/styles';

const th = 'px-3.5 py-2.5 text-left text-[.8rem] font-bold uppercase tracking-wide text-muted bg-calm whitespace-nowrap';
const td = 'px-3.5 py-2.5 border-b border-edge whitespace-nowrap';

/** Aggiorna o importa il catalogo: una modale con le due vie (Portale Offerte, CSV). */
function CatalogModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const { flash } = useApp();
  const { run, busy } = useAction();
  const file = useRef<HTMLInputElement>(null);
  const arera = () => run(async () => { const r = await api.post<WithMessages>('/offers/import-arera'); flash(r.messages); onClose(); onDone(); });
  const csv = (e: FormEvent) => {
    e.preventDefault();
    const f = file.current?.files?.[0];
    if (!f) return;
    const body = new FormData(); body.set('csv', f);
    void run(async () => { const r = await api.post<WithMessages>('/offers/import-csv', body); flash(r.messages); onClose(); onDone(); });
  };
  return (
    <Modal open={open} onClose={onClose} title="Aggiorna o importa il catalogo">
      <div className="space-y-6 pb-4">
        <section><h3 className="font-bold">Portale Offerte ARERA (open data)</h3>
          <div className="my-2"><Button busy={busy} onClick={() => void arera()}>{busy ? 'Download in corso…' : 'Aggiorna dal Portale Offerte'}</Button></div>
          <Muted>Scarica i file pubblici (~35 MB), importa le offerte domestiche e sostituisce quelle importate prima. Le offerte inserite a mano e quella «attuale» restano. Sconti e bonus una tantum non sono importati.</Muted></section>
        <section><h3 className="font-bold">Import da CSV</h3>
          <form onSubmit={csv} className="my-2 space-y-3">
            <label className="flex flex-col gap-1 text-sm font-medium">File CSV
              <input ref={file} type="file" accept=".csv,text/csv" required className={`${fieldClass} file:mr-3 file:rounded-block file:border-0 file:bg-accent-soft file:px-3 file:py-1 file:font-bold file:text-accent`} /></label>
            <SoftButton type="submit" busy={busy}>Importa</SoftButton>
          </form>
          <Muted>Intestazione = nomi dei campi (vedi <code>examples/offers.csv</code>). Separatore , o ;</Muted></section>
      </div>
    </Modal>
  );
}

export default function Offers() {
  const [params, setParams] = useSearchParams();
  const page = usePage();
  const q = params.get('q') ?? '';
  const [term, setTerm] = useState(q);
  const filters = useOfferFilters();
  const [catalog, setCatalog] = useState(false);
  const confirm = useConfirm();
  const { run } = useAction();
  const admin = useIsAdmin();
  const { data, error, loading, reload } = useQuery<{ items: Offer[]; page: PageInfo; q: string; catalog_empty: boolean }>('/offers', { q, page, ...filters });

  const remove = async (o: Offer) => {
    if (!(await confirm({ title: "Eliminare l'offerta?", message: `${o.supplier} – ${o.name}` }))) return;
    await run(async () => { await api.del(`/offers/${o.id}`); reload(); });
  };

  return (
    <>
      <H1>Offerte</H1>
      <Actions>
        <LinkButton to="/offers/new?commodity=power" soft>+ Luce</LinkButton>
        <LinkButton to="/offers/new?commodity=gas" soft>+ Gas</LinkButton>
        {admin && <SoftButton onClick={() => setCatalog(true)}>Aggiorna o importa il catalogo</SoftButton>}
      </Actions>
      <CatalogModal open={catalog} onClose={() => setCatalog(false)} onDone={reload} />
      {loading && !data ? <Loading /> : error || !data ? <ErrorBox error={error!} /> : <>
        {data.catalog_empty && <Muted className="mb-3">Il catalogo è vuoto: {admin ? 'importa le offerte dal Portale Offerte' : 'chiedi a un amministratore di importare le offerte dal Portale Offerte'} per poterle confrontare.</Muted>}
        {(data.page.total > 0 || q) && (
          <form className="my-2 flex flex-wrap gap-2" role="search" onSubmit={(e) => { e.preventDefault(); setParams(term ? { q: term } : {}); }}>
            <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Cerca fornitore o offerta" aria-label="Cerca fornitore o offerta" className={`${fieldClass} max-w-xs flex-1`} />
            <Button type="submit">Cerca</Button>
          </form>
        )}
        <OfferFilters />
        <Pager page={data.page} />
        <Scroll><table className="w-full">
          <thead><tr><th className={th}>Fornitura</th><th className={th}>Fornitore</th><th className={th}>Offerta</th><th className={th}>Tipo</th><th className={th}>Scadenza</th><th className={th} /><th className={th} /></tr></thead>
          <tbody>{data.items.map((o) => (
            <tr key={o.id} className={o.is_current ? 'bg-accent-soft' : 'hover:bg-calm'}>
              <td className={td}>{commodityLabel(o.commodity)}</td><td className={td}>{o.supplier}</td>
              <td className={`${td} whitespace-normal`}><Link className="font-bold text-accent underline" to={`/offers/${o.id}`}>{o.name}</Link>{o.dual_with && <span className="text-sm text-muted"> (luce+gas)</span>}<Flags o={o} /></td>
              <td className={td}>{o.price_type === 'fixed' ? 'fisso' : 'indicizzato'}</td><td className={td}>{o.expires_on ?? '–'}</td>
              <td className={td}>{!!o.is_current && <Tag kind="current">attuale</Tag>}</td>
              <td className={td}>{(admin || o.profile_id != null) && <DangerLink onClick={() => void remove(o)}>elimina</DangerLink>}</td>
            </tr>))}
            {!data.items.length && <tr><td colSpan={7} className={`${td} text-muted`}>{filtersActive(filters) || q ? 'Nessuna offerta con questi filtri: provane meno.' : 'Nessuna offerta.'}</td></tr>}
          </tbody></table></Scroll>
        <Pager page={data.page} />
      </>}
    </>
  );
}
