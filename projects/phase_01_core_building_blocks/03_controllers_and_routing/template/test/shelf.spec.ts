import { Controller, Get, Param } from '@nestjs/common';
import request from 'supertest';
import { ShelfController } from '../src/shelf/shelf.controller.js';
import { specificityRoutes, strictRoutes } from '../src/shelf/shelf-options.js';
import { createApp } from './helpers.js';

// Controllers written only for these tests, so each one can be broken on purpose.
@Controller('shelf')
class WrongOrder {
  @Get(':id')
  one(@Param('id') id: string): string {
    return `one:${id}`;
  }

  @Get('latest')
  latest(): string {
    return 'latest';
  }
}

@Controller('dup')
class DuplicateA {
  @Get('x')
  a(): string {
    return 'a';
  }
}

@Controller('dup')
class DuplicateB {
  @Get('x')
  b(): string {
    return 'b';
  }
}

describe('Task 7: ShelfController, route order and route conflicts', () => {
  describe('7a: declaration order decides', () => {
    it('ShelfController answers the literal route /shelf/latest', async () => {
      const { app } = await createApp([ShelfController]);

      const res = await request(app.getHttpServer()).get('/shelf/latest').expect(200);
      expect(res.text).toBe('latest shelf');

      await app.close();
    });

    it('ShelfController still answers other ids with the parameter route', async () => {
      const { app } = await createApp([ShelfController]);

      const res = await request(app.getHttpServer()).get('/shelf/42').expect(200);
      expect(res.text).toBe('shelf 42');

      await app.close();
    });

    it('control: the same two routes in the wrong order, with default options, swallow /shelf/latest', async () => {
      const { app } = await createApp([WrongOrder]);

      const res = await request(app.getHttpServer()).get('/shelf/latest').expect(200);
      expect(res.text).toBe('one:latest');

      await app.close();
    });
  });

  describe('7b: strictRoutes', () => {
    it('refuses to start when two controllers register the same method and path', async () => {
      await expect(
        createApp([DuplicateA, DuplicateB], { app: strictRoutes }),
      ).rejects.toThrow(/Duplicate route: GET \/dup\/x/);
    });

    it('only warns about shadowed routes: the application still starts', async () => {
      const { app, warnings } = await createApp([WrongOrder], { app: strictRoutes });

      expect(warnings.some((message) => message.includes('is shadowed by'))).toBe(true);

      await app.close();
    });
  });

  describe('7c: specificityRoutes', () => {
    it('registers literal routes before parameter routes, whatever the declaration order', async () => {
      const { app } = await createApp([WrongOrder], { app: specificityRoutes });

      const latest = await request(app.getHttpServer()).get('/shelf/latest').expect(200);
      expect(latest.text).toBe('latest');
      const other = await request(app.getHttpServer()).get('/shelf/7').expect(200);
      expect(other.text).toBe('one:7');

      await app.close();
    });
  });
});
