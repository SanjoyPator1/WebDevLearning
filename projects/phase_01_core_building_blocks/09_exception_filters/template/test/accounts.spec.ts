import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AccountsController } from '../src/accounts/accounts.controller.js';
import { createApp } from './helpers.js';

describe('Task 1: throwing the built-in exceptions', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [AccountsController] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('NotFoundException with a message', async () => {
    const res = await request(app.getHttpServer()).get('/accounts/missing').expect(404);

    expect(res.body).toEqual({ message: 'account 7 not found', error: 'Not Found', statusCode: 404 });
  });

  it('BadRequestException with a message and an errorCode', async () => {
    const res = await request(app.getHttpServer()).get('/accounts/weak-password').expect(400);

    expect(res.body).toEqual({
      message: 'password too short',
      error: 'Bad Request',
      statusCode: 400,
      errorCode: 'WEAK_PASSWORD',
    });
  });

  it('ConflictException with a message and an errorCode', async () => {
    const res = await request(app.getHttpServer()).get('/accounts/duplicate').expect(409);

    expect(res.body).toEqual({
      message: 'email already registered',
      error: 'Conflict',
      statusCode: 409,
      errorCode: 'DUPLICATE_EMAIL',
    });
  });

  it('an array as the message lists several problems at once', async () => {
    const res = await request(app.getHttpServer()).get('/accounts/fields').expect(400);

    expect(res.body).toEqual({
      message: ['name must not be empty', 'age must be positive'],
      error: 'Bad Request',
      statusCode: 400,
    });
  });

  it('the generic HttpException with an object sends that object as the whole body', async () => {
    const res = await request(app.getHttpServer()).get('/accounts/custom').expect(422);

    expect(res.body).toEqual({ code: 'E1', hint: 'try again' });
  });

  it('guard: an unexpected Error never leaks its message: the client gets a generic 500', async () => {
    const res = await request(app.getHttpServer()).get('/accounts/crash').expect(500);

    expect(res.body).toEqual({ statusCode: 500, message: 'Internal server error' });
    expect(JSON.stringify(res.body)).not.toContain('hunter2');
  });
});
