import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { FOCUS_RING } from './styles';

// Modali come in Formando PerCorsi: su telefono (<1024px) un foglio che sale dal basso (95% dell'altezza, 500ms);
// da desktop un riquadro centrale (angoli 12px, padding 32px, ombra «sopra tutto», fondo grigio scuro al 75%).
// Si chiudono sempre con lo stesso CloseButton (cerchio tenue da 48px con la X, tratto 3).

export function CloseButton({ onClick, disabled, label = 'Chiudi', className = '' }: { onClick: () => void; disabled?: boolean; label?: string; className?: string }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
      className={`group flex h-12 w-12 flex-none items-center justify-center rounded-full bg-accent-soft transition-all hover:bg-accent disabled:pointer-events-none disabled:opacity-50 ${FOCUS_RING} ${className}`}>
      <X className="h-7 w-7 text-accent transition-colors group-hover:text-on-accent" strokeWidth={3} aria-hidden />
    </button>
  );
}

let scrollLocks = 0;
const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

/** Comportamento comune: blocco dello scroll, Esc, fuoco dentro il pannello e ritorno al punto di partenza. */
function useDialog(open: boolean, onClose: () => void) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const before = document.activeElement as HTMLElement | null;
    if (scrollLocks++ === 0) document.body.style.overflow = 'hidden';
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopPropagation(); onClose(); return; }
      if (e.key !== 'Tab' || !panel.current) return;
      const items = [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (!items.length) { e.preventDefault(); return; }
      const first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      if (--scrollLocks === 0) document.body.style.overflow = '';
      before?.focus?.();
    };
  }, [open, onClose]);
  return panel;
}

/** Monta con un piccolo ritardo per far partire la transizione, e smonta a transizione finita. */
function useTransitionMount(open: boolean, ms = 500) {
  const [mounted, setMounted] = useState(open);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (open) { setMounted(true); const t = setTimeout(() => setVisible(true), 10); return () => clearTimeout(t); }
    setVisible(false);
    const t = setTimeout(() => setMounted(false), ms);
    return () => clearTimeout(t);
  }, [open, ms]);
  return { mounted, visible };
}

interface ModalProps { open: boolean; title: string; onClose: () => void; children: ReactNode; compact?: boolean; wide?: boolean }

/** Modale di contenuto: foglio dal basso su telefono, riquadro centrale su desktop. `compact` = altezza del contenuto. */
export function Modal({ open, title, onClose, children, compact = false, wide = false }: ModalProps) {
  const { mounted, visible } = useTransitionMount(open);
  const panel = useDialog(mounted && open, onClose);
  const titleId = useId();
  if (!mounted) return null;
  return createPortal(
    <div className={`fixed inset-0 z-50 flex items-end bg-black/50 transition-opacity duration-500 lg:items-center lg:justify-center lg:bg-gray-800/75 lg:p-4 ${visible ? 'opacity-100' : 'opacity-0'}`}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div ref={panel} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
        className={`flex w-full flex-col bg-surface p-4 outline-none transition-all duration-500 rounded-t-lg ${compact ? 'max-h-[85%]' : 'h-[95%]'} lg:h-auto lg:max-h-[85vh] lg:rounded-xl lg:p-8 lg:shadow-top ${wide ? 'lg:max-w-3xl' : 'lg:max-w-lg'} ${visible ? 'translate-y-0 lg:scale-100' : 'translate-y-full lg:translate-y-0 lg:scale-95'}`}>
        <div className="mb-2 flex items-center gap-2 pt-2 lg:mb-4 lg:pt-0">
          <h2 id={titleId} className="w-full pl-14 text-center text-2xl font-bold lg:text-xl lg:text-accent">{title}</h2>
          <CloseButton onClick={onClose} />
        </div>
        <div className="min-h-0 flex-1 overflow-auto">{children}</div>
      </div>
    </div>, document.body);
}

export interface ConfirmOptions { title?: string; message: string; confirmLabel?: string; cancelLabel?: string; danger?: boolean }

/** Conferma sempre al centro (anche su telefono): messaggio breve e due bottoni affiancati, «Annulla» tenue + azione piena. */
export function ConfirmModal({ open, title, message, confirmLabel = 'Elimina', cancelLabel = 'Annulla', danger = true, busy = false, onConfirm, onCancel }:
  ConfirmOptions & { open: boolean; busy?: boolean; onConfirm: () => void; onCancel: () => void }) {
  const { mounted, visible } = useTransitionMount(open, 200);
  const panel = useDialog(mounted && open, onCancel);
  const titleId = useId();
  if (!mounted) return null;
  return createPortal(
    <div className={`fixed inset-0 z-[60] flex items-center justify-center bg-gray-800/75 p-4 transition-opacity duration-200 ${visible ? 'opacity-100' : 'opacity-0'}`}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div ref={panel} role="alertdialog" aria-modal="true" aria-labelledby={title ? titleId : undefined} tabIndex={-1}
        className={`flex w-full max-w-md flex-col items-center gap-4 rounded-xl bg-surface p-8 shadow-top outline-none transition-transform duration-200 ${visible ? 'scale-100' : 'scale-95'}`}>
        {title && <h2 id={titleId} className="text-center text-xl font-bold text-accent">{title}</h2>}
        <p className="text-center">{message}</p>
        <div className="mt-2 flex w-full gap-4">
          <button type="button" onClick={onCancel} className={`w-full rounded-block bg-accent-soft p-2 font-bold text-accent transition-colors hover:bg-accent hover:text-on-accent ${FOCUS_RING}`}>{cancelLabel}</button>
          <button type="button" onClick={onConfirm} aria-disabled={busy}
            className={`w-full rounded-block p-2 font-bold transition ${danger ? 'bg-bad text-white' : 'bg-accent text-on-accent'} hover:brightness-110 aria-disabled:cursor-wait aria-disabled:opacity-70 ${FOCUS_RING}`}>{confirmLabel}</button>
        </div>
      </div>
    </div>, document.body);
}

