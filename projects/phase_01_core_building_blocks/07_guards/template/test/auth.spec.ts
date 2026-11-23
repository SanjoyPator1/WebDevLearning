import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ProfileController } from '../src/auth/profile.controller.js';
import { TokenService } from '../src/auth/token.service.js';
import { createApp } from './helpers.js';

describe('Task 2: an async guard with a provider, rejecting with 401', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [ProfileController], providers: [TokenService] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('a valid token lets the request through and attaches the user to the request', async () => {
    const res = await request(app.getHttpServer()).get('/profile').set('authorization', 'Bearer t-ada').expect(200);

    expect(res.body).toEqual({ name: 'ada' });
  });

  it('another valid token gives another user: the guard looks the token up each time', async () => {
    const res = await request(app.getHttpServer()).get('/profile').set('authorization', 'Bearer t-bob').expect(200);

    expect(res.body).toEqual({ name: 'bob' });
  });

  it('a missing header is a 401, not a 403', async () => {
    const res = await request(app.getHttpServer()).get('/profile').expect(401);

    expect(res.body).toEqual({ message: 'missing bearer token', error: 'Unauthorized', statusCode: 401 });
  });

  it('a header that is not "Bearer <token>" is a 401 too', async () => {
    const res = await request(app.getHttpServer()).get('/profile').set('authorization', 'Basic t-ada').expect(401);

    expect(res.body.message).toBe('missing bearer token');
  });

  it('an unknown token is a 401 with its own message', async () => {
    const res = await request(app.getHttpServer()).get('/profile').set('authorization', 'Bearer nope').expect(401);

    expect(res.body).toEqual({ message: 'invalid token', error: 'Unauthorized', statusCode: 401 });
  });
});
