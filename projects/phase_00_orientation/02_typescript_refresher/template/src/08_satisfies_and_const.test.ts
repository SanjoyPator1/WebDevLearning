import { describe, expect, expectTypeOf, it } from 'vitest';
import { defineRoute, palette, tupleOf } from './08_satisfies_and_const.js';

describe('08 satisfies and const type parameters', () => {
  it('palette keeps its precise value types', () => {
    expect(palette.red).toEqual([255, 0, 0]);
    expect(palette.green).toBe('#00ff00');
    expectTypeOf(palette.red).toEqualTypeOf<number[]>();
    expectTypeOf(palette.green).toEqualTypeOf<string>();
  });

  it('palette does not allow keys that are not there', () => {
    // @ts-expect-error 'blue' does not exist on palette
    void palette.blue;
  });

  it('tupleOf infers a readonly tuple of literals', () => {
    const tuple = tupleOf(['GET', 200]);
    expect(tuple).toEqual(['GET', 200]);
    expectTypeOf(tuple).toEqualTypeOf<readonly ['GET', 200]>();
  });

  it('defineRoute keeps literal property types', () => {
    const route = defineRoute({ method: 'GET', path: '/users' });
    expect(route).toEqual({ method: 'GET', path: '/users' });
    expectTypeOf(route.method).toEqualTypeOf<'GET'>();
    expectTypeOf(route.path).toEqualTypeOf<'/users'>();
  });
});
