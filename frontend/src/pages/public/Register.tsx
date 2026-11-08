import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { AuthCard, SimpleForm, TextInput } from '../../components/AuthCard';
import { TEXT_BUTTON } from '../../components/styles';

export default function Register() {
  const { registrationOpen, register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  if (!registrationOpen) return <Navigate to="/accedi" replace />;
  return (
    <AuthCard title="Crea il tuo account" intro="Carica più bollette e ottieni una stima precisa, con i tuoi consumi reali.">
      <SimpleForm cta="Registrati" onSubmit={() => register(name, email, password)}>
        <TextInput label="Nome" name="name" autoComplete="name" autoFocus required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
        <TextInput label="Email" type="email" name="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <TextInput label="Password (almeno 8 caratteri)" type="password" name="password" autoComplete="new-password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
      </SimpleForm>
      <p className="mb-0 mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted">
        <span>Hai già un account? <Link to="/accedi" className="font-bold text-accent underline">Accedi</Link></span>
        <Link to="/" className={TEXT_BUTTON}>Torna alla home</Link>
      </p>
    </AuthCard>
  );
}
