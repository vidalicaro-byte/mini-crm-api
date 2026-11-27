import type { z } from 'zod';
import { apiErrorBodySchema } from './schemas';
import { tokenStore } from './tokenStore';

export const BASE_URL: string = import.meta.env.VITE_API_URL ?? '/api';

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'ApiError';
    this.status = status;
  }
}

type QueryParams = Record<string, string | number | undefined>;

interface RequestOptions<S extends z.ZodType> {
  /** Validates the response body; the return type is inferred from it. */
  schema: S;
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  query?: QueryParams;
  body?: unknown;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: QueryParams) {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value));
  }
  return url;
}

/**
 * Typed fetch wrapper. Failures become ApiError, and the response is validated against
 * the schema so the rest of the app can trust the data it receives.
 */
export async function apiRequest<S extends z.ZodType>(
  path: string,
  { schema, method = 'GET', query, body, signal }: RequestOptions<S>,
): Promise<z.output<S>> {
  const headers = new Headers();
  if (body !== undefined) headers.set('Content-Type', 'application/json');
  const token = tokenStore.get();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      signal,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'Não foi possível conectar ao servidor.', { cause: error });
  }

  if (!response.ok) {
    const errorBody = apiErrorBodySchema.safeParse(await response.json().catch(() => null));
    throw new ApiError(
      response.status,
      errorBody.success ? errorBody.data.message : `Erro inesperado (${response.status}).`,
    );
  }

  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) {
    throw new ApiError(response.status, 'O servidor enviou uma resposta inesperada.', {
      cause: parsed.error,
    });
  }
  return parsed.data;
}
