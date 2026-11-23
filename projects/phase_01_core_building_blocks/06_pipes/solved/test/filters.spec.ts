import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { FiltersController } from '../src/filters/filters.controller.js';
import { createApp } from './helpers.js';

const V4 = '550e8400-e29b-41d4-a716-446655440000';
const V1 = '6ba7b810-9dad-11d1-80b4-00c04fd430c8';

describe('Task 2: ParseUUIDPipe, ParseEnumPipe, ParseBoolPipe, ParseDatePipe', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([FiltersController]));
  });

  afterEach(async () => {
    await app.close();
  });

  it('converts every value to its real type', async () => {
    const res = await request(app.getHttpServer())
      .get(`/filters/${V4}?color=red&archived=true&since=2020-01-02`)
      .expect(200);

    expect(res.body).toEqual({
      uuid: V4,
      color: 'red',
      archived: true,
      archivedType: 'boolean',
      since: '2020-01-02T00:00:00.000Z',
      sinceIsDate: true,
    });
  });

  it('archived defaults to false (a real boolean) and since stays missing', async () => {
    const res = await request(app.getHttpServer()).get(`/filters/${V4}?color=blue`).expect(200);

    expect(res.body).toMatchObject({ archived: false, archivedType: 'boolean', since: null, sinceIsDate: false });
  });

  it('accepts only a version 4 UUID', async () => {
    const res = await request(app.getHttpServer()).get(`/filters/${V1}?color=red`).expect(400);

    expect(res.body.message).toBe('Validation failed (uuid v 4 is expected)');
  });

  it('color must be one of the enum VALUES, and it is required', async () => {
    await request(app.getHttpServer()).get(`/filters/${V4}?color=green`).expect(400);
    await request(app.getHttpServer()).get(`/filters/${V4}?color=Red`).expect(400);
    await request(app.getHttpServer()).get(`/filters/${V4}`).expect(400);
  });

  it('archived must be the string true or false', async () => {
    await request(app.getHttpServer()).get(`/filters/${V4}?color=red&archived=maybe`).expect(400);
    await request(app.getHttpServer()).get(`/filters/${V4}?color=red&archived=1`).expect(400);
  });

  it('since must be a parsable date when it is given', async () => {
    const res = await request(app.getHttpServer()).get(`/filters/${V4}?color=red&since=garbage`).expect(400);

    expect(res.body.message).toBe('Validation failed (invalid date format)');
  });
});
