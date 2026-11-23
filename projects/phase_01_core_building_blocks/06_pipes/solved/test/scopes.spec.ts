import request from 'supertest';
import { configureApp } from '../src/scopes/configure-app.js';
import { ScopesController } from '../src/scopes/scopes.controller.js';
import { createApp } from './helpers.js';

describe('Task 5: binding scopes and their order', () => {
  it('a route with all four scopes: global, controller, method, parameter, in that order', async () => {
    const { app } = await createApp([ScopesController], { setup: configureApp });

    const res = await request(app.getHttpServer()).get('/scopes/one/abc').expect(200);

    expect(res.text).toBe('abc-G-C-M-P');
    await app.close();
  });

  it('a route with only the global and controller scopes', async () => {
    const { app } = await createApp([ScopesController], { setup: configureApp });

    const res = await request(app.getHttpServer()).get('/scopes/two/abc').expect(200);

    expect(res.text).toBe('abc-G-C');
    await app.close();
  });

  it('guard: pipes of every scope skip @Headers(): the header value comes through unchanged', async () => {
    const { app } = await createApp([ScopesController], { setup: configureApp });

    const res = await request(app.getHttpServer()).get('/scopes/header').set('x-h', 'hv').expect(200);

    expect(res.text).toBe('hv');
    await app.close();
  });
});
