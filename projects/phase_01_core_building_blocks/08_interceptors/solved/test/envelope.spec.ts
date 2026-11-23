import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { NotesController } from '../src/envelope/notes.controller.js';
import { createApp } from './helpers.js';

describe('Task 1: mapping the response with an interceptor', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [NotesController] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('wraps an object in { data }', async () => {
    const res = await request(app.getHttpServer()).get('/notes/one').expect(200);

    expect(res.body).toEqual({ data: { id: 1, text: 'hello' } });
  });

  it('wraps an array and a string too', async () => {
    const list = await request(app.getHttpServer()).get('/notes/list').expect(200);
    const text = await request(app.getHttpServer()).get('/notes/text').expect(200);

    expect(list.body).toEqual({ data: [{ id: 1 }, { id: 2 }] });
    expect(text.body).toEqual({ data: 'plain' });
  });

  it('wraps the value an async handler resolves to', async () => {
    const res = await request(app.getHttpServer()).get('/notes/later').expect(200);

    expect(res.body).toEqual({ data: 7 });
  });

  it('a handler that returns nothing gives { data: null }, not an empty object', async () => {
    const res = await request(app.getHttpServer()).get('/notes/none').expect(200);

    expect(res.body).toEqual({ data: null });
  });

  it('errors are not wrapped: the handler keeps its own 400', async () => {
    const res = await request(app.getHttpServer()).get('/notes/bad').expect(400);

    expect(res.body).toEqual({ message: 'nope', error: 'Bad Request', statusCode: 400 });
  });
});
