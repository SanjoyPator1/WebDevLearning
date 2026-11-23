import type { Request, Response } from 'express';
import request from 'supertest';
import { configureApp } from '../src/global/configure-app.js';
import { GlobalModule } from '../src/global/global.module.js';
import { tagResponse } from '../src/global/tag-response.js';
import { createApp } from './helpers.js';

describe('Task 1: functional middleware and app.use', () => {
  it('tagResponse sets the header and calls next() exactly once', () => {
    const res = { setHeader: vi.fn() } as unknown as Response;
    const next = vi.fn();

    tagResponse({} as Request, res, next);

    expect(res.setHeader).toHaveBeenCalledWith('x-tagged', 'yes');
    expect(next).toHaveBeenCalledTimes(1);
  });

  it('configureApp makes every response carry the header', async () => {
    const { app } = await createApp([GlobalModule], { setup: configureApp });

    const res = await request(app.getHttpServer()).get('/hello').expect(200);

    expect(res.text).toBe('hello');
    expect(res.headers['x-tagged']).toBe('yes');
    await app.close();
  });

  it('global middleware also runs for a path that no route handles (the 404)', async () => {
    const { app } = await createApp([GlobalModule], { setup: configureApp });

    const res = await request(app.getHttpServer()).get('/nothing-here').expect(404);

    expect(res.headers['x-tagged']).toBe('yes');
    await app.close();
  });

  it('guard: without configureApp nothing sets the header', async () => {
    const { app } = await createApp([GlobalModule]);

    const res = await request(app.getHttpServer()).get('/hello').expect(200);

    expect(res.headers['x-tagged']).toBeUndefined();
    await app.close();
  });
});
