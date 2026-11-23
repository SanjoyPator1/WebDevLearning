import {
  Body,
  Controller,
  Get,
  Injectable,
  type MiddlewareConsumer,
  Module,
  type NestMiddleware,
  type NestModule,
  Post,
  Req,
  RequestMethod,
} from '@nestjs/common';
import type { NextFunction, Request, Response } from 'express';
import request from 'supertest';
import { createApp } from './helpers.js';

// These tests need none of your code. They pass from the start and record how middleware
// behaves, measured on Nest 12.5.1 with Express 5. Read them, then change a line and watch
// one fail: that is the quickest way to learn what each one says.

interface Seen {
  route?: unknown;
  body?: unknown;
  url?: string;
  originalUrl?: string;
  params?: Record<string, string>;
}

let seen: Seen;
let handlerRoute: { path: string } | undefined;

@Injectable()
class Probe implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    seen = { route: req.route, body: req.body, url: req.url, originalUrl: req.originalUrl, params: req.params as Record<string, string> };
    next();
  }
}

@Controller('obs')
class ObsController {
  @Get('x/:id')
  read(@Req() req: Request): string {
    handlerRoute = req.route as { path: string };
    return 'ok';
  }

  @Post('x/:id')
  write(@Body() body: unknown): unknown {
    return body;
  }
}

function moduleWith(...routes: Parameters<ReturnType<MiddlewareConsumer['apply']>['forRoutes']>) {
  @Module({ controllers: [ObsController] })
  class ObsModule implements NestModule {
    configure(consumer: MiddlewareConsumer): void {
      consumer.apply(Probe).forRoutes(...routes);
    }
  }
  return ObsModule;
}

describe('Observations: what middleware can and cannot see', () => {
  beforeEach(() => {
    seen = {};
    handlerRoute = undefined;
  });

  it('middleware does not know which handler will run: no req.route for a string path, and only its own mount point otherwise', async () => {
    const { app: byString } = await createApp([moduleWith('obs')]);
    await request(byString.getHttpServer()).get('/obs/x/7').expect(200);
    expect(seen.route).toBeUndefined();
    expect(handlerRoute?.path).toBe('/obs/x/:id');
    await byString.close();

    // Mounted on the route pattern (controller class), Express does set req.route, but it is the
    // route of the MIDDLEWARE's own mount: it carries no controller class and no method name.
    seen = {};
    const { app: byController } = await createApp([moduleWith(ObsController)]);
    await request(byController.getHttpServer()).get('/obs/x/7').expect(200);
    expect((seen.route as { path: string }).path).toBe('/obs/x/:id');
    expect(JSON.stringify(seen.route)).not.toContain('ObsController');
    await byController.close();
  });

  it('module middleware sees the parsed body, global app.use middleware does not', async () => {
    const { app: moduleApp } = await createApp([moduleWith(ObsController)]);
    await request(moduleApp.getHttpServer()).post('/obs/x/7').send({ a: 1 }).expect(201);
    expect(seen.body).toEqual({ a: 1 });
    await moduleApp.close();

    seen = {};
    const { app: globalApp } = await createApp([moduleWith('nothing-matches-this')], {
      setup: (nest) => {
        nest.use((req: Request, res: Response, next: NextFunction) => {
          seen = { body: req.body, url: req.url };
          next();
        });
      },
    });
    await request(globalApp.getHttpServer()).post('/obs/x/7').send({ a: 1 }).expect(201);
    expect(seen.body).toBeUndefined();
    await globalApp.close();
  });

  it('a string path is mounted like app.use(path): req.url loses the prefix, req.params is empty', async () => {
    const { app } = await createApp([moduleWith('obs')]);

    await request(app.getHttpServer()).get('/obs/x/7?q=1').expect(200);

    expect(seen.url).toBe('/x/7?q=1');
    expect(seen.originalUrl).toBe('/obs/x/7?q=1');
    expect(seen.params).toEqual({});
    await app.close();
  });

  it('a controller class (or a path with a method) keeps req.url and fills req.params', async () => {
    const { app: byController } = await createApp([moduleWith(ObsController)]);
    await request(byController.getHttpServer()).get('/obs/x/7?q=1').expect(200);
    expect(seen.url).toBe('/obs/x/7?q=1');
    expect(seen.params).toEqual({ id: '7' });
    await byController.close();

    seen = {};
    const { app: byRouteInfo } = await createApp([moduleWith({ path: 'obs/x/:id', method: RequestMethod.GET })]);
    await request(byRouteInfo.getHttpServer()).get('/obs/x/7?q=1').expect(200);
    expect(seen.url).toBe('/obs/x/7?q=1');
    expect(seen.params).toEqual({ id: '7' });
    await byRouteInfo.close();
  });

  it('a string path is a PREFIX match: it also runs where no route exists. A controller class does not', async () => {
    const { app: byString } = await createApp([moduleWith('obs')]);
    await request(byString.getHttpServer()).get('/obs/no/such/route').expect(404);
    expect(seen.originalUrl).toBe('/obs/no/such/route');
    await byString.close();

    seen = {};
    const { app: byController } = await createApp([moduleWith(ObsController)]);
    await request(byController.getHttpServer()).get('/obs/no/such/route').expect(404);
    expect(seen.originalUrl).toBeUndefined();
    await byController.close();
  });
});
