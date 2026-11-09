import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthCard, SimpleForm, TextInput } from '../components/AuthCard';
import { TEXT_BUTTON } from '../components/styles';

export default function Login() {
  const { login, registrationOpen, site } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  return (
    <AuthCard title="Accedi" intro="Inserisci l'email e la password del tuo account.">
      <SimpleForm cta="Accedi" onSubmit={() => login(email, password)}>
        <TextInput label="Email" type="email" name="email" autoComplete="username" autoFocus required value={email} onChange={(e) => setEmail(e.target.value)} />
        <TextInput label="Password" type="password" name="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </SimpleForm>
      {site.mail_enabled
        ? <Link to="/password-dimenticata" className={`${TEXT_BUTTON} mt-2`}>Password dimenticata?</Link>
        : <p className="mb-0 mt-3 text-sm text-muted"><span aria-disabled="true" className="font-bold line-through decoration-1">Password dimenticata?</span> Il recupero via email non è attivo su questa installazione: chiedi a un amministratore di reimpostarla.</p>}
      <p className="mb-0 mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted">
        {registrationOpen ? <span>Non hai un account? <Link to="/registrati" className="font-bold text-accent underline">Registrati</Link></span> : <span />}
        <Link to="/" className={TEXT_BUTTON}>Torna alla home</Link>
      </p>
    </AuthCard>
  );
}
