import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  type EventHandlers,
  type Getters,
  makeGetters,
  type OnlyFunctions,
  type RemoveKey,
} from './05_key_remapping.js';

type Person = { name: string; age: number };

describe('05 key remapping', () => {
  it('Getters renames keys to getX and wraps values in functions', () => {
    expectTypeOf<Getters<Person>>().toEqualTypeOf<{
      getName: () => string;
      getAge: () => number;
    }>();
  });

  it('RemoveKey drops one key', () => {
    expectTypeOf<RemoveKey<{ kind: 'a'; value: number }, 'kind'>>().toEqualTypeOf<{
      value: number;
    }>();
  });

  it('OnlyFunctions keeps only function-valued keys', () => {
    type Service = { name: string; run: () => void; stop(code: number): boolean };
    expectTypeOf<OnlyFunctions<Service>>().toEqualTypeOf<{
      run: () => void;
      stop: (code: number) => boolean;
    }>();
  });

  it('EventHandlers builds onX handler signatures', () => {
    expectTypeOf<EventHandlers<{ click: { x: number }; close: undefined }>>().toEqualTypeOf<{
      onClick: (payload: { x: number }) => void;
      onClose: (payload: undefined) => void;
    }>();
  });

  it('makeGetters builds real getter functions', () => {
    const getters = makeGetters({ name: 'Ada', age: 36 });
    expect(getters.getName()).toBe('Ada');
    expect(getters.getAge()).toBe(36);
    expect(Object.keys(getters).sort()).toEqual(['getAge', 'getName']);
    expectTypeOf(getters.getName).toEqualTypeOf<() => string>();
    expectTypeOf(getters.getAge).toEqualTypeOf<() => number>();
  });
});
