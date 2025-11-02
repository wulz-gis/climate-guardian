import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

/**
 * Vite configuration for Climate Guardian.
 *
 * - Disables HMR error overlay to keep UI unobstructed during development.
 * - Pins dev server port to 5174 to match current preview URL.
 */
export default defineConfig({
  plugins: [vue()],
  base: '/climate-guardian/',
  server: {
    port: 5174,
    hmr: {
      overlay: false,
    },
  },
})