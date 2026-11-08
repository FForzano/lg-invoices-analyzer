import { useState } from 'react';
import { api } from '../lib/api';
import type { Message, User } from '../lib/types';
import { SimpleForm, TextInput } from './AuthCard';

/** Cambio password: serve quella attuale; la nuova va scritta due volte. Gli altri dispositivi dovranno accedere di nuovo. */
export default function PasswordForm({ cta = 'Cambia password', onDone }: { cta?: string; onDone: (user: User, messages: Message[]) => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [again, setAgain] = useState('');
  return (
    <SimpleForm cta={cta} onSubmit={async () => {
      if (next !== again) throw new Error('Le due password nuove non coincidono.');
      const r = await api.post<{ user: User; messages: Message[] }>('/auth/password', { current_password: current, new_password: next });
      setCurrent(''); setNext(''); setAgain('');
      onDone(r.user, r.messages);
    }}>
      <TextInput label="Password attuale" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
      <TextInput label="Nuova password (almeno 8 caratteri)" type="password" autoComplete="new-password" minLength={8} required value={next} onChange={(e) => setNext(e.target.value)} />
      <TextInput label="Ripeti la nuova password" type="password" autoComplete="new-password" minLength={8} required value={again} onChange={(e) => setAgain(e.target.value)} />
    </SimpleForm>
  );
}
