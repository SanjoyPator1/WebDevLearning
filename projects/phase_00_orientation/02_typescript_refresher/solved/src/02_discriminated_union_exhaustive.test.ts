import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  area,
  assertNever,
  describeShape,
  type ShapeKind,
  type ShapeOf,
} from './02_discriminated_union_exhaustive.js';

describe('02 discriminated union exhaustive', () => {
  it('computes areas', () => {
    expect(area({ kind: 'circle', radius: 2 })).toBeCloseTo(Math.PI * 4);
    expect(area({ kind: 'square', side: 3 })).toBe(9);
    expect(area({ kind: 'rectangle', width: 2, height: 5 })).toBe(10);
  });

  it('describes shapes', () => {
    expect(describeShape({ kind: 'circle', radius: 2 })).toBe('circle r=2');
    expect(describeShape({ kind: 'square', side: 3 })).toBe('square s=3');
    expect(describeShape({ kind: 'rectangle', width: 2, height: 5 })).toBe(
      'rectangle 2x5',
    );
  });

  it('assertNever throws with the offending value', () => {
    expect(() => {
      // @ts-expect-error a real value is never assignable to `never`
      assertNever({ kind: 'triangle' });
    }).toThrow('Unexpected value: {"kind":"triangle"}');
  });

  it('assertNever takes a parameter of type never', () => {
    expectTypeOf(assertNever).toEqualTypeOf<(value: never) => never>();
  });

  it('ShapeKind is the union of discriminants', () => {
    expectTypeOf<ShapeKind>().toEqualTypeOf<'circle' | 'square' | 'rectangle'>();
  });

  it('ShapeOf selects one member', () => {
    expectTypeOf<ShapeOf<'circle'>>().toEqualTypeOf<{
      kind: 'circle';
      radius: number;
    }>();
    expectTypeOf<ShapeOf<'square' | 'rectangle'>>().toEqualTypeOf<
      { kind: 'square'; side: number } | { kind: 'rectangle'; width: number; height: number }
    >();
  });
});
