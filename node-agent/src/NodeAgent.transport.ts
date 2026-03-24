export interface TransportResponse<T = unknown> {
  readonly ok: boolean;
  readonly status: number;
  readonly data: T | null;
  readonly error: string | null;
}

export interface NodeAgentTransport {
  post<T = unknown>(path: string, body: unknown): Promise<TransportResponse<T>>;
  get<T = unknown>(path: string): Promise<TransportResponse<T>>;
}

export interface HttpTransportOptions {
  token?: string;
}

export function createHttpTransport(baseUrl: string, options?: HttpTransportOptions): NodeAgentTransport {
  async function request<T>(method: string, path: string, body?: unknown): Promise<TransportResponse<T>> {
    try {
      const url = `${baseUrl}${path}`;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (options?.token) {
        headers["x-daedalus-token"] = options.token;
      }
      const opts: RequestInit = {
        method,
        headers,
      };
      if (body !== undefined) opts.body = JSON.stringify(body);

      const res = await fetch(url, opts);
      const data = res.headers.get("content-type")?.includes("json")
        ? await res.json()
        : null;

      return { ok: res.ok, status: res.status, data: data as T, error: res.ok ? null : `HTTP ${res.status}` };
    } catch (err: any) {
      return { ok: false, status: 0, data: null, error: err?.message ?? "Network error" };
    }
  }

  return {
    post<T>(path: string, body: unknown) { return request<T>("POST", path, body); },
    get<T>(path: string) { return request<T>("GET", path); },
  };
}

export function createMockTransport(
  handlers: Record<string, (body?: unknown) => unknown> = {},
): NodeAgentTransport & { calls: Array<{ method: string; path: string; body?: unknown }> } {
  const calls: Array<{ method: string; path: string; body?: unknown }> = [];

  async function handle<T>(method: string, path: string, body?: unknown): Promise<TransportResponse<T>> {
    calls.push({ method, path, body });
    const handler = handlers[`${method} ${path}`] ?? handlers[path];
    if (handler) {
      const data = handler(body) as T;
      return { ok: true, status: 200, data, error: null };
    }
    return { ok: true, status: 200, data: null, error: null };
  }

  return {
    calls,
    post<T>(path: string, body: unknown) { return handle<T>("POST", path, body); },
    get<T>(path: string) { return handle<T>("GET", path); },
  };
}
