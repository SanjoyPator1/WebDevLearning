import { ConsoleLogger, Logger, type INestApplication, type LoggerService } from '@nestjs/common';
import { ExpressAdapter } from '@nestjs/platform-express';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { createServer, type AddressInfo } from 'node:net';
import { createApp, startApp, type CreateAppOptions } from '../src/create-app.js';

// Test helpers. Not part of this exercise.

/** Collects every Nest log line as "Context|message". */
class CapturingLogger implements LoggerService {
  readonly lines: string[] = [];
  log(message: unknown, context?: string) {
    this.lines.push(`${context ?? ''}|${String(message)}`);
  }
  warn(message: unknown, context?: string) {
    this.lines.push(`${context ?? ''}|${String(message)}`);
  }
  error(message: unknown, ...rest: unknown[]) {
    this.lines.push(`${String(rest.at(-1) ?? '')}|${String(message)}`);
  }
}

// Nest's logger is a process-wide global that NestFactory.create only changes when you pass a logger.
// Reset it before every test so one test's logger cannot leak into the next.
beforeEach(() => {
  Logger.overrideLogger(new ConsoleLogger());
});

const open: INestApplication[] = [];
async function start(options: CreateAppOptions = {}): Promise<{ app: INestApplication; url: string }> {
  const app = await createApp(options);
  open.push(app);
  // Port 0 asks the OS for a free port, so tests never collide.
  await app.listen(0, '127.0.0.1');
  return { app, url: await app.getUrl() };
}
afterEach(async () => {
  await Promise.all(open.splice(0).map((app) => app.close()));
  vi.restoreAllMocks();
});

const adapters = ['express', 'fastify'] as const;

// Task 1
describe('1. createApp builds the app but does not listen', () => {
  it('returns an app whose server is not listening yet', async () => {
    const app = await createApp();
    open.push(app);
    expect(app.getHttpServer().listening).toBe(false);
  });
});

// Task 2
describe.each(adapters)('2. adapter: %s', (adapter) => {
  it('runs on the requested adapter', async () => {
    const app = await createApp({ adapter });
    open.push(app);
    const expected = adapter === 'express' ? ExpressAdapter : FastifyAdapter;
    expect(app.getHttpAdapter()).toBeInstanceOf(expected);
  });

  it('serves the same route whichever adapter is used', async () => {
    const { url } = await start({ adapter });
    const res = await fetch(`${url}/health`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: 'ok' });
  });
});

describe('2. adapter default', () => {
  it('is express when no adapter is given', async () => {
    const app = await createApp();
    open.push(app);
    expect(app.getHttpAdapter()).toBeInstanceOf(ExpressAdapter);
  });
});

// Task 3
describe.each(adapters)('3. global prefix: %s', (adapter) => {
  it('puts every route under the prefix', async () => {
    const { url } = await start({ adapter, globalPrefix: 'api' });
    expect((await fetch(`${url}/api/health`)).status).toBe(200);
    expect((await fetch(`${url}/api/version`)).status).toBe(200);
    expect((await fetch(`${url}/health`)).status).toBe(404);
  });

  it('leaves excluded routes outside the prefix', async () => {
    const { url } = await start({ adapter, globalPrefix: 'api', excludeFromPrefix: ['health'] });
    expect((await fetch(`${url}/health`)).status).toBe(200);
    expect((await fetch(`${url}/api/health`)).status).toBe(404);
    expect((await fetch(`${url}/api/version`)).status).toBe(200);
    expect((await fetch(`${url}/version`)).status).toBe(404);
  });
});

// Task 4
describe.each(adapters)('4. CORS: %s', (adapter) => {
  const origin = 'https://app.example.com';

  it('sends no CORS headers when CORS is not configured', async () => {
    const { url } = await start({ adapter });
    const res = await fetch(`${url}/health`, { headers: { Origin: origin } });
    expect(res.headers.get('access-control-allow-origin')).toBeNull();
  });

  it('allows the configured origin on a normal request', async () => {
    const { url } = await start({ adapter, cors: { origin } });
    const res = await fetch(`${url}/health`, { headers: { Origin: origin } });
    expect(res.headers.get('access-control-allow-origin')).toBe(origin);
  });

  it('answers the preflight request with 204', async () => {
    const { url } = await start({ adapter, cors: { origin } });
    const res = await fetch(`${url}/health`, {
      method: 'OPTIONS',
      headers: { Origin: origin, 'Access-Control-Request-Method': 'GET' },
    });
    expect(res.status).toBe(204);
    expect(res.headers.get('access-control-allow-origin')).toBe(origin);
  });
});

// Task 5
describe('5. logging', () => {
  it('sends Nest startup lines to the supplied logger', async () => {
    const logger = new CapturingLogger();
    const app = await createApp({ logger });
    open.push(app);
    await app.init();
    expect(logger.lines).toContain('NestFactory|Starting Nest application...');
    expect(logger.lines).toContain('RouterExplorer|Mapped {/health, GET} route');
    expect(logger.lines).toContain('NestApplication|Nest application successfully started');
  });

  it('prints nothing when no logger is supplied', async () => {
    const write = vi.spyOn(process.stdout, 'write');
    const app = await createApp();
    open.push(app);
    await app.init();
    const nestOutput = write.mock.calls.filter(([chunk]) => String(chunk).includes('[Nest]'));
    expect(nestOutput).toHaveLength(0);
  });

  it('without bufferLogs, a logger attached after create misses the lines Nest wrote during create', async () => {
    const late = new CapturingLogger();
    const app = await createApp();
    open.push(app);
    app.useLogger(late);
    await app.init();
    // create() already wrote these two before the late logger existed.
    expect(late.lines).not.toContain('NestFactory|Starting Nest application...');
    expect(late.lines).not.toContain('InstanceLoader|AppModule dependencies initialized');
    // init() runs after useLogger, so these do arrive.
    expect(late.lines).toContain('NestApplication|Nest application successfully started');
  });

  it('with bufferLogs, replays the startup lines to a logger attached after create', async () => {
    const late = new CapturingLogger();
    const app = await createApp({ bufferLogs: true });
    open.push(app);
    app.useLogger(late);
    await app.init();
    expect(late.lines).toContain('NestFactory|Starting Nest application...');
    expect(late.lines).toContain('NestApplication|Nest application successfully started');
  });
});

// Task 6
describe.each(adapters)('6. startApp: %s', (adapter) => {
  it('listens on the PORT from the environment and returns a working URL', async () => {
    const app = await createApp({ adapter });
    open.push(app);
    const url = await startApp(app, { PORT: '0' });
    expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
    const res = await fetch(`${url}/health`);
    expect(res.status).toBe(200);
  });

  it('binds 0.0.0.0 by default, so a container can reach it', async () => {
    const app = await createApp({ adapter });
    open.push(app);
    await startApp(app, { PORT: '0' });
    const address = app.getHttpServer().address() as AddressInfo;
    expect(address.address).toBe('0.0.0.0');
  });

  it('lets HOST override the host', async () => {
    const app = await createApp({ adapter });
    open.push(app);
    await startApp(app, { PORT: '0', HOST: '127.0.0.1' });
    const address = app.getHttpServer().address() as AddressInfo;
    expect(address.address).toBe('127.0.0.1');
  });
});

// Task 7
describe('7. close()', () => {
  it('releases the port', async () => {
    const app = await createApp();
    await startApp(app, { PORT: '0' });
    const { port } = app.getHttpServer().address() as AddressInfo;
    await app.close();

    // If close() really released the port, a plain TCP server can take it.
    await new Promise<void>((resolve, reject) => {
      const probe = createServer();
      probe.once('error', reject);
      probe.listen(port, '0.0.0.0', () => probe.close(() => resolve()));
    });
  });
});
