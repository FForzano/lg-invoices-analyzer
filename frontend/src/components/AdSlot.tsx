import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import type { Ad } from '../lib/types';
import { FOCUS_RING } from './styles';

export type AdSlotName = 'simulation-result' | 'bills-list' | 'compare-end';

/** Spazio pubblicitario: non occupa nulla finché il gestore non ne configura uno (ADS_FILE, vedi deploy/ads.example.json).
 *  Regole valide per ogni spazio: sempre dopo il contenuto che l'utente è venuto a leggere, mai tra il verdetto e i suoi numeri;
 *  niente popup né spostamenti di pagina (compare in coda, a pagina già disegnata); sempre la dicitura «Sponsorizzato»;
 *  testo, un link e al più un'immagine o un video serviti da questo stesso server: il video non parte da solo, nessuna richiesta a terzi. */
export default function AdSlot({ slot }: { slot: AdSlotName }) {
  const { site } = useAuth();
  const [ad, setAd] = useState<Ad | null>(null);
  useEffect(() => {
    if (!site.ads_enabled) return;
    let alive = true;
    api.get<{ ad: Ad | null }>('/ads', { slot }).then((r) => { if (alive) setAd(r.ad); }).catch(() => { /* senza annuncio la pagina resta com'è */ });
    return () => { alive = false; };
  }, [slot, site.ads_enabled]);
  if (!ad) return null;
  const media = 'aspect-video w-full flex-none overflow-hidden rounded-block bg-calm sm:w-56';
  return (
    <aside aria-label="Contenuto sponsorizzato" className="my-6 rounded-card border border-dashed border-line bg-surface/60 p-4 sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        {ad.video ? (
          <div className={media}><video className="h-full w-full object-cover" controls preload="none" playsInline poster={ad.image ?? undefined} aria-label={ad.alt}><source src={ad.video} />Il tuo browser non riproduce questo video.</video></div>
        ) : ad.image ? (
          <div className={media}><img src={ad.image} alt={ad.alt} loading="lazy" decoding="async" className="h-full w-full object-cover" /></div>
        ) : null}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            <span className="rounded-full bg-calm px-3 py-0.5 text-[.8rem] font-bold leading-6 text-fg">Sponsorizzato</span>
            <span>da {ad.sponsor}</span>
          </div>
          <p className="mb-0 mt-2 text-base font-bold">{ad.title}</p>
          {ad.text && <p className="mb-0 mt-1 max-w-[58ch] text-sm text-muted">{ad.text}</p>}
          <a href={ad.url} target="_blank" rel="sponsored noopener noreferrer" className={`mt-1 inline-flex min-h-[44px] items-center gap-1.5 rounded font-bold text-accent underline-offset-4 hover:underline ${FOCUS_RING}`}>
            {ad.cta}<ExternalLink className="h-4 w-4" aria-hidden /><span className="sr-only">(annuncio, si apre in una nuova scheda)</span>
          </a>
        </div>
      </div>
    </aside>
  );
}
