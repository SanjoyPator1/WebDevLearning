import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { StrictController } from '../src/strict/strict.controller.js';
import { createApp } from './helpers.js';

describe('Task 3: pipe options', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([StrictController]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('both routes still accept an integer and hand it over as a number', async () => {
    const a = await request(app.getHttpServer()).get('/strict/status/7').expect(200);
    const b = await request(app.getHttpServer()).get('/strict/named/7').expect(200);

    expect(a.body).toEqual({ id: 7 });
    expect(b.body).toEqual({ id: 7 });
  });

  it('/strict/status answers 422 with the default message', async () => {
    const res = await request(app.getHttpServer()).get('/strict/status/abc').expect(422);

    expect(res.body).toEqual({
      message: 'Validation failed (numeric string is expected)',
      error: 'Unprocessable Entity',
      statusCode: 422,
    });
  });

  it('/strict/named answers 400 with its own message', async () => {
    const res = await request(app.getHttpServer()).get('/strict/named/abc').expect(400);

    expect(res.body).toEqual({ message: 'id must be an integer', error: 'Bad Request', statusCode: 400 });
  });
});
