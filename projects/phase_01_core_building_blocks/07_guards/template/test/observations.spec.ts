import {
  type CanActivate,
  Controller,
  type ExecutionContext,
  ForbiddenException,
  Get,
  Injectable,
  type MiddlewareConsumer,
  Module,
  type NestMiddleware,
  type NestModule,
  Param,
  type PipeTransform,
  UnauthorizedException,
  UseGuards,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { EMPTY, from, of } from 'rxjs';
import request from 'supertest';
import { createApp } from './helpers.js';

// These tests need none of your code. They pass from the start and record how guards behave,
// measured on Nest 12.5.1 with Express 5. Read them, then change a line and watch one fail.

const ran: string[] = [];

function guardReturning(result: () => unknown): new () => CanActivate {
  @Injectable()
  class G implements CanActivate {
    canActivate(): never {
      return result() as never;
    }
  }
  return G;
}

async function call(guard: new () => CanActivate): Promise<{ status: number; body: Record<string, unknown> }> {
  @Controller('g')
  class C {
    @Get()
    @UseGuards(guard)
    g(): string {
      ran.push('handler');
      return 'ok';
    }
  }
  const app = await createApp({ controllers: [C] });
  const res = await request(app.getHttpServer()).get('/g');
  await app.close();
  return { status: res.status, body: res.body };
}

describe('Observations: how Nest reads a guard', () => {
  beforeEach(() => {
    ran.length = 0;
  });

  it('false is a 403 "Forbidden resource"; throwing picks the status yourself; a plain Error is a 500', async () => {
    const denied = await call(guardReturning(() => false));
    expect(denied).toEqual({ status: 403, body: { message: 'Forbidden resource', error: 'Forbidden', statusCode: 403 } });

    const unauthorized = await call(guardReturning(() => { throw new UnauthorizedException('who are you'); }));
    expect(unauthorized.status).toBe(401);
    expect(unauthorized.body.message).toBe('who are you');

    const forbidden = await call(guardReturning(() => { throw new ForbiddenException('custom'); }));
    expect(forbidden.body).toEqual({ message: 'custom', error: 'Forbidden', statusCode: 403 });

    const crashed = await call(guardReturning(() => { throw new Error('bug'); }));
    expect(crashed).toEqual({ status: 500, body: { statusCode: 500, message: 'Internal server error' } });
    expect(ran).toEqual([]);
  });

  it('a Promise is awaited, and an Observable decides by its LAST value; an empty one is a 500', async () => {
    expect((await call(guardReturning(async () => true))).status).toBe(200);
    expect((await call(guardReturning(async () => false))).status).toBe(403);
    expect((await call(guardReturning(() => of(true)))).status).toBe(200);
    expect((await call(guardReturning(() => from([true, false])))).status).toBe(403);
    expect((await call(guardReturning(() => from([false, true])))).status).toBe(200);
    expect((await call(guardReturning(() => EMPTY))).status).toBe(500);
  });

  it('a non-boolean result is judged by truthiness: "yes" passes, undefined, 0 and null deny', async () => {
    expect((await call(guardReturning(() => 'yes'))).status).toBe(200);
    expect((await call(guardReturning(() => undefined))).status).toBe(403);
    expect((await call(guardReturning(() => 0))).status).toBe(403);
    expect((await call(guardReturning(() => null))).status).toBe(403);
  });

  it('order: middleware, then guard, then pipe, then handler. A denial stops before the pipe, and an unknown path never reaches a guard', async () => {
    const log: string[] = [];
    @Injectable()
    class Mw implements NestMiddleware {
      use(req: unknown, res: unknown, next: () => void): void {
        log.push('middleware');
        next();
      }
    }
    class Pipe implements PipeTransform {
      transform(value: unknown): unknown {
        log.push('pipe');
        return value;
      }
    }
    const Allow = guardReturning(() => { log.push('guard'); return true; });
    const Deny = guardReturning(() => { log.push('guard (deny)'); return false; });

    @Controller('o')
    class C {
      @Get('ok/:v')
      @UseGuards(Allow)
      ok(@Param('v', Pipe) v: string): string {
        log.push('handler');
        return v;
      }

      @Get('no/:v')
      @UseGuards(Deny)
      no(@Param('v', Pipe) v: string): string {
        log.push('handler');
        return v;
      }
    }
    @Module({ controllers: [C] })
    class M implements NestModule {
      configure(consumer: MiddlewareConsumer): void {
        consumer.apply(Mw).forRoutes('{*splat}');
      }
    }
    const app = await createApp({ imports: [M] });

    await request(app.getHttpServer()).get('/o/ok/1').expect(200);
    expect(log).toEqual(['middleware', 'guard', 'pipe', 'handler']);

    log.length = 0;
    await request(app.getHttpServer()).get('/o/no/1').expect(403);
    expect(log).toEqual(['middleware', 'guard (deny)']);

    log.length = 0;
    await request(app.getHttpServer()).get('/o/nothing').expect(404);
    expect(log).toEqual(['middleware']);
    await app.close();
  });

  it('the ExecutionContext: type, controller class, handler and the raw arguments. The matched route is known here', async () => {
    const seen: Record<string, unknown> = {};
    const Spy = guardReturning(() => true);
    Spy.prototype.canActivate = function (context: ExecutionContext) {
      const http = context.switchToHttp();
      Object.assign(seen, {
        type: context.getType(),
        controller: context.getClass().name,
        handler: context.getHandler().name,
        argCount: context.getArgs().length,
        routePath: http.getRequest().route?.path,
      });
      return true;
    };

    @Controller('x')
    class XController {
      @Get(':id')
      @UseGuards(Spy)
      read(): string {
        return 'ok';
      }
    }
    const app = await createApp({ controllers: [XController] });

    await request(app.getHttpServer()).get('/x/7').expect(200);

    expect(seen).toEqual({ type: 'http', controller: 'XController', handler: 'read', argCount: 3, routePath: '/x/:id' });
    await app.close();
  });

  it('a guard built by hand for app.useGlobalGuards() gets no injection', async () => {
    @Injectable()
    class Dep {}
    @Injectable()
    class NeedsDep implements CanActivate {
      constructor(private readonly dep: Dep) {}
      canActivate(): boolean {
        return this.dep.constructor === Dep;
      }
    }
    @Controller('h')
    class C {
      @Get()
      h(): string {
        return 'ok';
      }
    }
    const app = await createApp({
      controllers: [C],
      providers: [Dep],
      setup: (nest) => nest.useGlobalGuards(new (NeedsDep as unknown as new () => CanActivate)()),
    });

    await request(app.getHttpServer()).get('/h').expect(500);
    await app.close();
  });
});

describe('Observations: Reflector', () => {
  const Roles = Reflector.createDecorator<string[]>();

  @Controller('r')
  @Roles(['user', 'admin'])
  class C {
    @Get('a')
    a(): void {}

    @Get('b')
    @Roles(['admin'])
    b(): void {}

    @Get('c')
    @Roles([])
    c(): void {}
  }
  const reflector = new Reflector();
  const handler = (name: 'a' | 'b' | 'c'): Function => C.prototype[name];

  it('getAllAndOverride: the first target that has a value wins, and an empty array IS a value', () => {
    expect(reflector.getAllAndOverride(Roles, [handler('a'), C])).toEqual(['user', 'admin']);
    expect(reflector.getAllAndOverride(Roles, [handler('b'), C])).toEqual(['admin']);
    expect(reflector.getAllAndOverride(Roles, [handler('c'), C])).toEqual([]);
  });

  it('getAllAndMerge concatenates the values of every target, duplicates included', () => {
    expect(reflector.getAllAndMerge(Roles, [handler('b'), C])).toEqual(['admin', 'user', 'admin']);
    expect(reflector.getAllAndMerge(Roles, [handler('c'), C])).toEqual(['user', 'admin']);
  });

  it('get() reads one target only, and an unset key is undefined', () => {
    expect(reflector.get(Roles, handler('a'))).toBeUndefined();
    expect(reflector.get(Roles, C)).toEqual(['user', 'admin']);
    expect(typeof Roles.KEY).toBe('string');
  });
});
