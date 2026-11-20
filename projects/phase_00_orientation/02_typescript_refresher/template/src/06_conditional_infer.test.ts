import { describe, expectTypeOf, it } from 'vitest';
import type {
  ElementOf,
  FirstArg,
  IsNever,
  ReturnTypeOf,
  ToArray,
  ToArrayWhole,
  Unwrap,
} from './06_conditional_infer.js';

describe('06 conditional types and infer', () => {
  it('Unwrap peels promises recursively and leaves other types alone', () => {
    expectTypeOf<Unwrap<Promise<string>>>().toEqualTypeOf<string>();
    expectTypeOf<Unwrap<Promise<Promise<number>>>>().toEqualTypeOf<number>();
    expectTypeOf<Unwrap<boolean>>().toEqualTypeOf<boolean>();
  });

  it('ElementOf extracts the element type of arrays and tuples', () => {
    expectTypeOf<ElementOf<string[]>>().toEqualTypeOf<string>();
    expectTypeOf<ElementOf<readonly [1, 'a']>>().toEqualTypeOf<1 | 'a'>();
    expectTypeOf<ElementOf<number>>().toBeNever();
  });

  it('FirstArg extracts the first parameter type', () => {
    expectTypeOf<FirstArg<(id: number, flag: boolean) => void>>().toEqualTypeOf<number>();
    // With no parameter to infer from, `infer A` has no candidates and falls back to unknown.
    expectTypeOf<FirstArg<() => void>>().toBeUnknown();
    expectTypeOf<FirstArg<string>>().toBeNever();
  });

  it('ReturnTypeOf extracts the return type', () => {
    expectTypeOf<ReturnTypeOf<() => Promise<string>>>().toEqualTypeOf<Promise<string>>();
    expectTypeOf<ReturnTypeOf<string>>().toBeNever();
  });

  it('ToArray distributes over unions', () => {
    expectTypeOf<ToArray<string | number>>().toEqualTypeOf<string[] | number[]>();
  });

  it('ToArrayWhole does not distribute', () => {
    expectTypeOf<ToArrayWhole<string | number>>().toEqualTypeOf<(string | number)[]>();
  });

  it('IsNever detects never without distributing', () => {
    expectTypeOf<IsNever<never>>().toEqualTypeOf<true>();
    expectTypeOf<IsNever<string>>().toEqualTypeOf<false>();
    expectTypeOf<IsNever<undefined>>().toEqualTypeOf<false>();
  });
});
