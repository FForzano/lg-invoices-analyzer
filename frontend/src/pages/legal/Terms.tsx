import { Link } from 'react-router-dom';
import { LegalDoc, Sec, useOperator } from './LegalDoc';

export default function Terms() {
  const { site, name, contact } = useOperator();
  return (
    <LegalDoc title="Termini d'uso">
      <p>Questi termini regolano l'uso di «Bollette», un servizio che legge le bollette di luce e gas e stima quanto costerebbero, in un anno, le offerte presenti sul mercato. Usandolo accetti quanto segue; se non sei d'accordo, non usarlo. Come trattiamo i dati personali è spiegato nella <Link to="/privacy">informativa privacy</Link>.</p>

      <Sec title="Chi offre il servizio">
        <p>Bollette è un software libero (licenza Apache-2.0) che ciascuno può installare sul proprio server. Il servizio che stai usando è offerto da <strong>{name}</strong> ({contact}), che lo gestisce in autonomia. Gli autori del software non gestiscono questa installazione, non hanno accesso ai suoi dati e non rispondono di come è configurata.</p>
        <p>Il servizio è destinato a persone maggiorenni che gestiscono le proprie forniture domestiche. {site.auth_enabled && site.registration_open ? 'Registrandoti dichiari di aver letto questi termini e l\'informativa privacy.' : ''}</p>
      </Sec>

      <Sec title="Che cosa fa, e che cosa non fa">
        <p>Il servizio ricava il consumo annuo dalle bollette che carichi e stima il costo annuo delle offerte del catalogo, dicendoti se e di quanto conviene cambiare. Le offerte provengono dagli open data del Portale Offerte (ARERA e Acquirente Unico).</p>
        <ul>
          <li>La stima riguarda <strong>solo la parte decisa dal fornitore</strong> (energia, quote fisse, potenza, sconti). Sono esclusi trasporto, oneri di sistema, imposte, bonus sociali e canone TV.</li>
          <li>Per le offerte indicizzate (PUN/PSV) si usano ipotesi di prezzo: il risultato può cambiare, e il servizio indica quando il vantaggio dipende da esse.</li>
          <li>Con meno di circa 330 giorni di bollette il consumo annuo è una proiezione e la stima è meno affidabile; con una sola bolletta è approssimativa.</li>
          <li>La lettura automatica dei PDF può sbagliare: controlla sempre i dati letti.</li>
          <li><strong>Una stima non è un preventivo, né una consulenza.</strong> Prima di cambiare fornitore verifica prezzi e condizioni sul sito del venditore o nel contratto.</li>
        </ul>
        <p>Bollette non è il Portale Offerte, non è collegato ad ARERA, ad Acquirente Unico né ad alcun fornitore, e non ti propone offerte per conto di nessuno.</p>
      </Sec>

      {site.auth_enabled ? (
        <Sec title="Account">
          <p>{site.registration_open ? 'Per usare l\'app completa serve un account. ' : 'Gli account sono creati dal gestore. '}Sei responsabile della riservatezza della password e di ciò che avviene con il tuo account; se pensi che qualcun altro vi abbia avuto accesso, cambiala subito. Ogni account può avere più profili (ad esempio un appartamento ciascuno).</p>
          <p>Puoi chiedere in ogni momento la chiusura dell'account scrivendo a {contact}: insieme all'account vengono eliminati i suoi profili, le bollette e i PDF caricati. Il gestore può sospendere o chiudere un account che violi questi termini o metta a rischio il servizio.</p>
        </Sec>
      ) : (
        <Sec title="Accesso">
          <p>Su questa installazione non c'è un sistema di account: chi raggiunge il sito può usarlo. Se è raggiungibile da Internet, il gestore è responsabile di proteggerlo.</p>
        </Sec>
      )}

      <Sec title="Uso corretto">
        <p>Carica solo bollette tue o di persone che ti hanno autorizzato a farlo. Non usare il servizio per attività illecite, per sovraccaricarlo o per aggirarne i limiti (le richieste pubbliche, come la simulazione, hanno un limite orario), né per estrarre in massa i suoi dati con strumenti automatici.</p>
      </Sec>

      <Sec title="I tuoi contenuti">
        <p>Le bollette e i dati che carichi restano tuoi. Dai al gestore soltanto il permesso di conservarli ed elaborarli per fornirti il servizio. Nella simulazione senza account il PDF viene letto in memoria e subito scartato.</p>
      </Sec>

      <Sec id="pubblicita" title="Pubblicità e contenuti sponsorizzati">
        <p>Il gestore può inserire nel servizio spazi con contenuti sponsorizzati{site.ads_enabled ? ': su questa installazione al momento ce ne sono' : ' (al momento su questa installazione non ce ne sono)'}. Quando ci sono, valgono queste regole:</p>
        <ul>
          <li>sono <strong>sempre riconoscibili</strong>: portano la dicitura «Sponsorizzato» e il nome di chi paga (D.Lgs. 70/2003, art. 8);</li>
          <li>stanno <strong>in coda</strong> ai contenuti, per esempio sotto il risultato di una simulazione, sotto l'elenco delle bollette o in fondo al confronto: non compaiono tra il verdetto e i numeri che lo sostengono, non sono finestre che si aprono da sole e non spostano la pagina;</li>
          <li><strong>non influenzano</strong> le stime, l'ordine delle offerte né il verdetto «conviene / non conviene»: il calcolo non conosce gli inserzionisti;</li>
          <li>sono testo, un collegamento e, a volte, un'immagine o un video che questo server ti consegna direttamente (il video parte solo se lo avvii): non caricano script né cookie, non partono richieste verso altri siti e non ti tracciano. Se in futuro il gestore userà una rete pubblicitaria che lo faccia, aggiornerà l'informativa e ti chiederà prima il consenso (art. 122 del Codice privacy);</li>
          <li>il collegamento porta a un sito esterno, di cui rispondono i suoi titolari: il gestore non garantisce prodotti, prezzi o condizioni dell'inserzionista e non li raccomanda.</li>
        </ul>
        <p>Gli annunci possono promuovere anche altri servizi del gestore o di società a lui collegate: in quel caso il nome indicato è il loro. Un annuncio non è mai un'offerta del catalogo e non va letto come un consiglio del servizio.</p>
      </Sec>

      <Sec title="Disponibilità e responsabilità">
        <p>Il servizio è offerto gratuitamente e «così com'è»: può avere errori, interruzioni o aggiornamenti, e il gestore non garantisce che sia sempre disponibile o privo di difetti. Le decisioni di cambiare fornitore sono tue.</p>
        <p>Il gestore non esclude né limita la propria responsabilità per dolo o colpa grave (art. 1229 del Codice civile), per i danni alla persona né negli altri casi in cui la legge non lo consente. Negli altri casi, e nei limiti di legge, non risponde delle perdite derivanti dall'uso delle stime o dall'affidamento su di esse, che sono indicative. Nulla in questi termini limita i diritti che la legge ti riconosce come consumatore (D.Lgs. 206/2005, Codice del consumo).</p>
      </Sec>

      <Sec title="Proprietà intellettuale">
        <p>Il codice è distribuito con licenza Apache-2.0: puoi leggerlo, usarlo e modificarlo secondo quella licenza dal <a href="https://github.com/FForzano/lg-invoices-analyzer" target="_blank" rel="noopener noreferrer">repository pubblico</a>. Nomi e marchi dei fornitori citati appartengono ai rispettivi titolari e sono usati solo per identificare le offerte.</p>
      </Sec>

      <Sec title="Modifiche">
        <p>Il gestore può modificare questi termini solo per un giustificato motivo: un cambiamento delle funzioni del servizio, della sua organizzazione o della normativa. Le modifiche valgono per il futuro. Se sono rilevanti, ne diamo avviso nel servizio{site.auth_enabled ? ' (e, dove possibile, per email)' : ''} con un preavviso congruo, e puoi smettere di usarlo{site.auth_enabled ? ' o chiedere la chiusura dell\'account' : ''} senza costi se non le accetti. La data in alto indica l'ultima versione.</p>
      </Sec>

      <Sec title="Legge applicabile e reclami">
        <p>Si applica la legge italiana. Se usi il servizio come consumatore restano ferme le norme inderogabili a tua tutela, comprese quelle sul giudice competente, che è quello del luogo in cui risiedi o hai eletto domicilio (artt. 33, comma 2, lett. u, e 66-bis del Codice del consumo). Prima di rivolgerti al giudice puoi scrivere a {contact}: cerchiamo una soluzione bonaria. Puoi anche rivolgerti a un organismo di risoluzione alternativa delle controversie (artt. 141 e seguenti del Codice del consumo); la piattaforma europea ODR è stata chiusa il 20 luglio 2025.</p>
        <p>Per questioni sui dati personali, vedi l'<Link to="/privacy">informativa privacy</Link>.</p>
      </Sec>
    </LegalDoc>
  );
}
