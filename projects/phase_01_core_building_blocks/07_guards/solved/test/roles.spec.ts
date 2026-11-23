import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { Roles } from '../src/roles/roles.decorator.js';
import { ReportsController } from '../src/roles/reports.controller.js';
import { createApp } from './helpers.js';

describe('Task 3a: a metadata decorator made with Reflector.createDecorator', () => {
  it('Roles carries a KEY, which is how a decorator made by Reflector.createDecorator is recognised', () => {
    expect(typeof (Roles as unknown as { KEY?: unknown }).KEY).toBe('string');
  });
});

describe('Task 3b: a role guard that reads the metadata', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [ReportsController] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('a route inherits the controller roles: a viewer and an admin may list', async () => {
    await request(app.getHttpServer()).get('/reports').set('x-role', 'viewer').expect(200, 'reports');
    await request(app.getHttpServer()).get('/reports').set('x-role', 'admin').expect(200, 'reports');
  });

  it('another role is denied with 403', async () => {
    const res = await request(app.getHttpServer()).get('/reports').set('x-role', 'stranger').expect(403);

    expect(res.body).toEqual({ message: 'Forbidden resource', error: 'Forbidden', statusCode: 403 });
  });

  it('no role header is denied too', async () => {
    await request(app.getHttpServer()).get('/reports').expect(403);
  });

  it('the method roles REPLACE the controller roles: a viewer may list but not delete', async () => {
    await request(app.getHttpServer()).delete('/reports/7').set('x-role', 'viewer').expect(403);
    await request(app.getHttpServer()).delete('/reports/7').set('x-role', 'admin').expect(200, 'deleted 7');
  });

  it('an EMPTY list on a method means no role is required, even though the controller has roles', async () => {
    await request(app.getHttpServer()).get('/reports/open').expect(200, 'open');
    await request(app.getHttpServer()).get('/reports/open').set('x-role', 'stranger').expect(200, 'open');
  });
});
