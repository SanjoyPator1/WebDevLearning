import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { OrdersController } from '../src/domain/orders.controller.js';
import { OrdersService } from '../src/domain/orders.service.js';
import { createApp } from './helpers.js';

describe('Task 3: mapping domain errors to HTTP in one place', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [OrdersController], providers: [OrdersService] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('a successful order is untouched by the filter', async () => {
    await request(app.getHttpServer()).get('/orders/apple/3').expect(200, { sku: 'apple', quantity: 3 });
  });

  it('OutOfStockError is a 409', async () => {
    const res = await request(app.getHttpServer()).get('/orders/empty/1').expect(409);

    expect(res.body).toEqual({ code: 'OUT_OF_STOCK', message: 'empty is out of stock' });
  });

  it('InvalidQuantityError is a 422', async () => {
    const res = await request(app.getHttpServer()).get('/orders/apple/0').expect(422);

    expect(res.body).toEqual({ code: 'INVALID_QUANTITY', message: 'quantity 0 is not allowed' });
  });

  it('UnknownProductError is a 404', async () => {
    const res = await request(app.getHttpServer()).get('/orders/ghost/1').expect(404);

    expect(res.body).toEqual({ code: 'UNKNOWN_PRODUCT', message: 'no product ghost' });
  });

  it('any other DomainError is a 400', async () => {
    const res = await request(app.getHttpServer()).get('/orders/old/1').expect(400);

    expect(res.body).toEqual({ code: 'DISCONTINUED', message: 'old is discontinued' });
  });

  it('an error that is NOT a DomainError is left alone: a generic 500 that hides the message', async () => {
    const res = await request(app.getHttpServer()).get('/orders/boom/1').expect(500);

    expect(res.body).toEqual({ statusCode: 500, message: 'Internal server error' });
    expect(JSON.stringify(res.body)).not.toContain('database');
  });
});
