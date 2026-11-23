import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { Cached } from '../src/memo/cached.decorator.js';
import { ProductCounter, ProductsController } from '../src/memo/products.controller.js';
import { createApp } from './helpers.js';

describe('Task 4a: the @Cached marker', () => {
  it('Cached is made by Reflector.createDecorator, so it carries a KEY', () => {
    expect(typeof (Cached as unknown as { KEY?: unknown }).KEY).toBe('string');
  });
});

describe('Task 4b: an interceptor that answers without calling the handler', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [ProductsController], providers: [ProductCounter] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('the second request for the same url is answered from the cache: the handler runs once', async () => {
    const first = await request(app.getHttpServer()).get('/products/1').expect(200);
    const second = await request(app.getHttpServer()).get('/products/1').expect(200);

    expect(first.body).toEqual({ id: '1', n: 1 });
    expect(second.body).toEqual({ id: '1', n: 1 });
    expect(app.get(ProductCounter).calls).toBe(1);
  });

  it('another url is another key', async () => {
    await request(app.getHttpServer()).get('/products/1').expect(200);
    const other = await request(app.getHttpServer()).get('/products/2').expect(200);

    expect(other.body).toEqual({ id: '2', n: 2 });
  });

  it('the query string is part of the key', async () => {
    await request(app.getHttpServer()).get('/products/1?x=1').expect(200);
    const other = await request(app.getHttpServer()).get('/products/1?x=2').expect(200);

    expect(other.body.n).toBe(2);
  });

  it('a route that is not marked @Cached() always runs its handler', async () => {
    const a = await request(app.getHttpServer()).get('/products/live').expect(200);
    const b = await request(app.getHttpServer()).get('/products/live').expect(200);

    expect([a.body.n, b.body.n]).toEqual([1, 2]);
  });
});
