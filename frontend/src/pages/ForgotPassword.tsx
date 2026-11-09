import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import type { Message } from '../lib/types';
import { AuthCard, SimpleForm, TextInput } from '../components/AuthCard';
import { Notice } from '../components/ui';
import { TEXT_BUTTON } from '../components/styles';
import { useAuth } from '../context/AuthContext';

/** Recupero password: esiste solo se il gestore ha configurato un server di posta (MAIL_HOST). Altrimenti lo dice e rimanda all'amministratore. */
export default function ForgotPassword() {
  const { site } = useAuth();
  const [email, setEmail] = useState('');
  const [done, setDone] = useState<string | null>(null);
  if (!site.mail_enabled) return (
    <AuthCard title="Recupero password non attivo">
      <p className="mt-3 text-sm">Su questa installazione non è configurato l'invio di email, quindi non posso mandarti un link. Chiedi a un amministratore di reimpostare la tua password: ti darà una provvisoria da cambiare al primo accesso.</p>
      <Link to="/accedi" className={`${TEXT_BUTTON} mt-2`}>Torna all'accesso</Link>
    </AuthCard>
  );
  return (
    <AuthCard title="Password dimenticata" intro="Scrivi l'email del tuo account: ti mandiamo un link, valido un'ora, per sceglierne una nuova.">
      {done ? <div className="mt-4"><Notice>{done}</Notice><p className="text-sm text-muted">Non arriva? Controlla la cartella spam, o riprova tra qualche minuto.</p></div>
        : <SimpleForm cta="Invia il link" onSubmit={async () => { const r = await api.post<{ messages: Message[] }>('/auth/forgot', { email }); setDone(r.messages[0]?.text ?? 'Controlla la tua email.'); }}>
          <TextInput label="Email" type="email" name="email" autoComplete="username" autoFocus required value={email} onChange={(e) => setEmail(e.target.value)} />
        </SimpleForm>}
      <Link to="/accedi" className={`${TEXT_BUTTON} mt-2`}>Torna all'accesso</Link>
    </AuthCard>
  );
}
