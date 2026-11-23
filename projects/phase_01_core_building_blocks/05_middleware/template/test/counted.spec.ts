import request from 'supertest';
import { CountedModule } from '../src/counted/counted.module.js';
import { createApp } from './helpers.js';

describe('Task 2: class middleware with an injected provider', () => {
  it('the header counts requests: the middleware really got HitCounterService', async () => {
    const { app } = await createApp([CountedModule]);

    const first = await request(app.getHttpServer()).get('/counted').expect(200);
    const second = await request(app.getHttpServer()).get('/counted').expect(200);

    expect(first.headers['x-hits']).toBe('1');
    expect(second.headers['x-hits']).toBe('2');
    await app.close();
  });

  it('it runs for every route of CountedController, and the counter is shared', async () => {
    const { app } = await createApp([CountedModule]);

    await request(app.getHttpServer()).get('/counted').expect(200);
    const res = await request(app.getHttpServer()).get('/counted/7').expect(200);

    expect(res.text).toBe('counted 7');
    expect(res.headers['x-hits']).toBe('2');
    await app.close();
  });

  it('it does not run for OtherController, which lives in the same module', async () => {
    const { app } = await createApp([CountedModule]);

    const res = await request(app.getHttpServer()).get('/other').expect(200);

    expect(res.text).toBe('other');
    expect(res.headers['x-hits']).toBeUndefined();
    await app.close();
  });
});
