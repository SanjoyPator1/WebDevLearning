import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { EchoController } from '../src/echo/echo.controller.js';
import { createApp } from './helpers.js';

describe('Task 2: EchoController, reading the request', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([EchoController]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('@Headers("x-token") reads one request header', async () => {
    const res = await request(app.getHttpServer()).get('/echo/headers').set('X-Token', 'abc').expect(200);

    expect(res.body).toEqual({ token: 'abc' });
  });

  it('a missing header arrives as undefined', async () => {
    const res = await request(app.getHttpServer()).get('/echo/headers').expect(200);

    expect(res.body).toEqual({});
  });

  it('@Query() without a name returns the whole query object', async () => {
    const res = await request(app.getHttpServer()).get('/echo/query?a=1&b=2').expect(200);

    expect(res.body).toEqual({ a: '1', b: '2' });
  });

  it('a repeated query key becomes an array', async () => {
    const res = await request(app.getHttpServer()).get('/echo/query?tag=x&tag=y').expect(200);

    expect(res.body).toEqual({ tag: ['x', 'y'] });
  });

  it('guard: Express 5 does not nest query keys, "a[b]" stays a literal key', async () => {
    const res = await request(app.getHttpServer()).get('/echo/query?a[b]=c').expect(200);

    expect(res.body).toEqual({ 'a[b]': 'c' });
  });

  it('@Param() without a name returns every route parameter', async () => {
    const res = await request(app.getHttpServer()).get('/echo/one/two').expect(200);

    expect(res.body).toEqual({ first: 'one', second: 'two' });
  });

  it('@Req() gives the underlying Express request', async () => {
    const res = await request(app.getHttpServer()).get('/echo/request?x=1').expect(200);

    expect(res.body).toEqual({ method: 'GET', path: '/echo/request', url: '/echo/request?x=1' });
  });
});
