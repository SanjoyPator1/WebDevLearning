import {
  type ArgumentMetadata,
  type CallHandler,
  type CanActivate,
  Controller,
  type ExecutionContext,
  Get,
  Header,
  HttpCode,
  type NestInterceptor,
  type PipeTransform,
  UseGuards,
  UseInterceptors,
  applyDecorators,
  createParamDecorator,
} from '@nestjs/common';
import request from 'supertest';
import { createApp } from './helpers.js';

// These tests need none of your code. They pass from the start and record how custom decorators behave,
// measured on Nest 12.5.1 with Express 5. Read them, then change a line and watch one fail.

const log: string[] = [];

class SetUser implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    log.push('guard');
    context.switchToHttp().getRequest().user = { name: 'ada', roles: ['admin'] };
    return true;
  }
}

class Before implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler) {
    log.push('interceptor:before');
    return next.handle();
  }
}

class Spy implements PipeTransform {
  transform(value: unknown, metadata: ArgumentMetadata): unknown {
    log.push(`pipe(type=${metadata.type}, data=${String(metadata.data)}, metatype=${metadata.metatype?.name})`);
    return value;
  }
}

const User = createParamDecorator((data: string | undefined, context: ExecutionContext) => {
  log.push('factory');
  const user = context.switchToHttp().getRequest().user;
  return data ? user?.[data] : user;
});

const Later = createParamDecorator(async (data: string) => {
  await new Promise((resolve) => setTimeout(resolve, 5));
  return { later: data };
});

describe('Observations: custom parameter decorators', () => {
  beforeEach(() => {
    log.length = 0;
  });

  @Controller('p')
  @UseGuards(SetUser)
  class P {
    @Get('timing')
    @UseInterceptors(Before)
    timing(@User('name') name: string): string {
      log.push('handler');
      return name;
    }

    @Get('piped')
    piped(@User('name', Spy) name: string): string {
      return name;
    }

    @Get('pipe-first')
    pipeFirst(@User(Spy) user: unknown): unknown {
      return user;
    }

    @Get('async')
    asyncRoute(@Later('k', Spy) value: unknown): unknown {
      return value;
    }

    @Get('twice')
    twice(@User('name') a: string, @User('roles') b: string[]): unknown {
      return { a, b };
    }
  }

  it('the factory runs after the guard and inside the interceptors: guard, interceptor before, factory, handler', async () => {
    const app = await createApp({ controllers: [P] });

    await request(app.getHttpServer()).get('/p/timing').expect(200, 'ada');

    expect(log).toEqual(['guard', 'interceptor:before', 'factory', 'handler']);
    await app.close();
  });

  it('a pipe sees type "custom", the data you gave, and the TypeScript type of the parameter', async () => {
    const app = await createApp({ controllers: [P] });

    await request(app.getHttpServer()).get('/p/piped').expect(200);

    expect(log).toContain('pipe(type=custom, data=name, metatype=String)');
    await app.close();
  });

  it('if the first argument is a pipe it is treated as a pipe, not as data', async () => {
    const app = await createApp({ controllers: [P] });

    const res = await request(app.getHttpServer()).get('/p/pipe-first').expect(200);

    expect(res.body).toEqual({ name: 'ada', roles: ['admin'] });
    expect(log).toContain('pipe(type=custom, data=undefined, metatype=Object)');
    await app.close();
  });

  it('an async factory is awaited before the pipes see the value', async () => {
    const app = await createApp({ controllers: [P] });

    const res = await request(app.getHttpServer()).get('/p/async').expect(200);

    expect(res.body).toEqual({ later: 'k' });
    await app.close();
  });

  it('the factory runs once per use of the decorator, on every request', async () => {
    const app = await createApp({ controllers: [P] });

    await request(app.getHttpServer()).get('/p/twice').expect(200);
    await request(app.getHttpServer()).get('/p/twice').expect(200);

    expect(log.filter((entry) => entry === 'factory')).toHaveLength(4);
    await app.close();
  });
});

describe('Observations: applyDecorators', () => {
  beforeEach(() => {
    log.length = 0;
  });

  class G1 implements CanActivate {
    canActivate(): boolean {
      log.push('G1');
      return true;
    }
  }
  class G2 implements CanActivate {
    canActivate(): boolean {
      log.push('G2');
      return true;
    }
  }

  const Both = (): MethodDecorator & ClassDecorator => applyDecorators(UseGuards(G1), UseGuards(G2));
  const One = (): MethodDecorator & ClassDecorator => applyDecorators(UseGuards(G1));

  it('decorators are applied in the order listed, so guards run in that order', async () => {
    @Controller('a')
    class A {
      @Get()
      @Both()
      a(): string {
        return 'a';
      }
    }
    const app = await createApp({ controllers: [A] });

    await request(app.getHttpServer()).get('/a').expect(200);

    expect(log).toEqual(['G1', 'G2']);
    await app.close();
  });

  it('a composed decorator used on the class AND on a method binds its guards twice: they run twice', async () => {
    @Controller('b')
    @One()
    class B {
      @Get()
      @One()
      b(): string {
        return 'b';
      }
    }
    const app = await createApp({ controllers: [B] });

    await request(app.getHttpServer()).get('/b').expect(200);

    expect(log).toEqual(['G1', 'G1']);
    await app.close();
  });
});

describe('Observations: when the response status is set', () => {
  it('@HttpCode and @Header are applied after the guards and before the interceptors; a denied request gets neither', async () => {
    const seen: Record<string, unknown> = {};
    class GuardSpy implements CanActivate {
      canActivate(context: ExecutionContext): boolean {
        const res = context.switchToHttp().getResponse();
        seen.guard = { status: res.statusCode, header: res.getHeader('x-fixed') };
        return true;
      }
    }
    class InterceptorSpy implements NestInterceptor {
      intercept(context: ExecutionContext, next: CallHandler) {
        const res = context.switchToHttp().getResponse();
        seen.interceptor = { status: res.statusCode, header: res.getHeader('x-fixed') };
        return next.handle();
      }
    }
    class Deny implements CanActivate {
      canActivate(): boolean {
        return false;
      }
    }

    @Controller('h')
    class H {
      @Get()
      @HttpCode(202)
      @Header('x-fixed', 'yes')
      @UseGuards(GuardSpy)
      @UseInterceptors(InterceptorSpy)
      h(): string {
        return 'ok';
      }

      @Get('denied')
      @HttpCode(202)
      @Header('x-fixed', 'yes')
      @UseGuards(Deny)
      denied(): string {
        return 'ok';
      }
    }
    const app = await createApp({ controllers: [H] });

    await request(app.getHttpServer()).get('/h').expect(202);
    expect(seen.guard).toEqual({ status: 200, header: undefined });
    expect(seen.interceptor).toEqual({ status: 202, header: 'yes' });

    const denied = await request(app.getHttpServer()).get('/h/denied').expect(403);
    expect(denied.headers['x-fixed']).toBeUndefined();
    await app.close();
  });
});
