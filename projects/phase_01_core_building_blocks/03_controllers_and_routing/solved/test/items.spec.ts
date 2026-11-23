import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ItemsController } from '../src/items/items.controller.js';
import { ItemsService } from '../src/items/items.service.js';
import { createApp } from './helpers.js';

describe('Task 1: ItemsController, routes and request data', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([ItemsController], { providers: [ItemsService] }));
  });

  afterEach(async () => {
    await app.close();
  });

  it('GET /items lists every item', async () => {
    const res = await request(app.getHttpServer()).get('/items').expect(200);

    expect(res.body).toEqual([
      { id: 1, name: 'apple' },
      { id: 2, name: 'banana' },
      { id: 3, name: 'cherry' },
    ]);
  });

  it('GET /items?search= filters by name', async () => {
    const res = await request(app.getHttpServer()).get('/items?search=an').expect(200);

    expect(res.body).toEqual([{ id: 2, name: 'banana' }]);
  });

  it('GET /items?limit= keeps only the first items (the query value is a string)', async () => {
    const res = await request(app.getHttpServer()).get('/items?limit=2').expect(200);

    expect(res.body).toEqual([
      { id: 1, name: 'apple' },
      { id: 2, name: 'banana' },
    ]);
  });

  it('GET /items/:id returns one item', async () => {
    const res = await request(app.getHttpServer()).get('/items/2').expect(200);

    expect(res.body).toEqual({ id: 2, name: 'banana' });
  });

  it('POST /items creates an item from the JSON body and answers 201', async () => {
    const created = await request(app.getHttpServer())
      .post('/items')
      .send({ name: 'durian' })
      .expect(201);
    expect(created.body).toEqual({ id: 4, name: 'durian' });

    const all = await request(app.getHttpServer()).get('/items').expect(200);
    expect(all.body).toHaveLength(4);
  });
});
