import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AuditLog } from '../src/common/audit-log.js';
import { LimitsController } from '../src/limits/limits.controller.js';
import { createApp } from './helpers.js';

describe('Tasks 3a and 3b: timeout and catchError', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [LimitsController], providers: [AuditLog] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('3a: a handler slower than 50 ms is answered with 408', async () => {
    const res = await request(app.getHttpServer()).get('/limits/slow').expect(408);

    expect(res.body).toEqual({ message: 'Request Timeout', statusCode: 408 });
  });

  it('3a: a fast handler is not affected', async () => {
    await request(app.getHttpServer()).get('/limits/fast').expect(200, 'quick');
  });

  it('3a: other errors pass through unchanged', async () => {
    const res = await request(app.getHttpServer()).get('/limits/fails').expect(400);

    expect(res.body.message).toBe('original');
  });

  it('3a: the 408 does NOT cancel the handler: it finishes in the background', async () => {
    await request(app.getHttpServer()).get('/limits/slow').expect(408);
    expect(app.get(AuditLog).entries).toEqual([]);

    await new Promise((resolve) => setTimeout(resolve, 250));

    expect(app.get(AuditLog).entries).toEqual(['slow-finished']);
  });

  it('3b: a plain Error becomes a 502 with a safe message', async () => {
    const res = await request(app.getHttpServer()).get('/limits/upstream').expect(502);

    expect(res.body).toEqual({ message: 'upstream failed', error: 'Bad Gateway', statusCode: 502 });
    expect(JSON.stringify(res.body)).not.toContain('hunter2');
  });

  it('3b: an HttpException is left as it is', async () => {
    const res = await request(app.getHttpServer()).get('/limits/bad').expect(400);

    expect(res.body.message).toBe('client mistake');
  });
});
