import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ItemsService } from '../src/items/items.service.js';
import { StashController } from '../src/stash/stash.controller.js';
import { createApp } from './helpers.js';

describe('Task 4: StashController, @Res', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([StashController], { providers: [ItemsService] }));
  });

  afterEach(async () => {
    await app.close();
  });

  describe('passthrough: Nest still sends the response', () => {
    it('PUT /stash/:id answers 201 with a Location header when it creates the item', async () => {
      const res = await request(app.getHttpServer())
        .put('/stash/10')
        .send({ name: 'elderberry' })
        .expect(201);

      expect(res.headers['location']).toBe('/stash/10');
      expect(res.body).toEqual({ id: 10, name: 'elderberry' });
    });

    it('PUT /stash/:id answers 200 when the item already exists', async () => {
      const res = await request(app.getHttpServer())
        .put('/stash/1')
        .send({ name: 'avocado' })
        .expect(200);

      expect(res.headers['location']).toBe('/stash/1');
      expect(res.body).toEqual({ id: 1, name: 'avocado' });
    });
  });

  describe('no passthrough: the handler sends the response itself', () => {
    it('GET /stash/:id/text sends plain text', async () => {
      const res = await request(app.getHttpServer()).get('/stash/2/text').expect(200);

      expect(res.headers['content-type']).toMatch(/^text\/plain/);
      expect(res.text).toBe('2:banana');
    });

    it('GET /stash/:id/text answers 404 for an unknown id', async () => {
      const res = await request(app.getHttpServer()).get('/stash/99/text').expect(404);

      expect(res.headers['content-type']).toMatch(/^text\/plain/);
      expect(res.text).toBe('not found');
    });
  });
});
