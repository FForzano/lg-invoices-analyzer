import { useEffect, useState, type ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { BarChart3, BookOpen, Lightbulb, MoreHorizontal, Receipt, Scale, SlidersHorizontal, Tag, Users, House, type LucideIcon } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Modal } from './Modal';
import { MessageList } from './ui';
import { FOCUS_RING, fieldClass } from './styles';

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
  { to: '/profiles', label: 'Profili', icon: Users },
];
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

function ProfileSwitch({ onDone }: { onDone?: () => void }) {
  const { profiles, profile, switchProfile } = useApp();
  if (profiles.length < 2) return null;
  return (
    <form className="flex flex-wrap items-center gap-2 px-1 pt-3" onSubmit={(e) => e.preventDefault()}>
      <select aria-label="Profilo attivo" value={profile.id} className={`${fieldClass} min-w-0 flex-1`}
        onChange={(e) => { void switchProfile(Number(e.target.value)); onDone?.(); }}>
        {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>
    </form>
  );
}

export default function Layout(): ReactNode {
  const { pathname } = useLocation();
  const { clearStale } = useApp();
  const [more, setMore] = useState(false);
  useEffect(() => { clearStale(); setMore(false); window.scrollTo({ top: 0 }); }, [pathname, clearStale]);
  const moreActive = MORE.some((i) => inSection(pathname, i));

  return (
    <div className="min-h-screen lg:pl-sidebar">
      <header className="flex items-center gap-2.5 border-t-4 border-accent bg-surface px-4 py-2 shadow-panel lg:hidden"><Brand /></header>

      <nav aria-label="Principale"
        className="fixed inset-x-0 bottom-0 z-20 flex items-stretch justify-around gap-1 bg-surface px-2 pb-[calc(.35rem+env(safe-area-inset-bottom))] pt-1.5 shadow-[0_-2px_12px_rgb(15_60_56/.12)] lg:inset-y-0 lg:right-auto lg:w-sidebar lg:flex-col lg:justify-start lg:gap-1 lg:overflow-auto lg:rounded-br-2xl lg:px-3 lg:pb-5 lg:pt-6 lg:shadow-[inset_0_4px_0_var(--accent),var(--shadow)]">
        <div className="hidden px-2 pb-5 pt-1 lg:block"><Brand /></div>
        {PRIMARY.map((i) => <NavItem key={i.to} item={i} path={pathname} variant="bar" />)}
        {PRIMARY.map((i) => <div key={i.to} className="hidden lg:block"><NavItem item={{ ...i }} path={pathname} variant="side" /></div>)}
        <button type="button" onClick={() => setMore(true)} aria-haspopup="dialog" aria-current={moreActive ? 'page' : undefined}
          className={`flex min-h-[3.5rem] min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-block px-1 py-1 text-center text-xs font-bold leading-tight lg:hidden ${FOCUS_RING} ${moreActive ? 'bg-accent-soft text-accent' : 'text-muted hover:text-accent'}`}>
          <MoreHorizontal className="h-6 w-6" aria-hidden /><span>Altro</span>
        </button>
        <div className="mt-2 hidden flex-1 flex-col gap-1 border-t border-edge pt-3 lg:flex">
          {MORE.map((i) => <NavItem key={i.to} item={i} path={pathname} variant="side" />)}
          <div className="mt-auto"><ProfileSwitch /></div>
        </div>
      </nav>

      <Modal open={more} onClose={() => setMore(false)} title="Altro" compact>
        <div className="flex flex-col gap-1 pb-2">
          <ProfileSwitch onDone={() => setMore(false)} />
          {MORE.map((i) => <NavItem key={i.to} item={i} path={pathname} variant="sheet" onNavigate={() => setMore(false)} />)}
        </div>
      </Modal>

      <main className="mx-auto max-w-[60rem] px-3 pb-[calc(var(--bar-h,4.25rem)+1.5rem+env(safe-area-inset-bottom))] pt-4 sm:px-4 lg:px-8 lg:pb-12 lg:pt-8">
        <MessageList />
        <Outlet />
      </main>
    </div>
  );
}
