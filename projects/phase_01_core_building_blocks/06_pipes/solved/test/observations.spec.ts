import {
  type ArgumentMetadata,
  BadRequestException,
  Body,
  Controller,
  DefaultValuePipe,
  Get,
  Headers,
  type PipeTransform,
  Param,
  ParseIntPipe,
  Post,
  Query,
  Req,
  createParamDecorator,
} from '@nestjs/common';
import request from 'supertest';
import { createApp } from './helpers.js';

// These tests need none of your code. They pass from the start and record how pipes behave,
// measured on Nest 12.5.1 with Express 5. Read them, then change a line and watch one fail.

const Custom = createParamDecorator((data: string) => `custom-${data}`);

class CreateDto {
  name!: string;
}

const seen: string[] = [];
class Spy implements PipeTransform {
  transform(value: unknown, metadata: ArgumentMetadata): unknown {
    seen.push(`${metadata.type}:${String(metadata.data)}:${metadata.metatype?.name ?? 'none'}`);
    return value;
  }
}

@Controller('obs')
class ObsController {
  @Post('args/:id')
  args(
    @Body() body: CreateDto,
    @Query('n') n: number,
    @Param('id') id: string,
    @Headers('h') h: string,
    @Req() req: unknown,
    @Custom('k') c: string,
  ): string {
    return 'ok';
  }

  @Get('int/:v')
  int(@Param('v', ParseIntPipe) v: number): { v: number } {
    return { v };
  }

  @Get('default-then-int')
  defaultThenInt(@Query('n', new DefaultValuePipe(10), ParseIntPipe) n: number): { n: number } {
    return { n };
  }

  @Get('int-then-default')
  intThenDefault(@Query('n', ParseIntPipe, new DefaultValuePipe(10)) n: number): { n: number } {
    return { n };
  }

  @Get('default-only')
  defaultOnly(@Query('x', new DefaultValuePipe('dflt')) x: string): { x: string } {
    return { x };
  }
}

describe('Observations: what pipes receive and how they behave', () => {
  beforeEach(() => {
    seen.length = 0;
  });

  it('ParseIntPipe is strict: only an optional minus and digits, never 5.5, 1e3, +5 or 0x10', async () => {
    const { app } = await createApp([ObsController]);

    for (const [raw, expected] of [['5', 5], ['-5', -5], ['007', 7]] as const) {
      const res = await request(app.getHttpServer()).get(`/obs/int/${raw}`).expect(200);
      expect(res.body).toEqual({ v: expected });
    }
    for (const raw of ['5.5', '1e3', '+5', '0x10', 'abc']) {
      await request(app.getHttpServer()).get(`/obs/int/${raw}`).expect(400);
    }
    await app.close();
  });

  it('DefaultValuePipe replaces only null, undefined and NaN: an empty string stays empty', async () => {
    const { app } = await createApp([ObsController]);

    await request(app.getHttpServer()).get('/obs/default-only').expect(200, { x: 'dflt' });
    await request(app.getHttpServer()).get('/obs/default-only?x=').expect(200, { x: '' });
    await app.close();
  });

  it('the order of pipes matters: default first works, parse first rejects the missing value', async () => {
    const { app } = await createApp([ObsController]);

    await request(app.getHttpServer()).get('/obs/default-then-int').expect(200, { n: 10 });
    await request(app.getHttpServer()).get('/obs/int-then-default').expect(400);
    await app.close();
  });

  it('a pipe sees type, data and metatype; @Headers() and @Req() are never piped', async () => {
    const { app } = await createApp([ObsController], { setup: (nest) => nest.useGlobalPipes(new Spy()) });

    await request(app.getHttpServer()).post('/obs/args/7?n=1').set('h', 'v').send({}).expect(201);

    expect([...seen].sort()).toEqual([
      'body:undefined:CreateDto',
      'custom:k:String',
      'param:id:String',
      'query:n:Number',
    ]);
    await app.close();
  });

  it('an error thrown by a pipe stops the request: BadRequestException is a 400, a plain Error a 500', async () => {
    class Reject implements PipeTransform {
      transform(): never {
        throw new BadRequestException('nope');
      }
    }
    class Crash implements PipeTransform {
      transform(): never {
        throw new Error('bug');
      }
    }
    const ran: string[] = [];

    @Controller('fail')
    class FailController {
      @Get('reject/:v')
      reject(@Param('v', Reject) v: string): string {
        ran.push('handler');
        return v;
      }

      @Get('crash/:v')
      crash(@Param('v', Crash) v: string): string {
        ran.push('handler');
        return v;
      }
    }
    const { app } = await createApp([FailController]);

    const rejected = await request(app.getHttpServer()).get('/fail/reject/x').expect(400);
    expect(rejected.body.message).toBe('nope');
    const crashed = await request(app.getHttpServer()).get('/fail/crash/x').expect(500);
    expect(crashed.body).toEqual({ statusCode: 500, message: 'Internal server error' });
    expect(ran).toEqual([]);
    await app.close();
  });
});

