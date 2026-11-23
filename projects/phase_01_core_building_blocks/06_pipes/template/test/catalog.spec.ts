import request from 'supertest';
import { CatalogController } from '../src/catalog/catalog.controller.js';
import { CatalogService } from '../src/catalog/catalog.service.js';
import { createApp } from './helpers.js';

describe('Task 6: a pipe with an injected provider', () => {
  it('turns a known sku into the product name', async () => {
    const { app } = await createApp([CatalogController], { providers: [CatalogService] });

    const res = await request(app.getHttpServer()).get('/catalog/A1').expect(200);

    expect(res.body).toEqual({ product: 'Anvil' });
    await app.close();
  });

  it('rejects an unknown sku with a 400 that names it', async () => {
    const { app } = await createApp([CatalogController], { providers: [CatalogService] });

    const res = await request(app.getHttpServer()).get('/catalog/ZZ').expect(400);

    expect(res.body.message).toBe('unknown sku "ZZ"');
    await app.close();
  });

  it('uses the SAME CatalogService as the rest of the application', async () => {
    const { app } = await createApp([CatalogController], { providers: [CatalogService] });

    await request(app.getHttpServer()).get('/catalog/Z9').expect(400);
    app.get(CatalogService).add('Z9', 'Zinc');
    const res = await request(app.getHttpServer()).get('/catalog/Z9').expect(200);

    expect(res.body).toEqual({ product: 'Zinc' });
    await app.close();
  });
});
