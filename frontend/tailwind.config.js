/** Token del design: stessi nomi e valori di DESIGN.md. I colori sono variabili CSS (tema chiaro/scuro in index.css). */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)', surface: 'var(--surface)', fg: 'var(--fg)', muted: 'var(--muted)',
        line: 'var(--line)', edge: 'var(--edge)', calm: 'var(--calm-bg)',
        accent: 'var(--accent)', 'accent-deep': 'var(--accent-deep)', 'accent-soft': 'var(--accent-soft)', 'on-accent': 'var(--on-accent)',
        warn: 'var(--warn)', good: 'var(--good)', 'good-bg': 'var(--good-bg)', bad: 'var(--bad)',
        sticker: 'var(--sticker)', 'sticker-ink': 'var(--sticker-ink)',
      },
      fontFamily: { sans: ['Figtree', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'sans-serif'] },
      boxShadow: { panel: 'var(--shadow)', lift: 'var(--shadow-up)', top: '0 25px 50px -12px rgb(0 0 0 / .25)' },
      borderRadius: { field: '12px', card: '12px', block: '8px' },
      spacing: { bar: '4.25rem', sidebar: '15rem' },
      keyframes: {
        stamp: { from: { transform: 'rotate(-7deg) scale(1.3)', opacity: '0' }, to: { transform: 'rotate(-2deg)', opacity: '1' } },
        fade: { from: { opacity: '0' }, to: { opacity: '1' } },
      },
      animation: { stamp: 'stamp .35s cubic-bezier(.16,1,.3,1) both', fade: 'fade .2s ease-out both' },
    },
  },
  plugins: [],
};
