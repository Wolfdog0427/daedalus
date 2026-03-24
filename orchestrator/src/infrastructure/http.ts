import http from 'node:http';
import type { Logger } from './logging.js';
import type { OrchestratorConfig } from './config.js';

export interface HttpRequest extends http.IncomingMessage {
  body?: any;
  params: Record<string, string>;
}

export interface HttpResponse extends http.ServerResponse {
  json(body: any): void;
  status(code: number): HttpResponse;
}

type HttpMethod = 'GET' | 'POST' | 'PATCH';
type RouteHandler = (req: HttpRequest, res: HttpResponse) => void;

export interface HttpServer extends http.Server {
  get(path: string, handler: RouteHandler): void;
  post(path: string, handler: RouteHandler): void;
  patch(path: string, handler: RouteHandler): void;
}

interface HttpServerDeps {
  logger: Logger;
  config: OrchestratorConfig;
  orchestrator: any;
  eventBus: any;
  operatorContext: any;
}

interface Route {
  method: HttpMethod;
  path: string;
  segments: string[];
  handler: RouteHandler;
}

function matchRoute(
  route: Route,
  method: string,
  urlPath: string,
): Record<string, string> | null {
  if (route.method !== method) return null;
  const urlSegments = urlPath.split('/');
  if (route.segments.length !== urlSegments.length) return null;

  const params: Record<string, string> = {};
  for (let i = 0; i < route.segments.length; i++) {
    const seg = route.segments[i];
    if (seg.startsWith(':')) {
      params[seg.slice(1)] = decodeURIComponent(urlSegments[i]);
    } else if (seg !== urlSegments[i]) {
      return null;
    }
  }
  return params;
}

function needsBody(method: string): boolean {
  return method === 'POST' || method === 'PATCH';
}

export function createHttpServer(_deps: HttpServerDeps): HttpServer {
  const routes: Route[] = [];

  function addRoute(method: HttpMethod, path: string, handler: RouteHandler) {
    routes.push({ method, path, segments: path.split('/'), handler });
  }

  const server = http.createServer(
    (rawReq: http.IncomingMessage, rawRes: http.ServerResponse) => {
      const req = rawReq as HttpRequest;
      const res = rawRes as HttpResponse;
      req.params = {};

      res.json = (body: any) => {
        const payload = JSON.stringify(body);
        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Content-Length', Buffer.byteLength(payload));
        res.end(payload);
      };

      res.status = (code: number) => {
        res.statusCode = code;
        return res;
      };

      const urlPath = (req.url ?? '').split('?')[0];
      let matched: Route | null = null;

      for (const route of routes) {
        const params = matchRoute(route, req.method ?? '', urlPath);
        if (params) {
          req.params = params;
          matched = route;
          break;
        }
      }

      if (!matched) {
        res.statusCode = 404;
        res.json({ error: 'Not found' });
        return;
      }

      if (needsBody(req.method ?? '')) {
        let data = '';
        req.on('data', (chunk: Buffer) => {
          data += chunk;
        });
        req.on('end', () => {
          try {
            req.body = data ? JSON.parse(data) : undefined;
          } catch {
            req.body = undefined;
          }
          matched!.handler(req, res);
        });
      } else {
        matched.handler(req, res);
      }
    },
  ) as HttpServer;

  server.get = (path, handler) => addRoute('GET', path, handler);
  server.post = (path, handler) => addRoute('POST', path, handler);
  server.patch = (path, handler) => addRoute('PATCH', path, handler);

  return server;
}
