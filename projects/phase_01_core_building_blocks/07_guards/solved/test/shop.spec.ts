import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ShopModule } from '../src/shop/shop.module.js';
import { createApp } from './helpers.js';

describe('Task 4: a global guard through APP_GUARD, with an @Public() opt-out', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ imports: [ShopModule] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('a route with no decorator is private: 401 without the token', async () => {
    const res = await request(app.getHttpServer()).get('/shop/items').expect(401);

    expect(res.body).toEqual({ message: 'missing or invalid token', error: 'Unauthorized', statusCode: 401 });
  });

  it('the right token opens it, a wrong one does not', async () => {
    await request(app.getHttpServer()).get('/shop/items').set('x-token', 'let-me-in').expect(200);
    await request(app.getHttpServer()).get('/shop/items').set('x-token', 'nope').expect(401);
  });

  it('@Public(true) on a method opens that route', async () => {
    await request(app.getHttpServer()).get('/shop/health').expect(200, 'ok');
  });

  it('@Public(true) on a controller opens all of its routes', async () => {
    await request(app.getHttpServer()).get('/docs').expect(200, 'docs');
  });

  it('@Public(false) on a method closes it again inside a public controller (handler beats class)', async () => {
    await request(app.getHttpServer()).get('/docs/internal').expect(401);
    await request(app.getHttpServer()).get('/docs/internal').set('x-token', 'let-me-in').expect(200, 'internal docs');
  });

  it('the guard is global, but a path that matches no route is a 404, never a 401', async () => {
    await request(app.getHttpServer()).get('/nothing-here').expect(404);
  });
});
