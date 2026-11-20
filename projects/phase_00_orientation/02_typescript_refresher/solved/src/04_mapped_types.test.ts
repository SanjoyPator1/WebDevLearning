import { describe, expectTypeOf, it } from 'vitest';
import type {
  Mutable,
  MyPartial,
  MyPick,
  MyReadonly,
  MyRecord,
  MyRequired,
} from './04_mapped_types.js';

type User = { readonly id: number; name: string; email?: string };

// There is nothing to run here. These tests are compile-time checks that
// `pnpm test` enforces through `tsc --noEmit`.
describe('04 mapped types', () => {
  it('MyPartial matches the built-in Partial', () => {
    expectTypeOf<MyPartial<User>>().toEqualTypeOf<Partial<User>>();
    expectTypeOf<MyPartial<User>>().toEqualTypeOf<{
      readonly id?: number;
      name?: string;
      email?: string;
    }>();
  });

  it('MyRequired removes optionality', () => {
    expectTypeOf<MyRequired<User>>().toEqualTypeOf<Required<User>>();
    expectTypeOf<MyRequired<{ a?: number }>>().toEqualTypeOf<{ a: number }>();
  });

  it('MyReadonly makes every property readonly', () => {
    expectTypeOf<MyReadonly<User>>().toEqualTypeOf<Readonly<User>>();
    expectTypeOf<MyReadonly<{ a: number }>>().toEqualTypeOf<{
      readonly a: number;
    }>();
  });

  it('Mutable removes readonly', () => {
    expectTypeOf<Mutable<User>>().toEqualTypeOf<{
      id: number;
      name: string;
      email?: string;
    }>();
    expectTypeOf<Mutable<Readonly<{ a: number }>>>().toEqualTypeOf<{ a: number }>();
  });

  it('MyPick keeps only the chosen keys', () => {
    expectTypeOf<MyPick<User, 'id' | 'name'>>().toEqualTypeOf<
      Pick<User, 'id' | 'name'>
    >();
  });

  it('MyPick only accepts real keys', () => {
    // @ts-expect-error 'nope' is not a key of User
    type Bad = MyPick<User, 'nope'>;
    expectTypeOf<Bad>().not.toBeAny();
  });

  it('MyRecord builds an object type from keys and a value type', () => {
    expectTypeOf<MyRecord<'a' | 'b', number>>().toEqualTypeOf<
      Record<'a' | 'b', number>
    >();
    expectTypeOf<MyRecord<string, boolean>>().toEqualTypeOf<
      Record<string, boolean>
    >();
  });
});
