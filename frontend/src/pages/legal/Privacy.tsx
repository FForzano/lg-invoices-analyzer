import { Link } from 'react-router-dom';
import { Scroll } from '../../components/ui';
import { LegalDoc, Sec, useOperator } from './LegalDoc';

const th = 'px-3.5 py-2.5 text-left text-[.8rem] font-bold uppercase tracking-wide text-muted bg-calm';
const td = 'px-3.5 py-2.5 border-b border-edge align-top';

export default function Privacy() {
  const { site, o, name, contact } = useOperator();
  const login = site.auth_enabled;
  const s3 = site.storage === 's3';
  return (
    <LegalDoc title="Privacy e cookie">
      <p>Questa informativa spiega quali dati personali tratta Bollette, perché, per quanto tempo e quali sono i tuoi diritti. È resa ai sensi degli artt. 13 e 14 del Regolamento (UE) 2016/679 (GDPR) e del D.Lgs. 196/2003 (Codice privacy), come modificato dal D.Lgs. 101/2018.</p>

      {!login && <p className="rounded-field border border-line bg-surface p-3 text-sm">Se questo sito è installato a casa tua e lo usi solo tu o la tua famiglia, il trattamento è per fini esclusivamente personali o domestici e il GDPR non si applica (art. 2, par. 2, lett. c). Questa informativa vale se il sito è offerto ad altre persone.</p>}

      <Sec title="Titolare del trattamento">
        <p>Il titolare è <strong>{name}</strong>{o.address ? `, ${o.address}` : ''}{o.vat ? `, P. IVA ${o.vat}` : ''}{o.registry ? `, iscrizione al Registro imprese / REA ${o.registry}` : ''}. Per qualsiasi richiesta sui tuoi dati scrivi a {contact}. Non è stato designato un responsabile della protezione dei dati (DPO), perché non è obbligatorio per questo servizio. Bollette è un software libero che ognuno installa sul proprio server: gli autori del software non ricevono né vedono i dati di questa installazione.</p>
      </Sec>

      <Sec title="Quali dati trattiamo e perché">
        <ul>
          {login && <li><strong>Account:</strong> nome, email e password. La password non è conservata in chiaro ma come impronta Argon2id. Serve a crearti l'account e farti accedere (esecuzione del servizio richiesto, art. 6.1.b GDPR).</li>}
          <li><strong>Profili e bollette</strong>{login ? ' del tuo account' : ''}: per ogni profilo, nome, regione, provincia, comune e potenza impegnata; per ogni bolletta, fornitore, periodo, consumi, importi, offerta applicata e il PDF stesso. Carica solo bollette tue o di cui sei autorizzato a occuparti. Un PDF di bolletta può contenere anche intestatario, indirizzo di fornitura, codici POD/PDR e dati di pagamento: per questo conviene caricare solo ciò che serve. Servono a stimare il consumo annuo e confrontare le offerte (art. 6.1.b).</li>
          {login && <li><strong>Simulazione senza account:</strong> il PDF viene letto in memoria e subito scartato. Non è salvato né scritto nel database; per la simulazione non si usa mai l'intelligenza artificiale.</li>}
          <li><strong>Dati tecnici:</strong> indirizzo IP e data della richiesta compaiono nei registri del server (e dell'eventuale reverse proxy) e, in memoria, servono a limitare le richieste ripetute; per l'accesso si contano i tentativi falliti. Serve a proteggere il servizio da abusi (interesse legittimo, art. 6.1.f).</li>
          {site.mail_enabled && <li><strong>Email di servizio:</strong> se chiedi il recupero della password, il tuo indirizzo e un link monouso (valido un'ora) passano dal server di posta configurato dal gestore. Non inviamo newsletter né comunicazioni promozionali.</li>}
          {site.llm_enabled && <li><strong>Lettura assistita da IA:</strong> solo per le bollette caricate{login ? ' con un account' : ''}, quando le regole di lettura non bastano, il testo della bolletta può essere inviato a un fornitore di intelligenza artificiale (Anthropic, PBC, con sede negli Stati Uniti), che agisce come responsabile del trattamento, per estrarne i campi. È un trasferimento verso un paese terzo: avviene con le garanzie del capo V del GDPR, cioè la decisione di adeguatezza sul Data Privacy Framework UE-USA, se il fornitore vi aderisce, oppure le clausole contrattuali tipo della Commissione europea. Puoi chiederne copia al titolare. Se non vuoi, inserisci i dati con il modulo manuale.</li>}
        </ul>
        <p>Il conferimento dei dati necessari al servizio è facoltativo, ma senza di essi non possiamo fornirlo. Non trattiamo categorie particolari di dati e non facciamo profilazione né decisioni basate unicamente su trattamenti automatizzati con effetti giuridici (art. 22 GDPR): la stima è un calcolo, la scelta resta tua.</p>
      </Sec>

      <Sec title="Pubblicità">
        <p>Gli eventuali contenuti sponsorizzati (vedi i <Link to="/termini#pubblicita">termini d'uso</Link>) sono testo, un link e a volte un'immagine o un video serviti da questo stesso server: non ti profiliamo, non carichiamo script o cookie pubblicitari e non comunichiamo agli inserzionisti alcun dato su di te. Se segui il link, ti sposti sul sito dell'inserzionista, che è titolare dei dati che lì gli lasci e ha una sua informativa.</p>
      </Sec>

      <Sec title="Con chi condividiamo i dati">
        <p>I dati non sono venduti né ceduti per scopi commerciali. Possono trattarli, per conto del titolare e solo per erogare il servizio, i fornitori tecnici scelti da chi gestisce il sito: {s3 ? 'il servizio di archiviazione dei file (compatibile S3) dove sono conservati i PDF, ' : ''}{site.database === 'postgresql' ? 'il server PostgreSQL, ' : ''}il fornitore di hosting o di rete{site.mail_enabled ? ', il fornitore di posta' : ''}{site.llm_enabled ? ' e, nei casi descritti sopra, il fornitore di IA' : ''}.</p>
        {login && <p>Gli amministratori del sito possono creare, modificare ed eliminare gli account (vedono nome, email e numero di profili). L'app non offre loro la lettura delle bollette altrui, ma chi ha accesso al server o al database può tecnicamente vedere i dati archiviati: è un obbligo del titolare limitarlo e proteggerlo.</p>}
      </Sec>

      <Sec title="Per quanto tempo">
        <ul>
          {login ? <li>Account, profili, bollette e PDF restano finché non chiedi di eliminarli o l'account viene chiuso; con l'account sono cancellati anche i PDF. Le eventuali copie di backup fatte dal gestore si sovrascrivono secondo la sua rotazione.</li>
            : <li>Profili, bollette e PDF restano sul server finché non li elimini dall'app.</li>}
          {login && <li>L'accesso resta valido fino a 30 giorni senza usare l'app (durata predefinita, configurabile), poi scade.</li>}
          {site.mail_enabled && <li>Il link di recupero password dura un'ora e vale una volta sola.</li>}
          <li>I registri tecnici seguono la configurazione del server del gestore e non sono conservati più del necessario alla sicurezza.</li>
        </ul>
      </Sec>

      <Sec title="I tuoi diritti">
        <p>Puoi chiedere al titolare l'accesso ai tuoi dati, la rettifica, la cancellazione, la limitazione del trattamento, la portabilità (artt. 15-20 GDPR) e opporti al trattamento fondato sul legittimo interesse (art. 21). Scrivi a {contact}: rispondiamo senza ingiustificato ritardo e in ogni caso entro un mese dalla richiesta (prorogabile di due in casi complessi, art. 12 GDPR). Se ritieni che il trattamento violi la normativa puoi proporre reclamo al Garante per la protezione dei dati personali (<a href="https://www.garanteprivacy.it" target="_blank" rel="noopener noreferrer">garanteprivacy.it</a>, art. 77 GDPR), o rivolgerti all'autorità giudiziaria.</p>
      </Sec>

      <Sec title="Minori">
        <p>Il servizio è destinato a persone maggiorenni e non raccogliamo consapevolmente dati di minori. Se scopriamo di averne raccolti, li cancelliamo; per la fascia sotto i 14 anni l'art. 2-quinquies del Codice privacy richiede in ogni caso il consenso di chi esercita la responsabilità genitoriale.</p>
      </Sec>

      <Sec id="cookie" title="Cookie e strumenti simili">
        <p>Bollette usa solo strumenti <strong>tecnici</strong>, necessari a far funzionare ciò che hai chiesto. Per questi la normativa (art. 122 del Codice privacy e Linee guida del Garante del 10 giugno 2021) richiede l'informativa ma non il consenso, perciò non vedi alcun banner. Non usiamo cookie di profilazione, di analisi o di terze parti, e non carichiamo font, script o immagini da altri siti.</p>
        <Scroll><table className="w-full">
          <thead><tr><th className={th}>Nome</th><th className={th}>A cosa serve</th><th className={th}>Durata</th></tr></thead>
          <tbody>
            {login && <tr><td className={td}><code>bollette_access</code><br /><span className="text-sm text-muted">cookie, percorso /api</span></td><td className={td}>Ti riconosce mentre usi l'app (token di accesso firmato, <code>HttpOnly</code>, <code>SameSite=Strict</code>).</td><td className={td}>15 minuti</td></tr>}
            {login && <tr><td className={td}><code>bollette_refresh</code><br /><span className="text-sm text-muted">cookie, percorso /api/auth</span></td><td className={td}>Rinnova l'accesso senza chiederti la password a ogni visita (<code>HttpOnly</code>, <code>SameSite=Strict</code>, a rotazione).</td><td className={td}>30 giorni senza usare l'app (valore predefinito)</td></tr>}
            <tr><td className={td}><code>bollette.profile</code><br /><span className="text-sm text-muted">archivio locale del browser</span></td><td className={td}>Ricorda quale profilo (appartamento) hai scelto. Resta nel tuo browser; non è un cookie e non viene mai inviato a terzi.</td><td className={td}>finché non lo cancelli</td></tr>
          </tbody></table></Scroll>
        <p>Se cancelli questi dati dal browser, dovrai solo riaccedere{login ? '' : ' e scegliere di nuovo il profilo'}. Se il gestore introdurrà strumenti non tecnici (per esempio una rete pubblicitaria che tracci), lo scriverà qui e ti chiederà prima il consenso.</p>
      </Sec>

      <Sec title="Sicurezza">
        <p>Password con Argon2id, sessioni in cookie <code>HttpOnly</code> non leggibili dal codice della pagina, rinnovo a rotazione, blocco dopo tentativi ripetuti e limiti alle richieste pubbliche. Nessun sistema è invulnerabile: in caso di violazione dei dati personali il titolare agisce come previsto dagli artt. 33 e 34 GDPR.</p>
      </Sec>

      <Sec title="Modifiche">
        <p>Aggiorneremo questa informativa se cambiano i trattamenti; la data in alto indica l'ultima versione.</p>
      </Sec>
    </LegalDoc>
  );
}
