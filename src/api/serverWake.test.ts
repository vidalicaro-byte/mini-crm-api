import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../mocks/server';
import { healthUrl, waitForServer } from './serverWake';

const url = 'https://api.example.com/health';
const fast = { url, retryDelayMs: 1, attemptTimeoutMs: 200 };

describe('healthUrl', () => {
  it('puts /health next to the /api prefix', () => {
    expect(healthUrl('https://api.example.com/api', 'https://app.example.com')).toBe(
      'https://api.example.com/health',
    );
    expect(healthUrl('https://api.example.com/api/', 'https://app.example.com')).toBe(
      'https://api.example.com/health',
    );
  });

  it('resolves a relative base against the page origin', () => {
    expect(healthUrl('/api', 'https://app.example.com')).toBe('https://app.example.com/health');
  });
});

describe('waitForServer', () => {
  it('resolves as soon as the health check answers', async () => {
    server.use(http.get(url, () => HttpResponse.json({ status: 'ok' })));
    await expect(waitForServer(fast)).resolves.toBe(true);
  });

  it('keeps trying while the server is waking up', async () => {
    let calls = 0;
    server.use(
      http.get(url, () => {
        calls += 1;
        if (calls === 1) return HttpResponse.error(); // connection refused
        if (calls === 2) return new HttpResponse('<html>loading</html>', { status: 503 });
        return HttpResponse.json({ status: 'ok' });
      }),
    );
    await expect(waitForServer(fast)).resolves.toBe(true);
    expect(calls).toBe(3);
  });

  it('gives up after the time limit', async () => {
    server.use(http.get(url, () => HttpResponse.error()));
    await expect(waitForServer({ ...fast, giveUpAfterMs: 30 })).resolves.toBe(false);
  });

  it('stops when aborted', async () => {
    server.use(http.get(url, () => HttpResponse.error()));
    const controller = new AbortController();
    const waiting = waitForServer({ ...fast, retryDelayMs: 50, signal: controller.signal });
    controller.abort(new DOMException('left the page', 'AbortError'));
    await expect(waiting).rejects.toThrow('left the page');
  });
});
