import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../mocks/server';
import { ServerWakeGate } from './ServerWakeGate';

const url = 'https://api.example.com/health';
const fast = { url, retryDelayMs: 5, attemptTimeoutMs: 200 };

describe('ServerWakeGate', () => {
  it('renders the app right away when disabled (mock API)', () => {
    render(<ServerWakeGate enabled={false}>app</ServerWakeGate>);
    expect(screen.getByText('app')).toBeInTheDocument();
  });

  it('shows nothing extra when the server is already awake', async () => {
    server.use(http.get(url, () => HttpResponse.json({ status: 'ok' })));
    render(
      <ServerWakeGate enabled waitOptions={fast}>
        app
      </ServerWakeGate>,
    );
    expect(await screen.findByText('app')).toBeInTheDocument();
    expect(screen.queryByText('Acordando o servidor')).not.toBeInTheDocument();
  });

  it('explains the wait while the server wakes up, then shows the app', async () => {
    let calls = 0;
    server.use(
      http.get(url, () => {
        calls += 1;
        return calls < 4 ? HttpResponse.error() : HttpResponse.json({ status: 'ok' });
      }),
    );
    render(
      <ServerWakeGate enabled noticeDelayMs={0} waitOptions={{ ...fast, retryDelayMs: 30 }}>
        app
      </ServerWakeGate>,
    );
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Acordando o servidor' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('até um minuto');
    expect(await screen.findByText('app')).toBeInTheDocument();
  });

  it('offers to try again when the server never answers', async () => {
    let up = false;
    server.use(
      http.get(url, () => (up ? HttpResponse.json({ status: 'ok' }) : HttpResponse.error())),
    );
    render(
      <ServerWakeGate enabled noticeDelayMs={0} waitOptions={{ ...fast, giveUpAfterMs: 20 }}>
        app
      </ServerWakeGate>,
    );
    const retry = await screen.findByRole('button', { name: 'Tentar de novo' });
    expect(screen.getByText(/Não foi possível conectar ao servidor/)).toBeInTheDocument();

    up = true;
    await userEvent.click(retry);
    expect(await screen.findByText('app')).toBeInTheDocument();
  });
});
