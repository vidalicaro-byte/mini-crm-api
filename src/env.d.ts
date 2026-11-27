interface ImportMetaEnv {
  /** Base URL of the API. Defaults to "/api" (served by the mock API). */
  readonly VITE_API_URL?: string;
  /** Set to "false" to talk to a real backend instead of the mock API. */
  readonly VITE_ENABLE_MOCKS?: string;
  /** "true" or "false": show the one-click demo sign-in buttons. Defaults to on with the mock API. */
  readonly VITE_DEMO_ACCOUNTS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
