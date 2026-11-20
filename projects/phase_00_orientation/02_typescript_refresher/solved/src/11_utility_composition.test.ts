import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  type CreateDto,
  type DeepReadonly,
  omit,
  pick,
  type PartialBy,
  type RequiredBy,
  type Simplify,
  type UpdateDto,
} from './11_utility_composition.js';

type User = {
  id: number;
  name: string;
  email: string;
  nickname?: string;
  createdAt: Date;
};

describe('11 utility type composition', () => {
  it('Simplify flattens an intersection into one object type', () => {
    expectTypeOf<Simplify<{ a: 1 } & { b: 2 }>>().toEqualTypeOf<{
      a: 1;
      b: 2;
    }>();
  });

  it('PartialBy makes only the chosen keys optional', () => {
    expectTypeOf<PartialBy<User, 'email' | 'createdAt'>>().toEqualTypeOf<{
      id: number;
      name: string;
      nickname?: string;
      email?: string;
      createdAt?: Date;
    }>();
  });

  it('RequiredBy makes only the chosen keys required', () => {
    expectTypeOf<RequiredBy<User, 'nickname'>>().toEqualTypeOf<{
      id: number;
      name: string;
      email: string;
      createdAt: Date;
      nickname: string;
    }>();
  });

  it('CreateDto drops server-owned keys', () => {
    expectTypeOf<CreateDto<User, 'id' | 'createdAt'>>().toEqualTypeOf<{
      name: string;
      email: string;
      nickname?: string;
    }>();
  });

  it('UpdateDto has no id and everything optional', () => {
    expectTypeOf<UpdateDto<User>>().toEqualTypeOf<{
      name?: string;
      email?: string;
      nickname?: string;
      createdAt?: Date;
    }>();
  });

  it('DeepReadonly freezes nested objects and arrays', () => {
    type Config = { server: { port: number; tags: string[] }; run: () => void };
    expectTypeOf<DeepReadonly<Config>>().toEqualTypeOf<{
      readonly server: {
        readonly port: number;
        readonly tags: readonly string[];
      };
      readonly run: () => void;
    }>();
  });

  it('omit and pick work at runtime and in the type', () => {
    const user = { id: 1, name: 'Ada', email: 'ada@example.com' };

    const withoutId = omit(user, ['id']);
    expect(withoutId).toEqual({ name: 'Ada', email: 'ada@example.com' });
    expectTypeOf(withoutId).toEqualTypeOf<{ name: string; email: string }>();
    expect(user).toHaveProperty('id'); // the original is not mutated

    const onlyName = pick(user, ['name']);
    expect(onlyName).toEqual({ name: 'Ada' });
    expectTypeOf(onlyName).toEqualTypeOf<{ name: string }>();
  });
});
