import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { BarChart3, BookOpen, Check, ChevronsUpDown, Lightbulb, MoreHorizontal, Receipt, Scale, SlidersHorizontal, Tag, House, UserRound, ShieldCheck, Settings2, type LucideIcon } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { Modal } from './Modal';
import { MessageList } from './ui';
import Footer from './Footer';
import { FOCUS_RING } from './styles';

interface Item { to: string; label: string; icon: LucideIcon; end?: boolean; match?: string }
const PRIMARY: Item[] = [
  { to: '/', label: 'Home', icon: House, end: true },
  { to: '/bills', label: 'Bollette', icon: Receipt },
  { to: '/offers', label: 'Offerte', icon: Tag },
  { to: '/compare/power', label: 'Confronto', icon: Scale, match: '/compare' },
];
const MORE: Item[] = [
  { to: '/history/power', label: 'Storico', icon: BarChart3, match: '/history' },
  { to: '/proposal', label: 'Proposta', icon: Lightbulb },
  { to: '/guide', label: 'Guida', icon: BookOpen },
  { to: '/settings', label: 'Impostazioni', icon: SlidersHorizontal },
];
const ACCOUNT: Item = { to: '/account', label: 'Account', icon: UserRound };
const USERS: Item = { to: '/users', label: 'Utenti', icon: ShieldCheck };
const inSection = (path: string, i: Item) => (i.end ? path === i.to : path.startsWith(i.match ?? i.to));

export function BrandMark({ className = 'h-8 w-8' }: { className?: string }) {
  return (
    <svg className={`${className} flex-none text-accent`} viewBox="0 0 32 32" aria-hidden focusable="false">
      <rect width="32" height="32" rx="9" fill="currentColor" />
      <path d="M9 6h14v20l-3.5-2.2L16 26l-3.5-2.2L9 26z" fill="#fff" />
      <path d="m12.5 14 2.5 2.5 4.5-5" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
const Brand = () => <Link to="/" className={`inline-flex items-center gap-2.5 text-xl font-extrabold tracking-tight text-fg no-underline ${FOCUS_RING}`}><BrandMark /><span>Bollette</span></Link>;

function NavItem({ item, path, onNavigate, variant }: { item: Item; path: string; onNavigate?: () => void; variant: 'bar' | 'side' | 'sheet' }) {
  const active = inSection(path, item);
  const base = `flex items-center rounded-block no-underline transition-colors ${FOCUS_RING}`;
  const look = variant === 'bar'
    ? `min-h-[3.5rem] min-w-0 flex-1 flex-col justify-center gap-0.5 px-1 py-1 text-center text-xs font-bold leading-tight lg:hidden`
    : `min-h-[2.75rem] gap-3.5 px-3 py-2 ${variant === 'sheet' ? 'min-h-[3rem] text-base font-bold' : 'text-base font-bold'}`;
  const color = active ? 'bg-accent-soft text-accent' : variant === 'bar' ? 'text-muted hover:text-accent' : 'text-fg hover:bg-calm';
  return (
    <NavLink to={item.to} onClick={onNavigate} aria-current={active ? 'page' : undefined} className={`${base} ${look} ${color}`}>
      <item.icon className={`${variant === 'bar' ? 'h-6 w-6' : 'h-[1.35rem] w-[1.35rem]'} flex-none ${active || variant === 'bar' ? '' : 'text-muted'}`} aria-hidden />
      <span>{item.label}</span>
    </NavLink>
  );
}

/** Il profilo attivo (un appartamento) decide cosa si vede in ogni pagina: sta in cima, come contesto, non in mezzo alle voci di navigazione. */
function ProfileMenu({ align = 'left', full = false }: { align?: 'left' | 'right'; full?: boolean }) {
  const { profiles, profile, switchProfile } = useApp();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menuId = useId();
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const away = (e: Event) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') { setOpen(false); trigger.current?.focus(); } };
    document.addEventListener('pointerdown', away); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', esc); };
  }, [open]);
  const choose = (id: number) => { setOpen(false); if (id !== profile.id) void switchProfile(id); trigger.current?.focus(); };
  const row = `flex min-h-[44px] w-full items-center gap-2.5 rounded-block px-3 py-2 text-left text-base no-underline hover:bg-calm ${FOCUS_RING}`;
  return (
    <div ref={root} className={`relative ${full ? 'w-full' : 'min-w-0'}`}>
      <button ref={trigger} type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls={open ? menuId : undefined}
        className={`flex min-h-[44px] w-full items-center gap-2.5 rounded-block bg-calm px-3 py-1.5 text-left font-bold transition-colors hover:bg-accent-soft ${FOCUS_RING}`}>
        <House className="h-[1.2rem] w-[1.2rem] flex-none text-accent" aria-hidden />
        <span className="min-w-0 flex-1 truncate"><span className="sr-only">Profilo attivo: </span>{profile.name}</span>
        <ChevronsUpDown className="h-4 w-4 flex-none text-muted" aria-hidden />
      </button>
      {open && (
        <div id={menuId} role="group" aria-label="Cambia profilo"
          className={`absolute top-full z-30 mt-1.5 w-max min-w-full max-w-[min(20rem,calc(100vw-1.5rem))] animate-fade rounded-card border border-edge bg-surface p-1 shadow-lift ${align === 'right' ? 'right-0' : 'left-0'}`}>
          {profiles.map((p) => (
            <button key={p.id} type="button" onClick={() => choose(p.id)} aria-current={p.id === profile.id ? 'true' : undefined} className={`${row} ${p.id === profile.id ? 'font-bold text-accent' : ''}`}>
              <Check className={`h-4 w-4 flex-none ${p.id === profile.id ? '' : 'invisible'}`} aria-hidden /><span className="min-w-0 truncate">{p.name}</span>
            </button>))}
          <Link to="/profiles" className={`${row} mt-1 border-t border-edge text-muted`}><Settings2 className="h-4 w-4 flex-none" aria-hidden />Gestisci i profili</Link>
        </div>)}
    </div>
  );
}

export default function Layout(): ReactNode {
  const { pathname } = useLocation();
  const { clearStale } = useApp();
  const [more, setMore] = useState(false);
  const { enabled, user } = useAuth();
  const items = enabled ? [...MORE, ACCOUNT, ...(user?.is_admin ? [USERS] : [])] : MORE;  // con il login spento non ci sono account da gestire
  useEffect(() => { clearStale(); setMore(false); window.scrollTo({ top: 0 }); }, [pathname, clearStale]);
  const moreActive = items.some((i) => inSection(pathname, i));

  return (
    <div className="min-h-screen lg:pl-sidebar">
      <header className="flex items-center justify-between gap-3 border-t-4 border-accent bg-surface px-4 py-2 shadow-panel lg:hidden"><Brand /><div className="min-w-0 max-w-[55%]"><ProfileMenu align="right" /></div></header>

      <nav aria-label="Principale"
        className="fixed inset-x-0 bottom-0 z-20 flex items-stretch justify-around gap-1 bg-surface px-2 pb-[calc(.35rem+env(safe-area-inset-bottom))] pt-1.5 shadow-[0_-2px_12px_rgb(15_60_56/.12)] lg:inset-y-0 lg:right-auto lg:w-sidebar lg:flex-col lg:justify-start lg:gap-1 lg:overflow-auto lg:rounded-br-2xl lg:px-3 lg:pb-5 lg:pt-6 lg:shadow-[inset_0_4px_0_var(--accent),var(--shadow)]">
        <div className="hidden px-2 pb-3 pt-1 lg:block"><Brand /></div>
        <div className="mb-3 hidden px-1 lg:block"><ProfileMenu full /></div>
        {PRIMARY.map((i) => <NavItem key={i.to} item={i} path={pathname} variant="bar" />)}
        {PRIMARY.map((i) => <div key={i.to} className="hidden lg:block"><NavItem item={{ ...i }} path={pathname} variant="side" /></div>)}
        <button type="button" onClick={() => setMore(true)} aria-haspopup="dialog" aria-current={moreActive ? 'page' : undefined}
          className={`flex min-h-[3.5rem] min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-block px-1 py-1 text-center text-xs font-bold leading-tight lg:hidden ${FOCUS_RING} ${moreActive ? 'bg-accent-soft text-accent' : 'text-muted hover:text-accent'}`}>
          <MoreHorizontal className="h-6 w-6" aria-hidden /><span>Altro</span>
        </button>
        <div className="mt-2 hidden flex-1 flex-col gap-1 border-t border-edge pt-3 lg:flex">
          {items.map((i) => <NavItem key={i.to} item={i} path={pathname} variant="side" />)}
        </div>
      </nav>

      <Modal open={more} onClose={() => setMore(false)} title="Altro" compact>
        <div className="flex flex-col gap-1 pb-2">
          {items.map((i) => <NavItem key={i.to} item={i} path={pathname} variant="sheet" onNavigate={() => setMore(false)} />)}
        </div>
      </Modal>

      <main className="mx-auto max-w-[60rem] px-3 pb-8 pt-4 sm:px-4 lg:px-8 lg:pb-12 lg:pt-8">
        <MessageList />
        <Outlet />
      </main>
      <Footer className="pb-[calc(var(--bar-h,4.25rem)+env(safe-area-inset-bottom))] lg:pb-0" />
    </div>
  );
}
