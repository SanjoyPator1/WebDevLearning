import request from 'supertest';
import { configureApp } from '../src/scopes/configure-app.js';
import { trace } from '../src/scopes/named.filter.js';
import { PlainController, ScopesController } from '../src/scopes/scopes.controller.js';
import { createApp } from './helpers.js';

describe('Task 5: binding scopes and the precedence between filters', () => {
  beforeEach(() => {
    trace.length = 0;
  });

  it('method beats controller beats global: only the method filter runs', async () => {
    const app = await createApp({ controllers: [ScopesController, PlainController], setup: configureApp });

    const res = await request(app.getHttpServer()).get('/scopes/one').expect(400);

    expect(res.body).toEqual({ by: 'method' });
    expect(trace).toEqual(['method']);
    await app.close();
  });

  it('with no method filter the controller filter handles it, and the global one never runs', async () => {
    const app = await createApp({ controllers: [ScopesController, PlainController], setup: configureApp });

    const res = await request(app.getHttpServer()).get('/scopes/two').expect(400);

    expect(res.body).toEqual({ by: 'controller' });
    expect(trace).toEqual(['controller']);
    await app.close();
  });

  it('with two filters on one route, the LAST one listed handles it', async () => {
    const app = await createApp({ controllers: [ScopesController, PlainController], setup: configureApp });

    const res = await request(app.getHttpServer()).get('/scopes/four').expect(400);

    expect(res.body).toEqual({ by: 'second' });
    expect(trace).toEqual(['second']);
    await app.close();
  });

  it('a controller with no filter of its own falls back to the global one', async () => {
    const app = await createApp({ controllers: [ScopesController, PlainController], setup: configureApp });

    const res = await request(app.getHttpServer()).get('/plain').expect(400);

    expect(res.body).toEqual({ by: 'global' });
    expect(trace).toEqual(['global']);
    await app.close();
  });
});
