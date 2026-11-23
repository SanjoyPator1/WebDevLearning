import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { VaultController } from '../src/apikey/vault.controller.js';
import { CallCounter } from '../src/common/call-counter.js';
import { createApp } from './helpers.js';

describe('Task 1: a guard that returns true or false', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [VaultController], providers: [CallCounter] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('lets a request with the right key through to the handler', async () => {
    const res = await request(app.getHttpServer()).get('/vault').set('x-api-key', 'secret').expect(200);

    expect(res.body).toEqual({ secret: 'swordfish', hit: 1 });
  });

  it('answers 403 with the standard body when the key is missing', async () => {
    const res = await request(app.getHttpServer()).get('/vault').expect(403);

    expect(res.body).toEqual({ message: 'Forbidden resource', error: 'Forbidden', statusCode: 403 });
  });

  it('answers 403 when the key is wrong', async () => {
    await request(app.getHttpServer()).get('/vault').set('x-api-key', 'guess').expect(403);
  });

  it('never runs the handler for a denied request', async () => {
    await request(app.getHttpServer()).get('/vault').expect(403);
    await request(app.getHttpServer()).get('/vault/keys').set('x-api-key', 'guess').expect(403);

    expect(app.get(CallCounter).calls).toBe(0);
  });

  it('bound once on the controller, it protects every route of it', async () => {
    await request(app.getHttpServer()).get('/vault/keys').expect(403);
    const ok = await request(app.getHttpServer()).get('/vault/keys').set('x-api-key', 'secret').expect(200);

    expect(ok.body).toEqual({ keys: ['k1', 'k2'], hit: 1 });
  });
});
