import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  assertIsDefined,
  describeValue,
  isNonEmptyString,
} from './01_narrowing.js';

describe('01 narrowing', () => {
  it('describeValue handles primitives and nullish values', () => {
    expect(describeValue('hi')).toBe('string:hi');
    expect(describeValue(42)).toBe('number:42');
    expect(describeValue(true)).toBe('boolean:true');
    expect(describeValue(null)).toBe('null');
    expect(describeValue(undefined)).toBe('undefined');
  });

  it('describeValue handles arrays, dates and objects', () => {
    expect(describeValue([1, 2, 3])).toBe('array:3');
    expect(describeValue(new Date('2026-01-02T03:04:05.000Z'))).toBe(
      'date:2026-01-02T03:04:05.000Z',
    );
    expect(describeValue({ name: 'nest' })).toBe('named:nest');
    expect(describeValue({ name: 1 })).toBe('object');
    expect(describeValue({})).toBe('object');
  });

  it('describeValue falls back to typeof for the rest', () => {
    expect(describeValue(10n)).toBe('bigint');
    expect(describeValue(Symbol('s'))).toBe('symbol');
    expect(describeValue(() => 1)).toBe('function');
  });

  it('isNonEmptyString is a type predicate', () => {
    expect(isNonEmptyString('a')).toBe(true);
    expect(isNonEmptyString('')).toBe(false);
    expect(isNonEmptyString(5)).toBe(false);

    const input = 'abc' as unknown;
    if (isNonEmptyString(input)) {
      // Compile-time check: this fails to compile until the return type is a predicate.
      expectTypeOf(input).toEqualTypeOf<string>();
    }
  });

  it('assertIsDefined throws and narrows', () => {
    expect(() => assertIsDefined(null)).toThrow('Expected value to be defined');
    expect(() => assertIsDefined(undefined, 'custom')).toThrow('custom');
    expect(() => assertIsDefined(0)).not.toThrow();

    const maybe = 'x' as string | undefined;
    assertIsDefined(maybe);
    // Compile-time check: fails to compile until the function has an `asserts` return type.
    expectTypeOf(maybe).toEqualTypeOf<string>();
  });
});
