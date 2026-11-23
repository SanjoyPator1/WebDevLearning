import request from 'supertest';
import { OrderLog } from '../src/order/order-log.js';
import { OrderModule } from '../src/order/order.module.js';
import { createApp } from './helpers.js';

describe('Task 5: the order middleware runs in', () => {
  it('global, then First, Second, Third in that order, then the handler', async () => {
    const { app } = await createApp([OrderModule], {
      setup: (nest) => {
        const log = nest.get(OrderLog);
        nest.use((req: unknown, res: unknown, next: () => void) => {
          log.add('global');
          next();
        });
      },
    });

    await request(app.getHttpServer()).get('/order').expect(200);

    expect(app.get(OrderLog).entries).toEqual(['global', 'first', 'second', 'third', 'handler']);
    await app.close();
  });

  it('every request writes the whole sequence again: nothing is skipped or doubled', async () => {
    const { app } = await createApp([OrderModule]);

    await request(app.getHttpServer()).get('/order').expect(200);
    await request(app.getHttpServer()).get('/order').expect(200);

    expect(app.get(OrderLog).entries).toEqual([
      'first', 'second', 'third', 'handler',
      'first', 'second', 'third', 'handler',
    ]);
    await app.close();
  });
});
