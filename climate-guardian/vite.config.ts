import { defineConfig } from 'vite'

/**
 * Vite configuration for Climate Guardian.
 *
 * - Disables HMR error overlay to keep UI unobstructed during development.
 * - Pins dev server port to 5174 to match current preview URL.
 */
export default defineConfig({
  server: {
    port: 5174,
    hmr: {
      overlay: false,
    },
  },
})