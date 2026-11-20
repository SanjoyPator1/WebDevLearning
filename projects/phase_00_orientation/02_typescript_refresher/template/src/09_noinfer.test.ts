import { describe, expect, expectTypeOf, it } from 'vitest';
import { createMachine, firstOr } from './09_noinfer.js';

describe('09 NoInfer', () => {
  it('createMachine infers the state union from the states array only', () => {
    const machine = createMachine(['idle', 'running', 'done'], 'idle');
    expect(machine.state).toBe('idle');
    expectTypeOf(machine.state).toEqualTypeOf<'idle' | 'running' | 'done'>();
  });

  it('createMachine rejects an initial state that is not in the list', () => {
    const bad = () =>
      // @ts-expect-error 'idel' is not one of the states
      createMachine(['idle', 'running'], 'idel');
    expect(bad).toBeTypeOf('function');
  });

  it('firstOr returns the element type and rejects a mismatching fallback', () => {
    expect(firstOr([1, 2], 0)).toBe(1);
    expect(firstOr<number>([], 7)).toBe(7);
    expectTypeOf(firstOr([1, 2], 0)).toEqualTypeOf<number>();

    const bad = () =>
      // @ts-expect-error a string fallback does not match number[]
      firstOr([1, 2], 'none');
    expect(bad).toBeTypeOf('function');
  });
});
