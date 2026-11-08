import { useAuth } from '../context/AuthContext';
import { AuthCard } from '../components/AuthCard';
import PasswordForm from '../components/PasswordForm';
import { TEXT_BUTTON } from '../components/styles';

/** Password provvisoria (account appena creato o di default): non si entra nell'app finché non è cambiata. */
export default function ChangePassword({ forced = false }: { forced?: boolean }) {
  const { user, setUser, logout } = useAuth();
  return (
    <AuthCard title="Scegli una nuova password" intro={forced ? `${user?.name}, la password attuale è provvisoria: sceglierne una tua serve a proteggere i tuoi dati.` : undefined}>
      <PasswordForm cta="Salva e continua" onDone={(u) => setUser(u)} />
      <button type="button" className={`${TEXT_BUTTON} mt-3`} onClick={() => void logout()}>Esci</button>
    </AuthCard>
  );
}
