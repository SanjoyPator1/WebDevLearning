import 'reflect-metadata';
import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { ItemsController } from '../src/items/items.controller.js';
import { ItemsService } from '../src/items/items.service.js';
import { UpdateItemDto } from '../src/items/update-item.dto.js';
import { createApp } from './helpers.js';

describe('Task 8: UpdateItemDto, a DTO is a class', () => {
  let app: INestApplication;

  beforeEach(async () => {
    ({ app } = await createApp([ItemsController], { providers: [ItemsService] }));
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await app.close();
  });

  it('PATCH /items/:id renames the item', async () => {
    const res = await request(app.getHttpServer())
      .patch('/items/2')
      .send({ name: 'blueberry' })
      .expect(200);

    expect(res.body).toEqual({ id: 2, name: 'blueberry' });
  });

  it('PATCH /items/:id with an empty body leaves the item unchanged', async () => {
    const res = await request(app.getHttpServer()).patch('/items/2').send({}).expect(200);

    expect(res.body).toEqual({ id: 2, name: 'banana' });
  });

  it('UpdateItemDto is a class, so it exists at runtime', () => {
    expect(typeof UpdateItemDto).toBe('function');
  });

  it('the handler parameter is typed with the class, so TypeScript emits it as design:paramtypes', () => {
    const paramTypes: unknown[] = Reflect.getMetadata('design:paramtypes', ItemsController.prototype, 'update');

    expect(paramTypes?.[1]).toBe(UpdateItemDto);
  });

  it('guard: without a pipe, the body arrives as a plain object and not as an UpdateItemDto', async () => {
    // Nest binds the handler when the application initialises, so the spy goes in first and
    // gets its own application.
    const original = ItemsController.prototype.update;
    const spy = vi.spyOn(ItemsController.prototype, 'update');
    // The spy is a new function. The route decorators stored the path and method on the
    // original one, so copy them over or Nest no longer sees a route.
    for (const key of Reflect.getMetadataKeys(original)) {
      Reflect.defineMetadata(key, Reflect.getMetadata(key, original), spy);
    }
    const spied = await createApp([ItemsController], { providers: [ItemsService] });

    await request(spied.app.getHttpServer()).patch('/items/2').send({ name: 'blueberry' }).expect(200);
    await spied.app.close();

    const received = spy.mock.calls[0]?.[1];
    expect(received).toEqual({ name: 'blueberry' });
    expect(received).not.toBeInstanceOf(UpdateItemDto);
  });
});
