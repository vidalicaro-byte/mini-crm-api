/**
 * Credentials of the demo users, served by the mock API and by the demo deployment of the
 * real API. The login page offers them as one-click shortcuts: by default only while the mock
 * API is on; VITE_DEMO_ACCOUNTS ("true" or "false") overrides that, e.g. for the demo server.
 */
export const DEMO_PASSWORD = 'demo1234';

export const demoAccounts = [
  { label: 'Entrar como administradora', email: 'marina@minicrm.demo' },
  { label: 'Entrar como vendedor', email: 'rafael@minicrm.demo' },
] as const;

const demoAccountsFlag = import.meta.env.VITE_DEMO_ACCOUNTS;

export const demoAccountsEnabled = demoAccountsFlag
  ? demoAccountsFlag === 'true'
  : import.meta.env.VITE_ENABLE_MOCKS !== 'false';
