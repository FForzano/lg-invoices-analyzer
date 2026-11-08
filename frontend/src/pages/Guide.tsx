import { Link } from 'react-router-dom';
import { H1, H2 } from '../components/ui';
import { FOCUS_RING } from '../components/styles';

const PILL = `inline-flex min-h-[44px] items-center rounded-full bg-surface px-5 py-1.5 font-medium text-fg no-underline shadow-panel transition duration-200 hover:-translate-y-px hover:shadow-lift ${FOCUS_RING}`;

// Testo della guida: identico a quello delle pagine Jinja precedenti.
export default function Guide() {
  return (

<div className="guide">
<H1>Guida: leggere le offerte e decidere</H1>
<p className="text-sm text-muted">Niente gergo: cosa significano le voci, come leggere il verdetto e cosa controllare prima di accettare una proposta. Nei form trovi un tastino <strong>(i)</strong> accanto a ogni termine.</p>
<div className="my-3 mb-5 flex flex-wrap gap-2" role="navigation" aria-label="Indice">
  <a className={PILL} href="#cosa">Cosa confronta</a><a className={PILL} href="#fisso">Fisso o indicizzato</a><a className={PILL} href="#voci">Le voci</a>
  <a className={PILL} href="#verdetto">Il verdetto</a><a className={PILL} href="#telefono">La telefonata</a><a className={PILL} href="#contratto">Prima di firmare</a>
</div>

<H2 id="cosa">Cosa confronta l'app (e cosa no)</H2>
<p>La bolletta ha due parti. Una la decide il <strong>venditore</strong> (la società con cui hai il contratto): il prezzo dell'energia, la quota fissa, eventuali sconti. L'altra non dipende da lui: trasporto, oneri di sistema, imposte e IVA sono uguali per tutti.</p>
<p>L'app confronta <strong>solo la prima parte</strong>, perché è l'unica che cambia se cambi venditore. Per questo il «costo annuo» che vedi è più basso del totale che paghi davvero: non è un errore. Conta la <em>differenza</em> tra due offerte, non la cifra in sé.</p>

<H2 id="fisso">Prezzo fisso o indicizzato?</H2>
<dl>
  <dt>Prezzo fisso</dt>
  <dd>Per tutta la durata delle condizioni (di solito 12 o 24 mesi) paghi lo stesso prezzo per ogni kWh (luce) o Smc (gas), qualunque cosa faccia il mercato. Sai in anticipo quanto spendi, a parità di consumi. <strong>Pro:</strong> prevedibile, ti protegge dai rincari. <strong>Contro:</strong> non godi dei ribassi, e il fisso di solito parte da un livello un po' più alto per coprire il rischio del venditore.</dd>
  <dt>Prezzo indicizzato (variabile)</dt>
  <dd>Il prezzo è <em>prezzo di mercato del mese + spread</em>. Il prezzo di mercato è il <strong>PUN</strong> per la luce e il <strong>PSV</strong> per il gas; lo spread è il margine fisso del venditore. <strong>Pro:</strong> quando il mercato scende, scende la bolletta; lo spread è spesso basso. <strong>Contro:</strong> se il mercato sale, sale anche la bolletta, senza tetto, e non puoi saperlo in anticipo.</dd>
</dl>
<p><strong>Come scegliere.</strong> Se vuoi tranquillità e un budget certo, il fisso. Se accetti oscillazioni per risparmiare in media e il tuo bilancio regge un mese caro, l'indicizzato. Per confrontare un indicizzato con un fisso, l'app ipotizza un prezzo di mercato medio (Impostazioni) e ricalcola anche con ±20% per mostrarti quanto il risultato dipende da quell'ipotesi.</p>
<dl>
  <dt>PUN</dt><dd>Prezzo Unico Nazionale: il prezzo all'ingrosso dell'elettricità in Italia, calcolato ogni mese. Unità: €/kWh.</dd>
  <dt>PSV</dt><dd>Punto di Scambio Virtuale: il prezzo all'ingrosso del gas in Italia. Unità: €/Smc.</dd>
  <dt>Spread</dt><dd>Quanto il venditore aggiunge al PUN o al PSV. A parità di altre condizioni, più basso è meglio.</dd>
</dl>

<H2 id="voci">Le voci di un'offerta</H2>
<dl>
  <dt>kWh e Smc</dt><dd>Il kilowattora (kWh) misura l'energia elettrica consumata. Lo standard metro cubo (Smc) misura il gas: i metri cubi letti dal contatore vanno moltiplicati per un coefficiente (C), che sta in bolletta.</dd>
  <dt>Fasce F1, F2, F3 (luce)</dt><dd>Alcune offerte hanno prezzi diversi per fascia oraria: F1 = ore di punta (lun-ven di giorno), F2 = sere e sabato, F3 = notte, domenica e festivi. Un'offerta «monoraria» ha un solo prezzo. Se consumi soprattutto di notte o nel weekend, le fasce possono convenirti.</dd>
  <dt>Quota fissa</dt><dd>Costo mensile che paghi anche senza consumare nulla (a volte chiamato «commercializzazione»). Se consumi poco, pesa più del prezzo dell'energia: confrontala sempre.</dd>
  <dt>Quota potenza</dt><dd>Costo per kW di potenza impegnata, cioè il limite del tuo contatore (3 kW, 4,5 kW…). Quella di rete è regolata e uguale per tutti.</dd>
  <dt>Perdite di rete, dispacciamento, oneri di capacità</dt><dd>Componenti tecniche che, nelle offerte indicizzate luce, si sommano al PUN. Se non sono nel prezzo, vengono fatturate a parte: per questo l'app aggiunge una stima, così il confronto è equo.</dd>
  <dt>Bonus e sconti una tantum</dt><dd>Valgono una sola volta, di solito il primo anno. Un bonus di 60 € non rende conveniente un'offerta che costa 80 € l'anno in più dal secondo anno. L'app mostra sempre il risparmio anche <em>senza</em> bonus.</dd>
  <dt>Durata delle condizioni</dt><dd>Per quanto restano validi i prezzi. Alla scadenza il venditore può proporre nuove condizioni, spesso peggiori: segna la data e rivaluta.</dd>
  <dt>Offerta attuale</dt><dd>Quella che hai ora: è il metro di paragone per tutto il resto. Si ricava dalla tua ultima bolletta.</dd>
</dl>

<H2 id="verdetto">Come leggere il verdetto</H2>
<ul>
  <li><strong>«Conviene cambiare»</strong> compare solo se il risparmio stimato è di almeno <strong>30 €</strong> l'anno <em>e</em> di almeno <strong>5%</strong>. Sotto quella soglia il disturbo di cambiare (pratiche, rischio di errori) non vale la pena.</li>
  <li><strong>Il risparmio è una stima</strong>: parte dal tuo consumo annuo (ricavato dalle bollette) e, per gli indicizzati, da un prezzo di mercato ipotizzato. Se hai poche bollette, l'app te lo segnala.</li>
  <li><strong>Prova ±20%</strong>: ricalcolo con il mercato più basso e più alto del 20%. Se il vantaggio resta in entrambi i casi, è solido; se sparisce, dipende da come andrà il mercato.</li>
  <li><strong>Primo anno e dall'anno dopo</strong>: se la differenza senza bonus è piccola o negativa, il vantaggio è solo il bonus.</li>
  <li><strong>Condizioni importate</strong>: prezzi e condizioni delle offerte pubblicate vanno sempre verificati sul sito del venditore prima di scegliere.</li>
</ul>

<H2 id="telefono">Se ti chiamano per proporti un'offerta</H2>
<ol>
  <li><strong>Non decidere durante la telefonata.</strong> Dì che richiami. Chi propone un'offerta valida non ha fretta artificiale.</li>
  <li><strong>Chiedi nome del venditore, nome dell'offerta e il prezzo preciso</strong> (€/kWh o €/Smc, senza IVA), se è fisso o indicizzato, e lo spread.</li>
  <li><strong>Chiedi tutte le voci</strong>: quota fissa, bonus (quanto, quando arriva, a che condizioni), durata, cosa succede alla fine.</li>
  <li>Inseriscile in <Link className="font-bold text-accent underline" to="/proposal">Proposta</Link> e <strong>salvala</strong>: l'app dice se conviene e ti prepara l'elenco da controllare nel contratto.</li>
  <li>Diffida se: non vogliono dirti il prezzo per kWh/Smc, parlano solo di «sconto percentuale» senza base, o dicono «è la stessa offerta che hai già» senza mostrarla.</li>
</ol>

<H2 id="contratto">Prima di firmare</H2>
<ul>
  <li><strong>Leggi la scheda di confronto / scheda sintetica</strong> che il venditore deve darti: riporta prezzi e condizioni in forma standard. Controlla che coincida con quanto detto a voce.</li>
  <li><strong>Controlla ogni voce</strong> della pagina della proposta salvata (la tabella «Da verificare nel contratto»).</li>
  <li><strong>Tempi</strong>: un contratto concluso per telefono o a distanza non ti vincola finché non lo confermi per iscritto (firma o accettazione scritta). Dopo la conferma hai in genere <strong>14 giorni</strong> per ripensarci senza penali (diritto di recesso): conserva data e documenti.</li>
  <li><strong>Non toccare il resto</strong>: il cambio di venditore non comporta interruzioni di fornitura né cambia contatore o tubi.</li>
  <li>Conserva copia del contratto e annota la <strong>data in cui finiscono le condizioni</strong>: salvala come «Attivata il» sull'offerta attuale e ti avviso 60 giorni prima.</li>
</ul>
<p className="text-sm text-muted">Le informazioni giuridiche (tempi, recesso) sono indicative: valgono le condizioni scritte nel contratto e le norme vigenti. Per dubbi o contestazioni puoi rivolgerti allo Sportello per il consumatore Arera o a un'associazione dei consumatori.</p>
</div>

  );
}
