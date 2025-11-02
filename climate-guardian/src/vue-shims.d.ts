/*
 * Vue Single File Component (.vue) type declarations
 *
 * Provides TypeScript module declarations so that imports of .vue files
 * are typed as Vue components. This resolves TS2307 errors during build
 * when importing SFCs like `import App from './App.vue'`.
 *
 * PEP 257 does not apply to TypeScript, but we keep comments clear.
 */
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, any>
  export default component
}