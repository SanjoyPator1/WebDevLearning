import 'reflect-metadata';
import { describe, expect, it } from 'vitest';
import { Controller, Field, Get, Param, Post } from '../src/decorators.js';
import { DESIGN_PARAMTYPES, FIELDS_KEY, PARAMS_KEY, PREFIX_KEY, ROUTE_KEY } from '../src/keys.js';
import type { ParamMetadata } from '../src/types.js';

// Fixture classes are declared INSIDE each test on purpose: decorators run when a class is
// defined, so a missing implementation fails that one test instead of the whole file.

interface Settings {
  dark: boolean;
}
class Owner {}

describe('Task 1: @Controller (class decorator)', () => {
  it('stores the prefix on the class', () => {
    @Controller('cats')
    class CatsController {}

    expect(Reflect.getMetadata(PREFIX_KEY, CatsController)).toBe('cats');
  });

  it('keeps every class separate', () => {
    @Controller('cats')
    class CatsController {}
    @Controller('dogs')
    class DogsController {}

    expect(Reflect.getMetadata(PREFIX_KEY, CatsController)).toBe('cats');
    expect(Reflect.getMetadata(PREFIX_KEY, DogsController)).toBe('dogs');
  });
});

describe('Task 2: @Get and @Post (method decorators)', () => {
  it('@Get stores the HTTP method and path on the prototype, for that method', () => {
    class C {
      @Get('/list')
      list() {}
    }

    expect(Reflect.getMetadata(ROUTE_KEY, C.prototype, 'list')).toEqual({
      httpMethod: 'GET',
      path: '/list',
    });
  });

  it('@Post stores POST', () => {
    class C {
      @Post('create')
      create() {}
    }

    expect(Reflect.getMetadata(ROUTE_KEY, C.prototype, 'create')).toEqual({
      httpMethod: 'POST',
      path: 'create',
    });
  });

  it('the path defaults to an empty string', () => {
    class C {
      @Get()
      root() {}
    }

    expect(Reflect.getMetadata(ROUTE_KEY, C.prototype, 'root')).toEqual({ httpMethod: 'GET', path: '' });
  });

  it('leaves undecorated methods alone', () => {
    class C {
      @Get()
      decorated() {}
      plain() {}
    }

    expect(Reflect.hasMetadata(ROUTE_KEY, C.prototype, 'decorated')).toBe(true);
    expect(Reflect.hasMetadata(ROUTE_KEY, C.prototype, 'plain')).toBe(false);
  });

  it('the compiler emitted design:paramtypes for the decorated method', () => {
    // Nothing to implement here beyond Get: any decorator on a method makes the compiler
    // emit its parameter types. This is the data the scanner reads in Task 6.
    class C {
      @Get()
      run(a: number, b: string): void {}
    }

    expect(Reflect.getMetadata(DESIGN_PARAMTYPES, C.prototype, 'run')).toEqual([Number, String]);
  });
});

describe('Task 3: @Param (parameter decorator)', () => {
  it('records the parameter index and name', () => {
    class C {
      @Get()
      find(@Param('id') id: string) {}
    }

    expect(Reflect.getMetadata(PARAMS_KEY, C.prototype, 'find')).toEqual([{ index: 0, name: 'id' }]);
  });

  it('keeps every @Param of the same method', () => {
    class C {
      @Get()
      find(@Param('id') id: string, @Param('verbose') verbose: boolean, @Param('page') page: number) {}
    }

    // Parameter decorators run last to first, so the stored order is an implementation detail.
    const stored: ParamMetadata[] = Reflect.getMetadata(PARAMS_KEY, C.prototype, 'find');
    expect([...stored].sort((a, b) => a.index - b.index)).toEqual([
      { index: 0, name: 'id' },
      { index: 1, name: 'verbose' },
      { index: 2, name: 'page' },
    ]);
  });

  it('keeps parameters of different methods apart', () => {
    class C {
      @Get()
      one(@Param('a') a: string) {}
      @Get()
      two(@Param('b') b: string) {}
    }

    expect(Reflect.getMetadata(PARAMS_KEY, C.prototype, 'one')).toEqual([{ index: 0, name: 'a' }]);
    expect(Reflect.getMetadata(PARAMS_KEY, C.prototype, 'two')).toEqual([{ index: 0, name: 'b' }]);
  });

  it('rejects constructor parameters (propertyKey is undefined there)', () => {
    expect(() => {
      class C {
        constructor(@Param('x') x: string) {}
      }
      return C;
    }).toThrow(/method parameters/);
  });
});

describe('Task 4: @Field (property decorator)', () => {
  it('records the name and the design:type of primitive properties, in declaration order', () => {
    class Todo {
      @Field() id!: number;
      @Field() title!: string;
      @Field() done!: boolean;
    }

    expect(Reflect.getMetadata(FIELDS_KEY, Todo)).toEqual([
      { name: 'id', type: Number },
      { name: 'title', type: String },
      { name: 'done', type: Boolean },
    ]);
  });

  it('records class and array types', () => {
    class Todo {
      @Field() owner!: Owner;
      @Field() tags!: string[];
    }

    expect(Reflect.getMetadata(FIELDS_KEY, Todo)).toEqual([
      { name: 'owner', type: Owner },
      { name: 'tags', type: Array },
    ]);
  });

  it('records Object for an interface type, because interfaces do not exist at runtime', () => {
    class Todo {
      @Field() settings!: Settings;
    }

    expect(Reflect.getMetadata(FIELDS_KEY, Todo)).toEqual([{ name: 'settings', type: Object }]);
  });

  it('stores the list on the class, not on the prototype, and keeps classes apart', () => {
    class A {
      @Field() a!: string;
    }
    class B {
      @Field() b!: number;
    }

    expect(Reflect.getMetadata(FIELDS_KEY, A)).toEqual([{ name: 'a', type: String }]);
    expect(Reflect.getMetadata(FIELDS_KEY, B)).toEqual([{ name: 'b', type: Number }]);
    expect(Reflect.hasMetadata(FIELDS_KEY, A.prototype)).toBe(false);
  });
});
