import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ProfileController } from '../src/user/profile.controller.js';
import { createApp } from './helpers.js';

describe('Tasks 1 and 2: custom parameter decorators', () => {
  let app: INestApplication;

  beforeEach(async () => {
    app = await createApp({ controllers: [ProfileController] });
  });

  afterEach(async () => {
    await app.close();
  });

  it('@CurrentUser() gives the whole user the guard attached', async () => {
    const res = await request(app.getHttpServer()).get('/profile').set('x-user', 'ada').expect(200);

    expect(res.body).toEqual({ user: { name: 'ada', roles: ['admin'] } });
  });

  it('@CurrentUser() is undefined when no user was attached', async () => {
    const res = await request(app.getHttpServer()).get('/profile').expect(200);

    expect(res.body).toEqual({ user: null });
  });

  it("@CurrentUser('name') gives one property", async () => {
    const res = await request(app.getHttpServer()).get('/profile/name').set('x-user', 'eve').expect(200);

    expect(res.body).toEqual({ name: 'eve' });
  });

  it("@CurrentUser('name') is undefined, not a crash, when there is no user", async () => {
    const res = await request(app.getHttpServer()).get('/profile/name').expect(200);

    expect(res.body).toEqual({ name: null });
  });

  it("a pipe after the data runs on the decorator's value: @CurrentUser('name', UpperPipe)", async () => {
    const res = await request(app.getHttpServer()).get('/profile/shout').set('x-user', 'ada').expect(200);

    expect(res.body).toEqual({ name: 'ADA' });
  });

  it('@Locale() takes the language of the first tag, lower-cased', async () => {
    const french = await request(app.getHttpServer())
      .get('/profile/locale')
      .set('accept-language', 'fr-CH,fr;q=0.9,en;q=0.8')
      .expect(200);
    const shouting = await request(app.getHttpServer()).get('/profile/locale').set('accept-language', 'EN-us').expect(200);

    expect(french.body).toEqual({ locale: 'fr' });
    expect(shouting.body).toEqual({ locale: 'en' });
  });

  it('@Locale() defaults to en when the header is missing or empty', async () => {
    const missing = await request(app.getHttpServer()).get('/profile/locale').expect(200);
    const empty = await request(app.getHttpServer()).get('/profile/locale').set('accept-language', '').expect(200);

    expect(missing.body).toEqual({ locale: 'en' });
    expect(empty.body).toEqual({ locale: 'en' });
  });

  it('two different decorators work side by side in one handler', async () => {
    const res = await request(app.getHttpServer())
      .get('/profile/both')
      .set('x-user', 'bob')
      .set('accept-language', 'de')
      .expect(200);

    expect(res.body).toEqual({ name: 'bob', locale: 'de' });
  });
});
