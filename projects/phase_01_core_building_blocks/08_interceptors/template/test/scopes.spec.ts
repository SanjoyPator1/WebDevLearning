import request from 'supertest';
import { configureApp } from '../src/scopes/configure-app.js';
import { trace } from '../src/scopes/named.interceptor.js';
import { ScopesController } from '../src/scopes/scopes.controller.js';
import { ElsewhereModule } from '../src/stamp/elsewhere.module.js';
import { StampModule } from '../src/stamp/stamp.module.js';
import { createApp } from './helpers.js';

describe('Tasks 5a and 5b: binding scopes, and the mirror image of before and after', () => {
  beforeEach(() => {
    trace.length = 0;
  });

  it('global, controller, method on the way in; the reverse on the way out', async () => {
    const app = await createApp({ controllers: [ScopesController], setup: configureApp });

    await request(app.getHttpServer()).get('/scopes/one').expect(200, 'one');

    expect(trace).toEqual([
      'global:before', 'controller:before', 'method:before', 'handler',
      'method:after', 'controller:after', 'global:after',
    ]);
    await app.close();
  });

  it('two interceptors in one @UseInterceptors: in order going in, reversed coming out', async () => {
    const app = await createApp({ controllers: [ScopesController], setup: configureApp });

    await request(app.getHttpServer()).get('/scopes/two').expect(200, 'two');

    expect(trace).toEqual([
      'global:before', 'controller:before', 'first:before', 'second:before', 'handler',
      'second:after', 'first:after', 'controller:after', 'global:after',
    ]);
    await app.close();
  });

  it('a route with no method interceptor still gets the global and controller ones', async () => {
    const app = await createApp({ controllers: [ScopesController], setup: configureApp });

    await request(app.getHttpServer()).get('/scopes/three').expect(200, 'three');

    expect(trace).toEqual(['global:before', 'controller:before', 'handler', 'controller:after', 'global:after']);
    await app.close();
  });
});

describe('Task 5c: a global interceptor with dependency injection (APP_INTERCEPTOR)', () => {
  it('StampInterceptor receives StampService and stamps the controller of its own module', async () => {
    const app = await createApp({ imports: [StampModule] });

    const res = await request(app.getHttpServer()).get('/stamped').expect(200);

    expect(res.headers['x-stamp']).toBe('stamp-1');
    await app.close();
  });

  it('it is global: a controller of a module that never imports StampModule is stamped too', async () => {
    const app = await createApp({ imports: [StampModule, ElsewhereModule] });

    const res = await request(app.getHttpServer()).get('/elsewhere').expect(200);

    expect(res.text).toBe('elsewhere');
    expect(res.headers['x-stamp']).toBe('stamp-1');
    await app.close();
  });
});
