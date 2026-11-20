import 'reflect-metadata';
import { describe, expect, it } from 'vitest';
import { Controller, Field, Get, Param, Post } from '../src/decorators.js';
import { getFields, scanController } from '../src/scanner.js';

class Owner {}

describe('Task 5: getFields', () => {
  it('returns the fields recorded by @Field()', () => {
    class Todo {
      @Field() id!: number;
      @Field() owner!: Owner;
    }

    expect(getFields(Todo)).toEqual([
      { name: 'id', type: Number },
      { name: 'owner', type: Owner },
    ]);
  });

  it('returns an empty list for a class without fields', () => {
    class Empty {}

    expect(getFields(Empty)).toEqual([]);
  });
});

describe('Task 6: scanController', () => {
  function defineCatsController() {
    @Controller('cats')
    class CatsController {
      @Get()
      findAll(@Param('limit') limit: number) {}

      @Get(':id')
      findOne(@Param('id') id: string, @Param('verbose') verbose: boolean) {}

      @Post('/')
      create(@Param('name') name: string, @Param('owner') owner: Owner) {}

      @Get('ping')
      ping() {}

      helper() {}
    }
    return CatsController;
  }

  it('builds the whole route table, in declaration order, with joined paths', () => {
    expect(scanController(defineCatsController())).toEqual([
      {
        httpMethod: 'GET',
        path: '/cats',
        handler: 'findAll',
        params: [{ index: 0, name: 'limit', type: Number }],
      },
      {
        httpMethod: 'GET',
        path: '/cats/:id',
        handler: 'findOne',
        params: [
          { index: 0, name: 'id', type: String },
          { index: 1, name: 'verbose', type: Boolean },
        ],
      },
      {
        httpMethod: 'POST',
        path: '/cats',
        handler: 'create',
        params: [
          { index: 0, name: 'name', type: String },
          { index: 1, name: 'owner', type: Owner },
        ],
      },
      { httpMethod: 'GET', path: '/cats/ping', handler: 'ping', params: [] },
    ]);
  });

  it('ignores methods that have no route decorator', () => {
    const handlers = scanController(defineCatsController()).map((route) => route.handler);

    expect(handlers).not.toContain('helper');
    expect(handlers).not.toContain('constructor');
  });

  it('sorts params by index even though decorators ran last to first', () => {
    const findOne = scanController(defineCatsController()).find((route) => route.handler === 'findOne');

    expect(findOne?.params.map((param) => param.index)).toEqual([0, 1]);
  });

  it('works with an empty prefix', () => {
    @Controller('')
    class RootController {
      @Get('health')
      health() {}
    }

    expect(scanController(RootController)).toEqual([
      { httpMethod: 'GET', path: '/health', handler: 'health', params: [] },
    ]);
  });

  it('throws when the class is not decorated with @Controller()', () => {
    class NotAController {
      @Get()
      run() {}
    }

    expect(() => scanController(NotAController)).toThrow('NotAController is not decorated with @Controller()');
  });
});
