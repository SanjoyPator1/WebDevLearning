import {
  type ArgumentsHost,
  BadRequestException,
  type CallHandler,
  type CanActivate,
  Catch,
  Controller,
  type ExceptionFilter,
  type ExecutionContext,
  Get,
  HttpException,
  Injectable,
  IntrinsicException,
  type MiddlewareConsumer,
  Module,
  type NestInterceptor,
  type NestMiddleware,
  type NestModule,
  NotFoundException,
  Param,
  type PipeTransform,
  UseFilters,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { BaseExceptionFilter } from '@nestjs/core';
import { catchError, throwError } from 'rxjs';
import request from 'supertest';
import { createApp } from './helpers.js';

// These tests need none of your code. They pass from the start and record how exceptions and filters
// behave, measured on Nest 12.5.1 with Express 5. Read them, then change a line and watch one fail.

const logged: string[] = [];
const capture = {
  log() {},
  warn() {},
  error(message: unknown) {
    logged.push(String((message as Error)?.message ?? message));
  },
};

function named(name: string, types: Array<new (...args: never[]) => unknown> = []): new () => ExceptionFilter {
  @Catch(...types)
  class F implements ExceptionFilter {
    catch(exception: unknown, host: ArgumentsHost): void {
      const status = exception instanceof HttpException ? exception.getStatus() : 500;
      host.switchToHttp().getResponse().status(status).json({ by: name });
    }
  }
  return F;
}

describe('Observations: the default response and what gets logged', () => {
  beforeEach(() => {
    logged.length = 0;
  });

  class MyIntrinsic extends IntrinsicException {}

  @Controller('d')
  class D {
    @Get('bare') bare(): never { throw new BadRequestException(); }
    @Get('string') string(): never { throw new BadRequestException('too short'); }
    @Get('object') object(): never { throw new BadRequestException({ code: 'X' }); }
    @Get('code-string') codeString(): never { throw new BadRequestException('too short', { errorCode: 'WEAK' }); }
    @Get('code-object') codeObject(): never { throw new BadRequestException({ code: 'X' }, { errorCode: 'WEAK' }); }
    @Get('cause') cause(): never { throw new BadRequestException('wrapped', { cause: new Error('root cause') }); }
    @Get('plain') plain(): never { throw new Error('secret internals'); }
    @Get('thrown-string') thrownString(): never { throw 'just a string'; }
    @Get('intrinsic') intrinsic(): never { throw new MyIntrinsic('mine'); }
  }

  it('the default body: message, error and statusCode, or exactly the object you gave', async () => {
    const app = await createApp({ controllers: [D], app: { logger: capture } });

    expect((await request(app.getHttpServer()).get('/d/bare')).body).toEqual({ message: 'Bad Request', statusCode: 400 });
    expect((await request(app.getHttpServer()).get('/d/string')).body).toEqual({ message: 'too short', error: 'Bad Request', statusCode: 400 });
    expect((await request(app.getHttpServer()).get('/d/object')).body).toEqual({ code: 'X' });
    await app.close();
  });

  it('errorCode (new in v12) is added to the body for a string, array or empty message, but NOT when the body is an object', async () => {
    const app = await createApp({ controllers: [D], app: { logger: capture } });

    expect((await request(app.getHttpServer()).get('/d/code-string')).body).toEqual({
      message: 'too short', error: 'Bad Request', statusCode: 400, errorCode: 'WEAK',
    });
    expect((await request(app.getHttpServer()).get('/d/code-object')).body).toEqual({ code: 'X' });
    await app.close();
  });

  it('the cause is for your logs: it never reaches the client', async () => {
    const app = await createApp({ controllers: [D], app: { logger: capture } });

    const res = await request(app.getHttpServer()).get('/d/cause').expect(400);

    expect(JSON.stringify(res.body)).not.toContain('root cause');
    await app.close();
  });

  it('anything that is not an HttpException is a generic 500, and is logged; an HttpException is not logged', async () => {
    const app = await createApp({ controllers: [D], app: { logger: capture } });

    await request(app.getHttpServer()).get('/d/bare').expect(400);
    expect(logged).toEqual([]);

    const plain = await request(app.getHttpServer()).get('/d/plain').expect(500);
    expect(plain.body).toEqual({ statusCode: 500, message: 'Internal server error' });
    await request(app.getHttpServer()).get('/d/thrown-string').expect(500);
    expect(logged).toEqual(['secret internals', 'just a string']);
    await app.close();
  });

  it('extend IntrinsicException (the base class of HttpException) for an error that should not be logged', async () => {
    const app = await createApp({ controllers: [D], app: { logger: capture } });

    await request(app.getHttpServer()).get('/d/intrinsic').expect(500);

    expect(logged).toEqual([]);
    await app.close();
  });
});

describe('Observations: which filter handles an exception', () => {
  it('@Catch() matches by instanceof: HttpException takes its subclasses, a specific class only itself', async () => {
    const HttpOnly = named('http', [HttpException]);
    const BadOnly = named('bad', [BadRequestException]);
    const results: Record<string, string> = {};

    for (const [label, F] of [['HttpException', HttpOnly], ['BadRequestException', BadOnly]] as const) {
      @Controller('m')
      @UseFilters(F)
      class M {
        @Get('bad') bad(): never { throw new BadRequestException(); }
        @Get('missing') missing(): never { throw new NotFoundException(); }
        @Get('plain') plain(): never { throw new Error('x'); }
      }
      const app = await createApp({ controllers: [M], app: { logger: capture } });
      for (const path of ['bad', 'missing', 'plain']) {
        const res = await request(app.getHttpServer()).get(`/m/${path}`);
        results[`${label} ${path}`] = res.body.by ?? `default ${res.status}`;
      }
      await app.close();
    }

    expect(results).toEqual({
      'HttpException bad': 'http',
      'HttpException missing': 'http',
      'HttpException plain': 'default 500',
      'BadRequestException bad': 'bad',
      'BadRequestException missing': 'default 404',
      'BadRequestException plain': 'default 500',
    });
  });

  it('only ONE filter handles an exception: the most specific scope, and the LAST one in @UseFilters(a, b)', async () => {
    const Global = named('global');
    const Controller_ = named('controller');
    const Method = named('method');
    const First = named('first');
    const Second = named('second');

    @Controller('s')
    @UseFilters(Controller_)
    class S {
      @Get('method') @UseFilters(Method) method(): never { throw new BadRequestException(); }
      @Get('controller') controller(): never { throw new BadRequestException(); }
      @Get('two') @UseFilters(First, Second) two(): never { throw new BadRequestException(); }
    }
    const app = await createApp({ controllers: [S], setup: (nest) => nest.useGlobalFilters(new Global()) });

    expect((await request(app.getHttpServer()).get('/s/method')).body.by).toBe('method');
    expect((await request(app.getHttpServer()).get('/s/controller')).body.by).toBe('controller');
    expect((await request(app.getHttpServer()).get('/s/two')).body.by).toBe('second');
    await app.close();
  });

  it('a filter must send the response itself: one that does not leaves the request hanging', async () => {
    @Catch()
    class Silent implements ExceptionFilter {
      catch(): void {}
    }
    @Controller('z')
    @UseFilters(Silent)
    class Z {
      @Get() z(): never { throw new BadRequestException(); }
    }
    const app = await createApp({ controllers: [Z] });

    await expect(
      (request(app.getHttpServer()).get('/z') as unknown as { timeout(o: object): Promise<unknown> }).timeout({ response: 300, deadline: 500 }),
    ).rejects.toMatchObject({ code: 'ECONNABORTED' });
    await app.close();
  });
});

describe('Observations: which exceptions reach a filter', () => {
  it('everything: from the handler, a guard, a pipe, an interceptor, middleware and an unknown path', async () => {
    class Deny implements CanActivate {
      canActivate(): boolean {
        return false;
      }
    }
    class RejectPipe implements PipeTransform {
      transform(): never {
        throw new BadRequestException('pipe');
      }
    }
    @Injectable()
    class ThrowingMiddleware implements NestMiddleware {
      use(): never {
        throw new BadRequestException('middleware');
      }
    }
    @Injectable()
    class Remap implements NestInterceptor {
      intercept(context: ExecutionContext, next: CallHandler) {
        return next.handle().pipe(catchError(() => throwError(() => new BadRequestException('interceptor'))));
      }
    }
    @Controller('r')
    class R {
      @Get('handler') handler(): never { throw new BadRequestException(); }
      @Get('guard') @UseGuards(Deny) guard(): string { return 'x'; }
      @Get('pipe/:v') pipe(@Param('v', RejectPipe) v: string): string { return v; }
      @Get('interceptor') @UseInterceptors(Remap) interceptor(): never { throw new Error('x'); }
    }
    @Controller('mw')
    class Mw {
      @Get() mw(): string { return 'ok'; }
    }
    @Module({ controllers: [R, Mw] })
    class M implements NestModule {
      configure(consumer: MiddlewareConsumer): void {
        consumer.apply(ThrowingMiddleware).forRoutes('mw');
      }
    }
    const All = named('catch-all');
    const app = await createApp({ imports: [M], setup: (nest) => nest.useGlobalFilters(new All()) });

    for (const path of ['/r/handler', '/r/guard', '/r/pipe/1', '/r/interceptor', '/mw', '/nothing-here']) {
      const res = await request(app.getHttpServer()).get(path);
      expect([path, res.body.by]).toEqual([path, 'catch-all']);
    }
    await app.close();
  });
});

describe('Observations: filters that extend BaseExceptionFilter', () => {
  it('a hand-built instance needs the HTTP adapter: without it, the failure falls through to Express HTML', async () => {
    @Catch()
    class Logging extends BaseExceptionFilter {
      catch(exception: unknown, host: ArgumentsHost): void {
        super.catch(exception, host);
      }
    }
    @Controller('x')
    class X {
      @Get() x(): never { throw new BadRequestException('bad'); }
    }
    const app = await createApp({ controllers: [X], setup: (nest) => nest.useGlobalFilters(new Logging()) });

    const res = await request(app.getHttpServer()).get('/x').expect(500);

    expect(res.headers['content-type']).toMatch(/html/);
    await app.close();
  });
});
