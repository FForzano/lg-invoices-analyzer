import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { AuthCard, SimpleForm, TextInput } from '../components/AuthCard';

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  return (
    <AuthCard title="Accedi" intro="Inserisci l'email e la password del tuo account.">
      <SimpleForm cta="Accedi" onSubmit={() => login(email, password)}>
        <TextInput label="Email" type="email" name="email" autoComplete="username" autoFocus required value={email} onChange={(e) => setEmail(e.target.value)} />
        <TextInput label="Password" type="password" name="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </SimpleForm>
    </AuthCard>
  );
}
