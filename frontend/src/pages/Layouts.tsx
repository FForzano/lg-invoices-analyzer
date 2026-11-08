import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { useQuery } from '../lib/useQuery';
import { useAction } from '../lib/useAction';
import type { Layout } from '../lib/types';
import { useConfirm } from '../context/ConfirmContext';
import { Actions, DangerLink, ErrorBox, H1, H2, LinkButton, Loading, Muted, Scroll } from '../components/ui';

const th = 'px-3.5 py-2.5 text-left text-[.8rem] font-bold uppercase tracking-wide text-muted bg-calm whitespace-nowrap';
const td = 'px-3.5 py-2.5 border-b border-edge whitespace-nowrap';

export default function Layouts() {
  const { data, error, loading, reload } = useQuery<{ mine: Layout[]; builtin: Layout[] }>('/layouts');
  const confirm = useConfirm();
  const { run } = useAction();
  const remove = async (l: Layout) => {
    if (!(await confirm({ title: 'Eliminare il layout?', message: `«${l.name}»: le bollette di questo fornitore non si leggeranno più da sole.` }))) return;
    await run(async () => { await api.del(`/layouts/${l.id}`); reload(); });
  };
  return (
    <>
      <H1>Layout di lettura</H1>
      <p>Un layout dice all'app dove trovare i dati nelle bollette di un fornitore. Le bollette dello stesso fornitore, anche con importi diversi, si leggono poi da sole, senza LLM. Per insegnarne uno nuovo carica una bolletta non riconosciuta: l'app ti propone di indicare i dati.</p>
      <Actions><LinkButton to="/bills/new" soft>Carica una bolletta</LinkButton></Actions>
      {loading && !data ? <Loading /> : error || !data ? <ErrorBox error={error!} /> : <>
        <H2>Insegnati da te</H2>
        {data.mine.length ? <>
          <Scroll><table className="w-full"><thead><tr><th className={th}>Layout</th><th className={th}>Fornitore nel testo</th><th className={`${th} text-right`}>Regole</th><th className={th} /></tr></thead>
            <tbody>{data.mine.map((l) => (
              <tr key={l.id} className="hover:bg-calm"><td className={td}>{l.name}</td><td className={td}>{l.signature}</td><td className={`${td} text-right`}>{l.rules.length}</td>
                <td className={`${td} flex items-center gap-4`}><Link className="font-bold text-accent underline" to={`/layouts/${l.id}/report`}>Segnala agli sviluppatori</Link><DangerLink onClick={() => void remove(l)}>elimina</DangerLink></td></tr>))}
            </tbody></table></Scroll>
          <Muted>«Segnala» mostra prima cosa verrebbe condiviso: solo etichette e formati, mai valori o dati personali. Se lo segnali, il tuo fornitore potrà essere letto da tutti senza insegnarlo.</Muted>
        </> : <Muted>Nessun layout ancora.</Muted>}
        <H2>Forniti con l'app</H2>
        {data.builtin.length ? <ul className="list-disc pl-5">{data.builtin.map((l) => <li key={l.name}>{l.name}</li>)}</ul>
          : <Muted>Nessuno: oltre alla lettura predefinita, i layout arrivano dalle segnalazioni degli utenti.</Muted>}
      </>}
    </>
  );
}
