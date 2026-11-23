import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ScopedModule } from '../src/scoped/scoped.module.js';
import { createApp } from './helpers.js';

describe('Task 3: forRoutes with a method, and exclude', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([ScopedModule]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('runs for GET /scoped', async () => {
    const res = await request(app.getHttpServer()).get('/scoped').expect(200);

    expect(res.headers['x-mark']).toBe('yes');
  });

  it('runs for the parameter route GET /scoped/:id', async () => {
    const res = await request(app.getHttpServer()).get('/scoped/7').expect(200);

    expect(res.text).toBe('item 7');
    expect(res.headers['x-mark']).toBe('yes');
  });

  it('runs for POST /scoped', async () => {
    const res = await request(app.getHttpServer()).post('/scoped').expect(201);

    expect(res.headers['x-mark']).toBe('yes');
  });

  it('does NOT run for GET /scoped/health', async () => {
    const res = await request(app.getHttpServer()).get('/scoped/health').expect(200);

    expect(res.text).toBe('ok');
    expect(res.headers['x-mark']).toBeUndefined();
  });

  it('still runs for POST /scoped/health: the exclusion is for one method only', async () => {
    const res = await request(app.getHttpServer()).post('/scoped/health').expect(201);

    expect(res.text).toBe('reported');
    expect(res.headers['x-mark']).toBe('yes');
  });

  it('does not run for another controller', async () => {
    const res = await request(app.getHttpServer()).get('/elsewhere').expect(200);

    expect(res.headers['x-mark']).toBeUndefined();
  });
});
