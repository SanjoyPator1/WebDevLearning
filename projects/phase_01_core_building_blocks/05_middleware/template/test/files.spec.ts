import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { FilesModule } from '../src/files/files.module.js';
import { createApp } from './helpers.js';

describe('Task 4: Express 5 paths in forRoutes', () => {
  let app: INestApplication;
  let warnings: string[];

  beforeEach(async () => {
    ({ app, warnings } = await createApp([FilesModule]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('the path is written in the Express 5 syntax, so Nest has nothing to auto-convert', () => {
    expect(warnings.filter((message) => message.startsWith('Unsupported route path'))).toEqual([]);
  });

  it('runs for a path below /files', async () => {
    const res = await request(app.getHttpServer()).get('/files/a/b').expect(200);

    expect(res.text).toBe('a/b');
    expect(res.headers['x-mark']).toBe('yes');
  });

  it('does not run for /files itself', async () => {
    const res = await request(app.getHttpServer()).get('/files').expect(200);

    expect(res.text).toBe('index');
    expect(res.headers['x-mark']).toBeUndefined();
  });
});
