/** Formati italiani: separatore migliaia = spazio, decimali = virgola (come le macro Jinja `eur` e `num`). */
const fix = (x: number, d: number) => {
  const [int, dec] = Math.abs(x).toFixed(d).split('.');
  return (x < 0 ? '-' : '') + int.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (dec ? ',' + dec : '');
};
export const num = (x: number | null | undefined, d = 2) => (x == null ? '–' : fix(x, d));
export const eur = (x: number | null | undefined) => (x == null ? '–' : `${fix(x, 2)} €`);
export const pctSigned = (x: number | null | undefined) => (x == null ? null : `${x > 0 ? '+' : x < 0 ? '-' : ''}${Math.abs(x).toFixed(1).replace('.', ',')}%`);
export const commodityLabel = (c: string) => (c === 'power' ? 'Luce' : 'Gas');
export const unitOf = (c: string) => (c === 'power' ? 'kWh' : 'Smc');
