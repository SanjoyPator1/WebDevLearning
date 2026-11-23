import { BadRequestException } from '@nestjs/common';
import request from 'supertest';
import { CustomController } from '../src/custom/custom.controller.js';
import { ParsePositiveIntPipe } from '../src/custom/parse-positive-int.pipe.js';
import { TrimPipe } from '../src/custom/trim.pipe.js';
import { createApp } from './helpers.js';

describe('Task 4a: a custom validating and transforming pipe', () => {
  it('transform() turns digits into a number', () => {
    const pipe = new ParsePositiveIntPipe();

    expect(pipe.transform('7', { type: 'query', data: 'limit' })).toBe(7);
    expect(pipe.transform('007', { type: 'query', data: 'limit' })).toBe(7);
    expect(pipe.transform(12, { type: 'query', data: 'limit' })).toBe(12);
  });

  it('transform() throws a BadRequestException built from the metadata', () => {
    const pipe = new ParsePositiveIntPipe();

    expect(() => pipe.transform('abc', { type: 'param', data: 'n' })).toThrow(BadRequestException);
    expect(() => pipe.transform('abc', { type: 'param', data: 'n' })).toThrow(
      'param "n" must be a positive integer',
    );
    expect(() => pipe.transform('0', { type: 'query', data: 'limit' })).toThrow(
      'query "limit" must be a positive integer',
    );
  });

  it('rejects zero, negatives, decimals and a missing value', () => {
    const pipe = new ParsePositiveIntPipe();
    const meta = { type: 'query', data: 'x' } as const;

    for (const bad of ['0', '-3', '5.5', 'abc', '', undefined, null, 0, -1, 2.5]) {
      expect(() => pipe.transform(bad, meta)).toThrow(BadRequestException);
    }
  });

  it('works on a route parameter over HTTP', async () => {
    const { app } = await createApp([CustomController]);

    const ok = await request(app.getHttpServer()).get('/custom/param/007').expect(200);
    expect(ok.body).toEqual({ n: 7, type: 'number' });

    const bad = await request(app.getHttpServer()).get('/custom/param/0').expect(400);
    expect(bad.body.message).toBe('param "n" must be a positive integer');
    await app.close();
  });

  it('the same pipe on a query value names the query in its message', async () => {
    const { app } = await createApp([CustomController]);

    await request(app.getHttpServer()).get('/custom/query?limit=5').expect(200, { limit: 5 });
    const bad = await request(app.getHttpServer()).get('/custom/query?limit=abc').expect(400);
    expect(bad.body.message).toBe('query "limit" must be a positive integer');
    await app.close();
  });
});

describe('Task 4b: a pure transformation pipe', () => {
  it('trims strings and leaves everything else alone', () => {
    const pipe = new TrimPipe();
    const meta = { type: 'body', data: 'name' } as const;
    const object = { a: 1 };

    expect(pipe.transform('  ada  ', meta)).toBe('ada');
    expect(pipe.transform(5, meta)).toBe(5);
    expect(pipe.transform(object, meta)).toBe(object);
    expect(pipe.transform(undefined, meta)).toBeUndefined();
  });

  it('works on a body property over HTTP and never rejects', async () => {
    const { app } = await createApp([CustomController]);

    await request(app.getHttpServer()).post('/custom/names').send({ name: '  ada ' }).expect(201, { name: 'ada' });
    await request(app.getHttpServer()).post('/custom/names').send({ name: 42 }).expect(201, { name: 42 });
    await app.close();
  });
});
