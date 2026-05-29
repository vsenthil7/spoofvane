// Vite client env typing (subset) so import.meta.env is typed under strict mode.
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
