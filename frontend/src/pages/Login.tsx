import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthCard, SimpleForm, TextInput } from '../components/AuthCard';
import { TEXT_BUTTON } from '../components/styles';

export default function Login() {
  const { login, registrationOpen } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  return (
    <AuthCard title="Accedi" intro="Inserisci l'email e la password del tuo account.">
      <SimpleForm cta="Accedi" onSubmit={() => login(email, password)}>
        <TextInput label="Email" type="email" name="email" autoComplete="username" autoFocus required value={email} onChange={(e) => setEmail(e.target.value)} />
        <TextInput label="Password" type="password" name="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </SimpleForm>
      <p className="mb-0 mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted">
        {registrationOpen ? <span>Non hai un account? <Link to="/registrati" className="font-bold text-accent underline">Registrati</Link></span> : <span />}
        <Link to="/" className={TEXT_BUTTON}>Torna alla home</Link>
      </p>
    </AuthCard>
  );
}
