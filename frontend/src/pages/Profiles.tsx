import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type WithMessages } from '../lib/api';
import { useAction } from '../lib/useAction';
import type { Profile } from '../lib/types';
import { useApp } from '../context/AppContext';
import { useConfirm } from '../context/ConfirmContext';
import { Actions, Button, Card, DangerLink, H1, Muted, SoftButton, Tag } from '../components/ui';
import { Modal } from '../components/Modal';
import { TEXT_BUTTON, fieldClass } from '../components/styles';

/** Nome del profilo: una modale piccola, uguale per «Nuovo» e «Rinomina». */
function NameModal({ open, title, initial, cta, onClose, onSubmit, busy }: { open: boolean; title: string; initial: string; cta: string; onClose: () => void; onSubmit: (name: string) => void; busy: boolean }) {
  const [name, setName] = useState(initial);
  const submit = (e: FormEvent) => { e.preventDefault(); onSubmit(name.trim()); };
  return (
    <Modal open={open} onClose={onClose} title={title} compact>
      <form onSubmit={submit} className="space-y-4 pb-2">
        <label className="flex flex-col gap-1 text-sm font-medium">Nome
          <input autoFocus value={name} onChange={(e) => setName(e.target.value)} maxLength={60} required placeholder="Es. Casa al mare" className={fieldClass} /></label>
        <div className="flex justify-end gap-3"><SoftButton onClick={onClose}>Annulla</SoftButton><Button type="submit" busy={busy}>{cta}</Button></div>
      </form>
    </Modal>
  );
}

export default function Profiles() {
  const { profiles, profile, refresh, switchProfile, flash } = useApp();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const { run, busy } = useAction();
  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState<Profile | null>(null);

  const create = (name: string) => run(async () => {
    const r = await api.post<WithMessages & { id: number }>('/profiles', { name });
    await switchProfile(r.id); flash(r.messages); setCreating(false); navigate('/settings');
  });
  const rename = (name: string) => run(async () => { await api.post(`/profiles/${renaming!.id}/rename`, { name }); setRenaming(null); await refresh(); });
  const remove = async (p: Profile) => {
    if (!(await confirm({ title: 'Eliminare il profilo?', message: `«${p.name}» e tutte le sue bollette. L'azione non si può annullare.` }))) return;
    await run(async () => { const r = await api.del<WithMessages>(`/profiles/${p.id}`); flash(r.messages); await refresh(); });
  };

  return (
    <>
      <H1>Profili</H1>
      <Muted>Un profilo è un appartamento (o una fornitura): ha le sue bollette, l'offerta attuale, la località e la potenza di default. Il catalogo delle offerte e le ipotesi su PUN/PSV sono condivisi.</Muted>
      {profiles.map((p) => (
        <Card key={p.id}>
          <div className="flex flex-wrap items-center gap-3 pt-3">
            <h2 className="text-xl font-bold">{p.name}</h2>
            {p.id === profile.id && <Tag kind="current">attivo</Tag>}
            <button type="button" className={TEXT_BUTTON} onClick={() => setRenaming(p)} aria-label={`Rinomina ${p.name}`}>Rinomina</button>
          </div>
          <Muted className="my-1">{p.bills ?? 0} {p.bills === 1 ? 'bolletta' : 'bollette'}</Muted>
          <div className="flex flex-wrap items-center gap-4">
            {p.id !== profile.id && <SoftButton onClick={() => void switchProfile(p.id)}>Usa</SoftButton>}
            {profiles.length > 1 && <DangerLink onClick={() => void remove(p)}>elimina</DangerLink>}
          </div>
        </Card>
      ))}
      <Actions><Button onClick={() => setCreating(true)}>+ Nuovo profilo</Button></Actions>
      <Muted>Parte con località e potenza del profilo attivo; dopo la creazione correggili in Impostazioni.</Muted>
      <NameModal key={`new-${creating}`} open={creating} title="Nuovo profilo" initial="" cta="Crea" busy={busy} onClose={() => setCreating(false)} onSubmit={(n) => void create(n)} />
      <NameModal key={`ren-${renaming?.id}`} open={renaming !== null} title="Rinomina profilo" initial={renaming?.name ?? ''} cta="Salva" busy={busy} onClose={() => setRenaming(null)} onSubmit={(n) => void rename(n)} />
    </>
  );
}
