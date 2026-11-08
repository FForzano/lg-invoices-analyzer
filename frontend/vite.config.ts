import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// In sviluppo `npm run dev` inoltra /api a Flask (flask run, porta 5001); in produzione Flask serve dist/.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:5001' } },
  preview: { proxy: { '/api': 'http://localhost:5001' } },
  build: { chunkSizeWarningLimit: 700 },
  test: { environment: 'node' },
});
