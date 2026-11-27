import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import LinearProgress from '@mui/material/LinearProgress';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { useEffect, useState, type ReactNode } from 'react';
import { waitForServer } from '../api/serverWake';

type Status = 'checking' | 'waking' | 'ready' | 'failed';

interface ServerWakeGateProps {
  children: ReactNode;
  /** Off with the mock API, which is always awake. */
  enabled?: boolean;
  /** How long to wait before telling the visitor the server is waking up. */
  noticeDelayMs?: number;
  /** Passed to waitForServer; tests shorten it. */
  waitOptions?: Parameters<typeof waitForServer>[0];
}

/**
 * Holds the app until the API is up. The demo API sleeps when idle (free hosting), so the first
 * visit can take about a minute: instead of a page full of spinners and errors, the visitor
 * gets one screen that says what is going on. When the server is already awake, nothing shows.
 */
export function ServerWakeGate({
  children,
  enabled = import.meta.env.VITE_ENABLE_MOCKS === 'false',
  noticeDelayMs = 1_500,
  waitOptions,
}: ServerWakeGateProps) {
  const [status, setStatus] = useState<Status>(enabled ? 'checking' : 'ready');
  const [attempt, setAttempt] = useState(0);
  // Read once: an inline options object must not restart the wait on every render.
  const [options] = useState(waitOptions);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    const notice = setTimeout(() => {
      setStatus((current) => (current === 'checking' ? 'waking' : current));
    }, noticeDelayMs);

    waitForServer({ ...options, signal: controller.signal })
      .then((ready) => setStatus(ready ? 'ready' : 'failed'))
      .catch(() => {
        // Aborted: the component went away.
      })
      .finally(() => clearTimeout(notice));

    return () => {
      clearTimeout(notice);
      controller.abort();
    };
  }, [enabled, noticeDelayMs, options, attempt]);

  if (status === 'ready') return children;
  if (status === 'checking') return null;

  return (
    <Box component="main" sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2 }}>
      <Paper variant="outlined" sx={{ p: 4, maxWidth: 440, width: '100%' }}>
        {status === 'waking' ? (
          // <output> is a live region (role "status"): screen readers announce the wait.
          <Box component="output" sx={{ display: 'block' }}>
            <Typography variant="h5" component="h1" gutterBottom>
              Acordando o servidor
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>
              A API de demonstração fica num plano gratuito e dorme quando ninguém usa. A primeira
              visita leva até um minuto; depois disso, tudo fica rápido.
            </Typography>
            <LinearProgress aria-label="Aguardando o servidor" />
          </Box>
        ) : (
          <>
            <Typography variant="h5" component="h1" gutterBottom>
              Servidor indisponível
            </Typography>
            <Alert severity="error" sx={{ mb: 3 }}>
              Não foi possível conectar ao servidor. Tente de novo em alguns instantes.
            </Alert>
            <Button
              variant="contained"
              onClick={() => {
                setStatus('waking');
                setAttempt((n) => n + 1);
              }}
            >
              Tentar de novo
            </Button>
          </>
        )}
      </Paper>
    </Box>
  );
}
