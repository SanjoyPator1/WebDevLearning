import request from 'supertest';
import { configureApp } from '../src/scopes/configure-app.js';
import { ScopesController } from '../src/scopes/scopes.controller.js';
import { trace } from '../src/scopes/trace.js';
import { createApp } from './helpers.js';

describe('Task 5: binding scopes, order and short-circuiting', () => {
  beforeEach(() => {
    trace.length = 0;
  });

  it('global, then controller, then method, then the handler', async () => {
    const app = await createApp({ controllers: [ScopesController], setup: configureApp });

    await request(app.getHttpServer()).get('/scopes/one').expect(200, 'one');

    expect(trace).toEqual(['global', 'controller', 'method', 'handler']);
    await app.close();
  });

  it('guards on one route run in the order given, and the first denial stops the rest', async () => {
    const app = await createApp({ controllers: [ScopesController], setup: configureApp });

    const res = await request(app.getHttpServer()).get('/scopes/two').expect(403);

    expect(res.body.message).toBe('Forbidden resource');
    expect(trace).toEqual(['global', 'controller', 'first', 'second']);
    await app.close();
  });

  it('a route with no method guard still gets the global and controller ones', async () => {
    const app = await createApp({ controllers: [ScopesController], setup: configureApp });

    await request(app.getHttpServer()).get('/scopes/three').expect(200, 'three');

    expect(trace).toEqual(['global', 'controller', 'handler']);
    await app.close();
  });
});
