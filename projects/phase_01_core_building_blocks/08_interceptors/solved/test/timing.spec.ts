import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AuditLog } from '../src/common/audit-log.js';
import { WorkController } from '../src/timing/work.controller.js';
import { createApp } from './helpers.js';

describe('Task 2: code before and after the handler (tap, finalize)', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [WorkController], providers: [AuditLog] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('writes start, ok and done around a successful handler', async () => {
    await request(app.getHttpServer()).get('/work/ok/10').expect(200, 'done');

    expect(app.get(AuditLog).entries).toEqual(['start GET /work/ok/10', 'ok', 'done']);
  });

  it('sets x-elapsed-ms to the time the handler took', async () => {
    const res = await request(app.getHttpServer()).get('/work/ok/60').expect(200);

    const elapsed = Number(res.headers['x-elapsed-ms']);
    expect(Number.isFinite(elapsed)).toBe(true);
    expect(elapsed).toBeGreaterThanOrEqual(55);
    expect(elapsed).toBeLessThan(400);
  });

  it('on failure it writes error and done, and the client still gets the handler error unchanged', async () => {
    const res = await request(app.getHttpServer()).get('/work/fail').expect(400);

    expect(res.body).toEqual({ message: 'failed on purpose', error: 'Bad Request', statusCode: 400 });
    expect(app.get(AuditLog).entries).toEqual(['start GET /work/fail', 'error', 'done']);
  });

  it('two overlapping requests are timed separately: the start time is not shared state', async () => {
    const [slow, fast] = await Promise.all([
      request(app.getHttpServer()).get('/work/ok/200'),
      (async () => {
        await new Promise((resolve) => setTimeout(resolve, 60));
        return request(app.getHttpServer()).get('/work/ok/10');
      })(),
    ]);

    expect(Number(slow.headers['x-elapsed-ms'])).toBeGreaterThanOrEqual(190);
    expect(Number(fast.headers['x-elapsed-ms'])).toBeLessThan(100);
  });
});
