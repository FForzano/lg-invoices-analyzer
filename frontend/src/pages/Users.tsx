import { useState, type FormEvent } from 'react';
import { api, type WithMessages } from '../lib/api';
import type { User } from '../lib/types';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { useConfirm } from '../context/ConfirmContext';
import { useAction } from '../lib/useAction';
import { useQuery } from '../lib/useQuery';
import { Actions, Button, Card, DangerLink, ErrorBox, H1, Loading, Muted, SoftButton, Tag } from '../components/ui';
import { Modal } from '../components/Modal';
import { TEXT_BUTTON, fieldClass } from '../components/styles';

type Editing = { mode: 'new' } | { mode: 'edit'; user: User } | { mode: 'password'; user: User } | null;

function UserModal({ editing, onClose, onSaved, busy, run }: { editing: Editing; onClose: () => void; onSaved: () => void; busy: boolean; run: ReturnType<typeof useAction>['run'] }) {
  const { flash } = useApp();
  const user = editing && editing.mode !== 'new' ? editing.user : null;
  const [name, setName] = useState(user?.name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [password, setPassword] = useState('');
  const [admin, setAdmin] = useState(user?.is_admin ?? false);
  if (!editing) return null;
  const mode = editing.mode;
  const title = mode === 'new' ? 'Nuovo utente' : mode === 'edit' ? 'Modifica utente' : `Nuova password per ${user!.name}`;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const r = mode === 'new' ? await api.post<WithMessages>('/users', { name, email, password, is_admin: admin })
        : mode === 'edit' ? await api.put<WithMessages>(`/users/${user!.id}`, { name, email, is_admin: admin })
        : await api.post<WithMessages>(`/users/${user!.id}/password`, { password });
      flash(r.messages); onSaved();
    });
  };
  return (
    <Modal open onClose={onClose} title={title} compact>
      <form onSubmit={submit} className="space-y-4 pb-2">
        {mode !== 'password' && <>
          <label className="flex flex-col gap-1 text-sm font-medium">Nome
            <input autoFocus value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required className={fieldClass} /></label>
          <label className="flex flex-col gap-1 text-sm font-medium">Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className={fieldClass} /></label>
          <label className="flex min-h-[44px] items-center gap-3 text-sm font-medium">
            <input type="checkbox" checked={admin} onChange={(e) => setAdmin(e.target.checked)} className="h-5 w-5" />Amministratore (gestisce gli utenti e aggiorna il catalogo offerte)</label>
        </>}
        {mode !== 'edit' && (
          <label className="flex flex-col gap-1 text-sm font-medium">Password provvisoria (almeno 8 caratteri)
            <input type="text" autoComplete="off" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required className={fieldClass} />
            <span className="text-xs font-normal text-muted">L'utente dovrà cambiarla al primo accesso.</span></label>
        )}
        <div className="flex justify-end gap-3"><SoftButton onClick={onClose}>Annulla</SoftButton><Button type="submit" busy={busy}>Salva</Button></div>
      </form>
    </Modal>
  );
}

export default function Users() {
  const { user: me } = useAuth();
  const { flash } = useApp();
  const confirm = useConfirm();
  const { run, busy } = useAction();
  const { data, error, reload } = useQuery<{ users: User[] }>('/users');
  const [editing, setEditing] = useState<Editing>(null);

  if (!me?.is_admin) return <><H1>Utenti</H1><Muted>Questa pagina è riservata agli amministratori.</Muted></>;
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const remove = async (u: User) => {
    if (!(await confirm({ title: 'Eliminare l\'utente?', message: `«${u.name}» con tutti i suoi profili e le sue bollette. L'azione non si può annullare.` }))) return;
    await run(async () => { const r = await api.del<WithMessages>(`/users/${u.id}`); flash(r.messages); reload(); });
  };

  return (
    <>
      <H1>Utenti</H1>
      <Muted>Ogni utente ha i suoi profili, bollette e offerta attuale. Il catalogo delle offerte e le ipotesi su PUN/PSV sono condivisi.</Muted>
      {data.users.map((u) => (
        <Card key={u.id}>
          <div className="flex flex-wrap items-center gap-3 pt-3">
            <h2 className="text-xl font-bold">{u.name}</h2>
            {u.is_admin && <Tag kind="current">amministratore</Tag>}
            {u.must_change_password && <Tag kind="warn">password provvisoria</Tag>}
          </div>
          <Muted className="my-1">{u.email} · {u.profiles ?? 0} {u.profiles === 1 ? 'profilo' : 'profili'}</Muted>
          <div className="flex flex-wrap items-center gap-4">
            <button type="button" className={TEXT_BUTTON} onClick={() => setEditing({ mode: 'edit', user: u })} aria-label={`Modifica ${u.name}`}>Modifica</button>
            <button type="button" className={TEXT_BUTTON} onClick={() => setEditing({ mode: 'password', user: u })} aria-label={`Reimposta la password di ${u.name}`}>Reimposta password</button>
            {u.id !== me.id && <DangerLink onClick={() => void remove(u)}>elimina</DangerLink>}
          </div>
        </Card>
      ))}
      <Actions><Button onClick={() => setEditing({ mode: 'new' })}>+ Nuovo utente</Button></Actions>
      <UserModal key={editing ? `${editing.mode}-${'user' in editing ? editing.user.id : 'n'}` : 'none'} editing={editing} busy={busy} run={run}
        onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />
    </>
  );
}
