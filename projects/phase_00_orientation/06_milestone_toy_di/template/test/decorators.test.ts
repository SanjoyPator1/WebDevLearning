import 'reflect-metadata';
import { describe, expect, it } from 'vitest';
import { Inject, Injectable } from '../src/decorators.js';
import { DESIGN_PARAMTYPES, INJECTABLE_KEY, SELF_DEPS_KEY } from '../src/keys.js';
import type { SelfDeclaredDependency } from '../src/types.js';

// Fixture classes are declared INSIDE each test: decorators run when a class is defined, so a
// missing implementation fails that one test instead of the whole file.

describe('Task 1: @Injectable', () => {
  it('marks the class', () => {
    @Injectable()
    class Service {}

    expect(Reflect.getOwnMetadata(INJECTABLE_KEY, Service)).toBe(true);
  });

  it('marks only the decorated class, not its neighbour', () => {
    @Injectable()
    class Decorated {}
    class Plain {}

    expect(Reflect.hasOwnMetadata(INJECTABLE_KEY, Decorated)).toBe(true);
    expect(Reflect.hasOwnMetadata(INJECTABLE_KEY, Plain)).toBe(false);
  });

  it('is what makes the compiler emit design:paramtypes for the constructor', () => {
    class Dep {}
    @Injectable()
    class Decorated {
      constructor(readonly dep: Dep) {}
    }
    class Undecorated {
      constructor(readonly dep: Dep) {}
    }

    expect(Reflect.getMetadata(DESIGN_PARAMTYPES, Decorated)).toEqual([Dep]);
    // No decorator, no metadata: a container reading this would think there are no dependencies.
    expect(Reflect.getMetadata(DESIGN_PARAMTYPES, Undecorated)).toBeUndefined();
  });
});

describe('Task 2: @Inject', () => {
  it('records the index and token of a string-token parameter', () => {
    @Injectable()
    class Service {
      constructor(@Inject('API_URL') readonly url: string) {}
    }

    expect(Reflect.getOwnMetadata(SELF_DEPS_KEY, Service)).toEqual([{ index: 0, token: 'API_URL' }]);
  });

  it('keeps every @Inject of the same constructor, whatever the order they ran in', () => {
    const LOGGER = Symbol('LOGGER');
    @Injectable()
    class Service {
      constructor(
        @Inject('API_URL') readonly url: string,
        readonly plain: number,
        @Inject(LOGGER) readonly logger: object,
      ) {}
    }

    const stored: SelfDeclaredDependency[] = Reflect.getOwnMetadata(SELF_DEPS_KEY, Service);
    expect([...stored].sort((a, b) => a.index - b.index)).toEqual([
      { index: 0, token: 'API_URL' },
      { index: 2, token: LOGGER },
    ]);
  });

  it('keeps classes apart', () => {
    @Injectable()
    class A {
      constructor(@Inject('A_TOKEN') readonly a: string) {}
    }
    @Injectable()
    class B {
      constructor(@Inject('B_TOKEN') readonly b: string) {}
    }

    expect(Reflect.getOwnMetadata(SELF_DEPS_KEY, A)).toEqual([{ index: 0, token: 'A_TOKEN' }]);
    expect(Reflect.getOwnMetadata(SELF_DEPS_KEY, B)).toEqual([{ index: 0, token: 'B_TOKEN' }]);
  });

  it('rejects method parameters', () => {
    expect(() => {
      class Service {
        run(@Inject('X') x: string) {}
      }
      return Service;
    }).toThrow(/constructor parameters/);
  });
});
