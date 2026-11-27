import { BASE_URL } from './client';

/** The API's liveness check: `/health` next to the `/api` prefix (it sits outside it). */
export function healthUrl(baseUrl: string = BASE_URL, origin: string = window.location.origin) {
  return new URL(`${baseUrl.replace(/\/api\/?$/, '')}/health`, origin).toString();
}

export interface WaitOptions {
  url?: string;
  signal?: AbortSignal;
  /** How long one attempt may take before it is abandoned and retried. */
  attemptTimeoutMs?: number;
  /** Pause between attempts that failed quickly. */
  retryDelayMs?: number;
  /** Total time before giving up. */
  giveUpAfterMs?: number;
}

function delay(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(timer);
        reject(signal.reason as Error);
      },
      { once: true },
    );
  });
}

/**
 * Polls the health check until the API answers. A free Render service sleeps when idle and
 * takes about a minute to wake up; meanwhile a request may hang, fail, or get Render's HTML
 * loading page (without CORS headers, so `fetch` throws). Any of those means "not yet".
 * Resolves `true` once the API is up, `false` after `giveUpAfterMs`.
 */
export async function waitForServer({
  url = healthUrl(),
  signal,
  attemptTimeoutMs = 15_000,
  retryDelayMs = 2_000,
  giveUpAfterMs = 120_000,
}: WaitOptions = {}): Promise<boolean> {
  const deadline = Date.now() + giveUpAfterMs;
  while (Date.now() < deadline) {
    const attempt = AbortSignal.any([
      AbortSignal.timeout(attemptTimeoutMs),
      ...(signal ? [signal] : []),
    ]);
    try {
      const response = await fetch(url, { signal: attempt, cache: 'no-store' });
      if (response.ok) return true;
    } catch (error) {
      if (signal?.aborted) throw error;
    }
    await delay(retryDelayMs, signal);
  }
  return false;
}
