import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ReplyController } from '../src/reply/reply.controller.js';
import { createApp } from './helpers.js';

describe('Task 3: ReplyController, shaping the response', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([ReplyController]));
  });

  afterEach(async () => {
    await app.close();
  });

  describe('status codes', () => {
    it('POST /reply/search answers 200 instead of the POST default 201', async () => {
      const res = await request(app.getHttpServer()).post('/reply/search').expect(200);

      expect(res.body).toEqual({ matches: 0 });
    });

    it('DELETE /reply/:id answers 204 and sends no body, although the handler returns one', async () => {
      const res = await request(app.getHttpServer()).delete('/reply/7').expect(204);

      expect(res.text).toBe('');
    });
  });

  describe('response headers', () => {
    it('GET /reply/cached sets two response headers', async () => {
      const res = await request(app.getHttpServer()).get('/reply/cached').expect(200);

      expect(res.text).toBe('fresh');
      expect(res.headers['cache-control']).toBe('public, max-age=60');
      expect(res.headers['x-reply']).toBe('cached');
    });
  });

  describe('redirects', () => {
    it('GET /reply/old redirects permanently (301) to /reply/new', async () => {
      const res = await request(app.getHttpServer()).get('/reply/old').expect(301);

      expect(res.headers['location']).toBe('/reply/new');
    });

    it('GET /reply/go redirects with the default 302 to /reply/new', async () => {
      const res = await request(app.getHttpServer()).get('/reply/go').expect(302);

      expect(res.headers['location']).toBe('/reply/new');
    });

    it('GET /reply/go?to= lets the handler override both the url and the status', async () => {
      const res = await request(app.getHttpServer()).get('/reply/go?to=/echo/x').expect(307);

      expect(res.headers['location']).toBe('/echo/x');
    });
  });
});
