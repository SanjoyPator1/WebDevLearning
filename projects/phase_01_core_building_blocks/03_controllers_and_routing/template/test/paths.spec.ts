import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { PathsController } from '../src/paths/paths.controller.js';
import { createApp } from './helpers.js';

describe('Task 6: PathsController, Express 5 route paths', () => {
  let app: INestApplication;
  let warnings: string[];

  beforeEach(async () => {
    ({ app, warnings } = await createApp([PathsController]));
  });

  afterEach(async () => {
    await app.close();
  });

  describe('named wildcard', () => {
    it('GET /static/*path answers the matched segments joined back together', async () => {
      const res = await request(app.getHttpServer()).get('/static/css/site.css').expect(200);

      expect(res.text).toBe('css/site.css');
    });

    it('the route is written in the Express 5 syntax, so Nest has nothing to auto-convert', () => {
      expect(warnings.filter((message) => message.startsWith('Unsupported route path'))).toEqual([]);
    });

    it('a named wildcard needs at least one segment, so GET /static/ is a 404', async () => {
      await request(app.getHttpServer()).get('/static/').expect(404);
    });
  });

  describe('optional segment', () => {
    it('GET /docs/:lang answers the default page', async () => {
      const res = await request(app.getHttpServer()).get('/docs/en').expect(200);

      expect(res.body).toEqual({ lang: 'en', page: 'index' });
    });

    it('GET /docs/:lang/:page answers that page, through the same route', async () => {
      const res = await request(app.getHttpServer()).get('/docs/en/intro').expect(200);

      expect(res.body).toEqual({ lang: 'en', page: 'intro' });
    });

    it('the optional group is one segment, so a third segment is a 404', async () => {
      await request(app.getHttpServer()).get('/docs/en/intro/extra').expect(404);
    });
  });
});
