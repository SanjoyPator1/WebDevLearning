import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { facts, trace } from '../src/lifecycle/components.js';
import { configureLifecycle } from '../src/lifecycle/configure-lifecycle.js';
import { LifecycleModule } from '../src/lifecycle/lifecycle.module.js';
import {
  deniedPath,
  handlerFailPath,
  okPath,
  pipeFailPath,
  statusSeenInGuard,
  statusSeenInInterceptor,
  unknownPath,
} from '../src/lifecycle/predictions.js';
import { createApp } from './helpers.js';

// The application is real and given. Your predictions in src/lifecycle/predictions.ts are compared with
// what it actually does. When one is wrong the message shows the actual trace.

describe('Task 4: the request lifecycle, predicted and then confirmed', () => {
  let app: INestApplication;

  beforeEach(async () => {
    trace.length = 0;
    delete facts.statusInGuard;
    delete facts.statusInInterceptor;
    app = await createApp({ imports: [LifecycleModule], setup: configureLifecycle });
  });

  afterEach(async () => {
    await app.close();
  });

  it('a successful request', async () => {
    await request(app.getHttpServer()).get('/life/ok/1').expect(200);

    expect(okPath).toEqual(trace);
  });

  it('a request that a guard denies', async () => {
    await request(app.getHttpServer()).get('/life/denied/1').expect(403);

    expect(deniedPath).toEqual(trace);
  });

  it('a request whose parameter pipe throws', async () => {
    await request(app.getHttpServer()).get('/life/pipefail/1').expect(400);

    expect(pipeFailPath).toEqual(trace);
  });

  it('a request whose handler throws', async () => {
    await request(app.getHttpServer()).get('/life/handlerfail/1').expect(400);

    expect(handlerFailPath).toEqual(trace);
  });

  it('a path that matches no route', async () => {
    await request(app.getHttpServer()).get('/nothing-here').expect(404);

    expect(unknownPath).toEqual(trace);
  });

  it('the status code a guard sees', async () => {
    await request(app.getHttpServer()).get('/life/status').expect(202);

    expect(statusSeenInGuard).toBe(facts.statusInGuard);
  });

  it('the status code an interceptor sees before the handler', async () => {
    await request(app.getHttpServer()).get('/life/status').expect(202);

    expect(statusSeenInInterceptor).toBe(facts.statusInInterceptor);
  });
});
