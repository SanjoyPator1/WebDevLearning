import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { SecuredModule } from '../src/secured/secured.module.js';
import { SecuredService } from '../src/secured/secured.service.js';
import { createApp } from './helpers.js';

describe('Task 6: a middleware that answers by itself', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([SecuredModule]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('answers 401 with a JSON message when the key is missing', async () => {
    const res = await request(app.getHttpServer()).get('/secured').expect(401);

    expect(res.body).toEqual({ message: 'invalid api key' });
  });

  it('answers 401 when the key is wrong', async () => {
    await request(app.getHttpServer()).get('/secured').set('x-api-key', 'guess').expect(401);
  });

  it('never runs the handler for a rejected request', async () => {
    await request(app.getHttpServer()).get('/secured').expect(401);
    await request(app.getHttpServer()).get('/secured').set('x-api-key', 'guess').expect(401);

    expect(app.get(SecuredService).calls).toBe(0);
  });

  it('lets a request with the right key through to the handler, once', async () => {
    const res = await request(app.getHttpServer()).get('/secured').set('x-api-key', 'secret').expect(200);

    expect(res.body).toEqual({ calls: 1 });
    expect(app.get(SecuredService).calls).toBe(1);
  });
});
