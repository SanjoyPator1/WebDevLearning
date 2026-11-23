import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { PagesController } from '../src/paging/paging.controller.js';
import { createApp } from './helpers.js';

describe('Task 1: ParseIntPipe and DefaultValuePipe', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([PagesController]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('GET /pages/:id hands the handler a real number', async () => {
    const res = await request(app.getHttpServer()).get('/pages/5').expect(200);

    expect(res.body).toEqual({ id: 5, type: 'number' });
  });

  it('GET /pages/:id answers 400 with the pipe message when the id is not an integer', async () => {
    const res = await request(app.getHttpServer()).get('/pages/abc').expect(400);

    expect(res.body).toEqual({
      message: 'Validation failed (numeric string is expected)',
      error: 'Bad Request',
      statusCode: 400,
    });
    await request(app.getHttpServer()).get('/pages/5.5').expect(400);
  });

  it('GET /pages uses the defaults when the query is empty, and they are numbers', async () => {
    const res = await request(app.getHttpServer()).get('/pages').expect(200);

    expect(res.body).toEqual({ page: 1, limit: 10, pageType: 'number', limitType: 'number' });
  });

  it('GET /pages converts the values that are given', async () => {
    const res = await request(app.getHttpServer()).get('/pages?page=3&limit=20').expect(200);

    expect(res.body).toEqual({ page: 3, limit: 20, pageType: 'number', limitType: 'number' });
  });

  it('GET /pages answers 400 for a value that is not an integer', async () => {
    await request(app.getHttpServer()).get('/pages?page=x').expect(400);
  });

  it('an EMPTY value is not "missing": ?page= is a 400, the default does not apply', async () => {
    await request(app.getHttpServer()).get('/pages?page=').expect(400);
  });
});
