import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  type Box,
  getProp,
  groupBy,
  pluck,
  Stack,
} from './03_generic_constraints.js';

type User = { id: number; name: string; role: 'admin' | 'user' };

const users: User[] = [
  { id: 1, name: 'Ada', role: 'admin' },
  { id: 2, name: 'Linus', role: 'user' },
  { id: 3, name: 'Grace', role: 'admin' },
];

describe('03 generic constraints', () => {
  it('getProp returns the value with the exact property type', () => {
    const user = users[0]!;
    expect(getProp(user, 'name')).toBe('Ada');
    expectTypeOf(getProp(user, 'id')).toEqualTypeOf<number>();
    expectTypeOf(getProp(user, 'role')).toEqualTypeOf<'admin' | 'user'>();
  });

  it('getProp rejects keys that do not exist', () => {
    const user = users[0]!;
    const bad = () => {
      // @ts-expect-error 'nope' is not a key of User
      return getProp(user, 'nope');
    };
    expect(bad).toBeTypeOf('function');
  });

  it('pluck returns an array of the property type', () => {
    expect(pluck(users, 'name')).toEqual(['Ada', 'Linus', 'Grace']);
    expectTypeOf(pluck(users, 'id')).toEqualTypeOf<number[]>();
  });

  it('groupBy infers the key union from the callback', () => {
    const grouped = groupBy(users, (u) => u.role);
    expect(grouped.admin?.map((u) => u.id)).toEqual([1, 3]);
    expect(grouped.user?.map((u) => u.id)).toEqual([2]);
    expectTypeOf(grouped).toEqualTypeOf<
      Partial<Record<'admin' | 'user', User[]>>
    >();
  });

  it('Box has a default type parameter', () => {
    expectTypeOf<Box>().toEqualTypeOf<{ value: string }>();
    expectTypeOf<Box<number>>().toEqualTypeOf<{ value: number }>();
  });

  it('Stack is a generic class', () => {
    const stack = new Stack<number>();
    expect(stack.size).toBe(0);
    expect(stack.pop()).toBeUndefined();
    stack.push(1);
    stack.push(2);
    expect(stack.peek()).toBe(2);
    expect(stack.pop()).toBe(2);
    expect(stack.size).toBe(1);
    expectTypeOf(stack.pop()).toEqualTypeOf<number | undefined>();
    expectTypeOf(stack.size).toEqualTypeOf<number>();
  });
});
