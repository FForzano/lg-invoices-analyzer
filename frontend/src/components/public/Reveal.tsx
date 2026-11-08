import { useEffect, useRef, useState, type ReactNode } from 'react';

/** Appare con una dissolvenza quando entra nella vista. Senza IntersectionObserver o con «riduci animazioni» è subito visibile. */
export default function Reveal({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(() => typeof IntersectionObserver === 'undefined' || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    if (seen || !ref.current) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold: 0.15 });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [seen]);
  return <div ref={ref} className={`transition-all duration-700 ease-out ${seen ? 'translate-y-0 opacity-100' : 'translate-y-5 opacity-0'} ${className}`}>{children}</div>;
}
