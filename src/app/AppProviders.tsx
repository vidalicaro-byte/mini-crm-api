import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { createQueryClient } from '../api/queryClient';
import { AuthProvider } from '../features/auth/AuthProvider';
import { theme } from '../theme/theme';
import { ServerWakeGate } from './ServerWakeGate';

interface AppProvidersProps {
  children: ReactNode;
  /** Tests inject their own client; the app creates one. */
  queryClient?: QueryClient;
}

export function AppProviders({ children, queryClient }: AppProvidersProps) {
  const [defaultClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient ?? defaultClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <ServerWakeGate>
          <AuthProvider>{children}</AuthProvider>
        </ServerWakeGate>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
