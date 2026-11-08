import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { ConfirmModal, type ConfirmOptions } from '../components/Modal';

type Ask = (o: ConfirmOptions) => Promise<boolean>;
const Ctx = createContext<Ask | null>(null);

/** `const confirm = useConfirm(); if (await confirm({ message: '…' })) …` al posto di window.confirm. */
export const useConfirm = () => { const v = useContext(Ctx); if (!v) throw new Error('useConfirm fuori da ConfirmProvider'); return v; };

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [opts, setOpts] = useState<ConfirmOptions | null>(null);
  const [open, setOpen] = useState(false);
  const resolver = useRef<(v: boolean) => void>();
  const ask = useCallback<Ask>((o) => new Promise((resolve) => { resolver.current = resolve; setOpts(o); setOpen(true); }), []);
  const done = (v: boolean) => { setOpen(false); resolver.current?.(v); };
  return (
    <Ctx.Provider value={ask}>
      {children}
      {opts && <ConfirmModal open={open} {...opts} onConfirm={() => done(true)} onCancel={() => done(false)} />}
    </Ctx.Provider>
  );
}
