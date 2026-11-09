import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { AuthCard, SimpleForm, TextInput } from '../components/AuthCard';
import { Notice } from '../components/ui';
import { PRIMARY_BUTTON, TEXT_BUTTON } from '../components/styles';

/** Pagina del link ricevuto per email: nuova password, poi si accede come sempre. */
export default function ResetPassword() {
  const token = useSearchParams()[0].get('token') ?? '';
  const [next, setNext] = useState('');
  const [again, setAgain] = useState('');
  const [done, setDone] = useState(false);
  if (done) return (
    <AuthCard title="Password cambiata" intro="Gli altri dispositivi dovranno accedere di nuovo.">
      <Link to="/accedi" className={`${PRIMARY_BUTTON} mt-5 w-full`}>Accedi</Link>
    </AuthCard>
  );
  if (!token) return (
    <AuthCard title="Link non valido">
      <div className="mt-3"><Notice level="warn">Questo indirizzo non contiene il codice per reimpostare la password. Apri il link dell'email per intero, oppure chiedine uno nuovo.</Notice></div>
      <Link to="/password-dimenticata" className={`${TEXT_BUTTON} mt-2`}>Richiedi un nuovo link</Link>
    </AuthCard>
  );
  return (
    <AuthCard title="Scegli una nuova password">
      <SimpleForm cta="Salva la password" onSubmit={async () => {
        if (next !== again) throw new Error('Le due password non coincidono.');
        await api.post('/auth/reset', { token, password: next }); setDone(true);
      }}>
        <TextInput label="Nuova password (almeno 8 caratteri)" type="password" autoComplete="new-password" minLength={8} required autoFocus value={next} onChange={(e) => setNext(e.target.value)} />
        <TextInput label="Ripeti la nuova password" type="password" autoComplete="new-password" minLength={8} required value={again} onChange={(e) => setAgain(e.target.value)} />
      </SimpleForm>
      <Link to="/password-dimenticata" className={`${TEXT_BUTTON} mt-2`}>Il link è scaduto? Richiedine uno nuovo</Link>
    </AuthCard>
  );
}
