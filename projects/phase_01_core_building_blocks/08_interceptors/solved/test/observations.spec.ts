import {
  BadRequestException,
  type CallHandler,
  type CanActivate,
  Catch,
  type ArgumentsHost,
  Controller,
  type ExceptionFilter,
  type ExecutionContext,
  Get,
  Injectable,
  type MiddlewareConsumer,
  Module,
  type NestInterceptor,
  type NestMiddleware,
  type NestModule,
  Param,
  type PipeTransform,
  UseFilters,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { type Observable, TimeoutError, catchError, concat, finalize, from, map, of, tap, timeout } from 'rxjs';
import request from 'supertest';
import { createApp } from './helpers.js';

// These tests need none of your code. They pass from the start and record how interceptors behave,
// measured on Nest 12.5.1 with Express 5. Read them, then change a line and watch one fail.

const log: string[] = [];
const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

function interceptor(impl: (next: CallHandler, context: ExecutionContext) => Observable<unknown>): new () => NestInterceptor {
  @Injectable()
  class X implements NestInterceptor {
    intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
      return impl(next, context);
    }
  }
  return X;
}

async function call(
  I: new () => NestInterceptor,
  handler: () => unknown,
): Promise<{ status: number; text: string; headers: Record<string, string> }> {
  @Controller('c')
  class C {
    @Get()
    @UseInterceptors(I)
    g(): unknown {
      return handler();
    }
  }
  const app = await createApp({ controllers: [C] });
  const res = await request(app.getHttpServer()).get('/c');
  await app.close();
  return { status: res.status, text: res.text, headers: res.headers as Record<string, string> };
}

describe('Observations: where interceptors sit', () => {
  beforeEach(() => {
    log.length = 0;
  });

  it('middleware, guard, interceptor (before), pipe, handler, interceptor (after)', async () => {
    @Injectable()
    class Mw implements NestMiddleware {
      use(req: unknown, res: unknown, next: () => void): void {
        log.push('middleware');
        next();
      }
    }
    class Allow implements CanActivate {
      canActivate(): boolean {
        log.push('guard');
        return true;
      }
    }
    class Pipe implements PipeTransform {
      transform(value: unknown): unknown {
        log.push('pipe');
        return value;
      }
    }
    const Spy = interceptor((next) => {
      log.push('interceptor:before');
      return next.handle().pipe(tap(() => log.push('interceptor:after')));
    });
    @Controller('o')
    class C {
      @Get(':v')
      @UseGuards(Allow)
      @UseInterceptors(Spy)
      go(@Param('v', Pipe) v: string): string {
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

    await request(app.getHttpServer()).get('/o/1').expect(200);

    expect(log).toEqual(['middleware', 'guard', 'interceptor:before', 'pipe', 'handler', 'interceptor:after']);
    await app.close();
  });

  it('an interceptor sees errors from pipes and the handler, but never a guard denial; filters come after', async () => {
    class Deny implements CanActivate {
      canActivate(): boolean {
        return false;
      }
    }
    class Reject implements PipeTransform {
      transform(): never {
        throw new BadRequestException('pipe');
      }
    }
    @Catch()
    class Filter implements ExceptionFilter {
      catch(error: unknown, host: ArgumentsHost): void {
        log.push('filter');
        host.switchToHttp().getResponse().status(400).json({ filtered: true });
      }
    }
    const Spy = interceptor((next) =>
      next.handle().pipe(
        tap({ error: (error) => log.push(`interceptor saw ${(error as Error).constructor.name}`) }),
      ),
    );
    @Controller('e')
    class C {
      @Get('guard')
      @UseGuards(Deny)
      @UseInterceptors(Spy)
      guard(): string {
        return 'x';
      }

      @Get('pipe/:v')
      @UseInterceptors(Spy)
      pipe(@Param('v', Reject) v: string): string {
        return v;
      }

      @Get('handler')
      @UseFilters(Filter)
      @UseInterceptors(Spy)
      handler(): never {
        throw new BadRequestException('handler');
      }
    }
    const app = await createApp({ controllers: [C] });

    await request(app.getHttpServer()).get('/e/guard').expect(403);
    expect(log).toEqual([]);

    await request(app.getHttpServer()).get('/e/pipe/1').expect(400);
    expect(log).toEqual(['interceptor saw BadRequestException']);

    log.length = 0;
    await request(app.getHttpServer()).get('/e/handler').expect(400);
    expect(log).toEqual(['interceptor saw BadRequestException', 'filter']);
    await app.close();
  });
});

describe('Observations: next.handle() is lazy', () => {
  beforeEach(() => {
    log.length = 0;
  });

  function run(I: new () => NestInterceptor): Promise<{ status: number; text: string }> {
    return call(I, () => {
      log.push('handler');
      return 'from handler';
    });
  }

  it('the handler runs only when the Observable from next.handle() is subscribed to', async () => {
    const answered = await run(interceptor(() => of('from interceptor')));
    expect(answered.text).toBe('from interceptor');
    expect(log).toEqual([]);

    const calledNotSubscribed = await run(interceptor((next) => { next.handle(); return of('x'); }));
    expect(calledNotSubscribed.text).toBe('x');
    expect(log).toEqual([]);
  });

  it('subscribing twice runs the handler twice', async () => {
    const res = await run(interceptor((next) => concat(next.handle(), next.handle())));

    expect(res.text).toBe('from handler');
    expect(log).toEqual(['handler', 'handler']);
  });
});

describe('Observations: what map, catchError, timeout and finalize do', () => {
  beforeEach(() => {
    log.length = 0;
  });

  it('map over undefined drops the property: { data: undefined } is sent as {}', async () => {
    const res = await call(interceptor((next) => next.handle().pipe(map((data) => ({ data })))), () => undefined);

    expect(res.text).toBe('{}');
  });

  it('map runs on every value a handler Observable emits, and Nest sends only the last one', async () => {
    const res = await call(interceptor((next) => next.handle().pipe(map((x) => (x as number) * 2))), () => from([1, 2, 3]));

    expect(res.text).toBe('6');
  });

  it('catchError that returns a value SWALLOWS the error, even a plain bug: the client gets a 200', async () => {
    const res = await call(
      interceptor((next) => next.handle().pipe(catchError(() => of({ fallback: true })))),
      () => {
        throw new Error('a real bug');
      },
    );

    expect(res.status).toBe(200);
    expect(res.text).toBe('{"fallback":true}');
  });

  it('timeout() alone is a 500, and the handler keeps running after the response', async () => {
    const res = await call(interceptor((next) => next.handle().pipe(timeout(30))), async () => {
      await sleep(80);
      log.push('slow handler finished');
      return 'late';
    });
    expect(res.status).toBe(500);
    expect(log).toEqual([]);

    await sleep(120);
    expect(log).toEqual(['slow handler finished']);
    expect(new TimeoutError().name).toBe('TimeoutError');
  });

  it('finalize runs after success and after an error, and BEFORE the response has been sent', async () => {
    const seen: boolean[] = [];
    const Spy = interceptor((next, context) => {
      const response = context.switchToHttp().getResponse();
      return next.handle().pipe(finalize(() => { log.push('finalize'); seen.push(response.headersSent); }));
    });

    await call(Spy, () => 'ok');
    await call(Spy, () => { throw new BadRequestException('x'); });
    await sleep(20);

    expect(log).toEqual(['finalize', 'finalize']);
    expect(seen).toEqual([false, false]);
  });
});

describe('Observations: state in an interceptor', () => {
  it('an interceptor is built once: a start time kept in a FIELD is overwritten by an overlapping request', async () => {
    @Injectable()
    class FieldTimer implements NestInterceptor {
      private start = 0;
      intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
        this.start = Date.now();
        return next.handle().pipe(map((value) => ({ value, ms: Date.now() - this.start })));
      }
    }
    @Controller('t')
    class C {
      @Get(':ms')
      @UseInterceptors(FieldTimer)
      async t(@Param('ms') ms: string): Promise<string> {
        await sleep(Number(ms));
        return ms;
      }
    }
    const app = await createApp({ controllers: [C] });

    const [slow] = await Promise.all([
      request(app.getHttpServer()).get('/t/200'),
      (async () => {
        await sleep(100);
        return request(app.getHttpServer()).get('/t/10');
      })(),
    ]);

    expect(slow.body.ms).toBeLessThan(150);
    await app.close();
  });
});
