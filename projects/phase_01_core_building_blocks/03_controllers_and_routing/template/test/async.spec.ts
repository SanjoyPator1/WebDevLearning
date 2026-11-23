import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AsyncController } from '../src/async/async.controller.js';
import { createApp } from './helpers.js';

describe('Task 5: AsyncController, promises and Observables', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([AsyncController]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('GET /async/later waits for the promise and answers its value', async () => {
    const res = await request(app.getHttpServer()).get('/async/later').expect(200);

    expect(res.body).toEqual({ waited: 20 });
  });

  it('GET /async/steps answers every value the Observable emits, as an array', async () => {
    const res = await request(app.getHttpServer()).get('/async/steps').expect(200);

    expect(res.body).toEqual([{ step: 1 }, { step: 2 }, { step: 3 }]);
  });

  it('GET /async/nothing answers 200 with an empty body, although the Observable emits nothing', async () => {
    const res = await request(app.getHttpServer()).get('/async/nothing').expect(200);

    expect(res.text).toBe('');
  });
});
