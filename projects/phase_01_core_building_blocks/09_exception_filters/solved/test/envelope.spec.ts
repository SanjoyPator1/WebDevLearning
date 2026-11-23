import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ShapesController } from '../src/envelope/shapes.controller.js';
import { createApp } from './helpers.js';

describe('Task 2: a custom filter for HttpException', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [ShapesController] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('uses the errorCode as the code, and adds the status and the path', async () => {
    const res = await request(app.getHttpServer()).get('/shapes/coded').expect(400);

    expect(res.body).toEqual({ status: 400, code: 'WEAK', message: 'too short', path: '/shapes/coded' });
  });

  it('keeps an array message as an array', async () => {
    const res = await request(app.getHttpServer()).get('/shapes/list').expect(400);

    expect(res.body).toEqual({
      status: 400,
      code: 'HTTP_400',
      message: ['a must be set', 'b must be set'],
      path: '/shapes/list',
    });
  });

  it('with no errorCode the code is HTTP_<status>', async () => {
    const res = await request(app.getHttpServer()).get('/shapes/plain404').expect(404);

    expect(res.body).toEqual({ status: 404, code: 'HTTP_404', message: 'Not Found', path: '/shapes/plain404' });
  });

  it('a response object without a message falls back to the exception message', async () => {
    const res = await request(app.getHttpServer()).get('/shapes/object').expect(422);

    expect(res.body).toEqual({ status: 422, code: 'HTTP_422', message: 'Http Exception', path: '/shapes/object' });
  });

  it('the path includes the query string', async () => {
    const res = await request(app.getHttpServer()).get('/shapes/coded?x=1').expect(400);

    expect(res.body.path).toBe('/shapes/coded?x=1');
  });

  it('a plain Error is not caught by this filter: Nest answers with its generic 500', async () => {
    const res = await request(app.getHttpServer()).get('/shapes/crash').expect(500);

    expect(res.body).toEqual({ statusCode: 500, message: 'Internal server error' });
  });
});
