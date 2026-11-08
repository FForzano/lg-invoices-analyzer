import { useState, type FormEvent } from 'react';
import { api, type WithMessages } from '../lib/api';
import type { User } from '../lib/types';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { useAction } from '../lib/useAction';
import { Button, Card, H1, H2, Muted, SoftButton, Tag } from '../components/ui';
import { Modal } from '../components/Modal';
import PasswordForm from '../components/PasswordForm';
import { fieldClass } from '../components/styles';

export default function Account() {
  const { user, setUser, logout } = useAuth();
  const { flash } = useApp();
  const { run, busy } = useAction();
  const [name, setName] = useState(user?.name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [changing, setChanging] = useState(false);
  if (!user) return null;

  const save = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const r = await api.put<WithMessages & { user: User }>('/auth/me', { name, email });
      setUser(r.user); flash(r.messages);
    });
  };

  return (
    <>
      <H1>Il tuo account {user.is_admin && <Tag kind="current">amministratore</Tag>}</H1>
      <Muted>I profili (le tue case o forniture) sono tuoi: gli altri utenti non li vedono. Ne puoi avere quanti vuoi, da «Profili».</Muted>
      <Card>
        <H2>Dati personali</H2>
        <form onSubmit={save} className="space-y-4 pb-3">
          <label className="flex flex-col gap-1 text-sm font-medium">Nome
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required autoComplete="name" className={fieldClass} /></label>
          <label className="flex flex-col gap-1 text-sm font-medium">Email (la usi per accedere)
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" className={fieldClass} /></label>
          <Button type="submit" busy={busy}>Salva</Button>
        </form>
      </Card>
      <Card>
        <H2>Password e accesso</H2>
        <div className="flex flex-wrap items-center gap-3 pb-3">
          <SoftButton onClick={() => setChanging(true)}>Cambia password</SoftButton>
          <SoftButton onClick={() => void logout()}>Esci</SoftButton>
        </div>
      </Card>
      <Modal open={changing} onClose={() => setChanging(false)} title="Cambia password" compact>
        <div className="pb-2">
          <PasswordForm onDone={(u, m) => { setUser(u); flash(m); setChanging(false); }} />
        </div>
      </Modal>
    </>
  );
}
