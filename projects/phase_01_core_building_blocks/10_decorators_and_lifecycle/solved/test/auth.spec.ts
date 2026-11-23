import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AdminController, LockedController } from '../src/auth/admin.controller.js';
import { createApp } from './helpers.js';

describe('Task 3: a composed decorator with applyDecorators', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [AdminController, LockedController] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('a route with @Auth("admin") answers 401 without a login: authentication runs first', async () => {
    const res = await request(app.getHttpServer()).get('/admin/dashboard').expect(401);

    expect(res.body.message).toBe('not logged in');
  });

  it('a logged-in user without the role gets 403', async () => {
    await request(app.getHttpServer()).get('/admin/dashboard').set('x-user', 'bob').expect(403);
    await request(app.getHttpServer()).get('/admin/dashboard').set('x-user', 'eve').expect(403);
  });

  it('a user with the role gets in', async () => {
    await request(app.getHttpServer()).get('/admin/dashboard').set('x-user', 'ada').expect(200, 'dashboard');
  });

  it('@Auth("admin", "editor") accepts either role', async () => {
    await request(app.getHttpServer()).get('/admin/articles').set('x-user', 'ada').expect(200);
    await request(app.getHttpServer()).get('/admin/articles').set('x-user', 'eve').expect(200);
    await request(app.getHttpServer()).get('/admin/articles').set('x-user', 'bob').expect(403);
  });

  it('a route without the decorator stays open', async () => {
    await request(app.getHttpServer()).get('/admin/open').expect(200, 'open');
  });

  it('the same decorator works on a class: every route of the controller is protected', async () => {
    await request(app.getHttpServer()).get('/locked/a').expect(401);
    await request(app.getHttpServer()).get('/locked/b').set('x-user', 'eve').expect(403);
    await request(app.getHttpServer()).get('/locked/a').set('x-user', 'ada').expect(200, 'a');
  });
});
