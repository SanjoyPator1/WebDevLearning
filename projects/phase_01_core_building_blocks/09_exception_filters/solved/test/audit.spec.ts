import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AuditModule } from '../src/audit/audit.module.js';
import { ErrorLog } from '../src/audit/error-log.js';
import { ThingsModule } from '../src/audit/things.module.js';
import { createApp } from './helpers.js';

describe('Tasks 4a and 4b: a catch-all filter that extends BaseExceptionFilter, registered with APP_FILTER', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ imports: [AuditModule, ThingsModule] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('records an unexpected error and the client still gets the default generic 500', async () => {
    const res = await request(app.getHttpServer()).get('/things/crash').expect(500);

    expect(res.body).toEqual({ statusCode: 500, message: 'Internal server error' });
    expect(app.get(ErrorLog).entries).toEqual(['Error: db down']);
  });

  it('records an HttpException and the client still gets its normal 400 body', async () => {
    const res = await request(app.getHttpServer()).get('/things/bad').expect(400);

    expect(res.body).toEqual({ message: 'bad', error: 'Bad Request', statusCode: 400 });
    expect(app.get(ErrorLog).entries).toEqual(['BadRequestException: bad']);
  });

  it('it is global: it also sees the 404 of a path that matches no route', async () => {
    const res = await request(app.getHttpServer()).get('/nothing-here').expect(404);

    expect(res.body.statusCode).toBe(404);
    expect(app.get(ErrorLog).entries).toEqual(['NotFoundException: Cannot GET /nothing-here']);
  });

  it('it applies to a controller of a module that never imports AuditModule, and ignores a success', async () => {
    await request(app.getHttpServer()).get('/things/fine').expect(200, 'fine');
    await request(app.getHttpServer()).get('/things/bad').expect(400);

    expect(app.get(ErrorLog).entries).toHaveLength(1);
  });
});
