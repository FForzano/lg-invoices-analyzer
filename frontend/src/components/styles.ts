// Stili condivisi dei controlli (come src/components/form/styles.ts di FPC, con l'accento teal).
export const FOCUS_RING = 'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface';
const LIFT = 'transition duration-200 hover:-translate-y-px hover:shadow-lift active:translate-y-0 active:shadow-none';
export const PRIMARY_BUTTON = `inline-flex min-h-[44px] items-center justify-center gap-2 rounded-field bg-accent px-6 py-2 font-bold text-on-accent no-underline hover:bg-accent-deep aria-disabled:cursor-wait aria-disabled:opacity-70 ${LIFT} ${FOCUS_RING}`;
export const SOFT_BUTTON = `inline-flex min-h-[44px] items-center justify-center gap-2 rounded-field bg-accent-soft px-6 py-2 font-bold text-accent no-underline transition-colors hover:bg-accent hover:text-on-accent aria-disabled:cursor-wait aria-disabled:opacity-70 ${FOCUS_RING}`;
export const TEXT_BUTTON = `inline-flex min-h-[44px] items-center rounded font-bold text-accent underline-offset-4 hover:underline ${FOCUS_RING}`;
export const DANGER_LINK = `rounded text-muted transition-colors hover:text-bad focus-visible:text-bad ${FOCUS_RING}`;
export const fieldClass = 'min-h-[44px] w-full rounded-field border border-line bg-surface px-3 py-2 text-base text-fg transition-colors focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent';
export const CARD = 'rounded-card border border-edge bg-surface px-5 pb-3 pt-1 shadow-panel';
