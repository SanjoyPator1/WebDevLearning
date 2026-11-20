import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  HttpError,
  isHttpError,
  type Result,
  safeJsonParse,
  toErrorMessage,
  tryCatch,
  tryCatchAsync,
} from './12_error_handling_unknown.js';

describe('12 error handling with unknown', () => {
  it('toErrorMessage handles everything that can be thrown', () => {
    expect(toErrorMessage(new Error('boom'))).toBe('boom');
    expect(toErrorMessage('plain string')).toBe('plain string');
    expect(toErrorMessage({ message: 'from object' })).toBe('from object');
    expect(toErrorMessage({ code: 42 })).toBe('{"code":42}');
    expect(toErrorMessage(undefined)).toBe('undefined');
    expectTypeOf(toErrorMessage).parameter(0).toBeUnknown();
  });

  it('HttpError carries a status and a cause', () => {
    const cause = new Error('db down');
    const error = new HttpError('Service unavailable', 503, { cause });
    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe('HttpError');
    expect(error.status).toBe(503);
    expect(error.message).toBe('Service unavailable');
    expect(error.cause).toBe(cause);
    expectTypeOf(error.status).toEqualTypeOf<number>();
  });

  it('isHttpError is a type predicate', () => {
    expect(isHttpError(new HttpError('x', 400))).toBe(true);
    expect(isHttpError(new Error('x'))).toBe(false);

    const caught = new HttpError('x', 404) as unknown;
    if (isHttpError(caught)) {
      expectTypeOf(caught).toEqualTypeOf<HttpError>();
    }
  });

  it('tryCatch returns a Result and narrows on ok', () => {
    const good = tryCatch(() => 21 * 2);
    expect(good).toEqual({ ok: true, value: 42 });
    expectTypeOf(good).toEqualTypeOf<Result<number>>();
    if (good.ok) {
      expectTypeOf(good.value).toEqualTypeOf<number>();
    } else {
      expectTypeOf(good.error).toEqualTypeOf<Error>();
    }

    const bad = tryCatch(() => {
      throw new Error('nope');
    });
    expect(bad.ok).toBe(false);
    if (!bad.ok) expect(bad.error.message).toBe('nope');
  });

  it('tryCatch wraps non-Error throwables and keeps the original as cause', () => {
    const result = tryCatch(() => {
      throw 'a string was thrown';
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBeInstanceOf(Error);
      expect(result.error.message).toBe('a string was thrown');
      expect(result.error.cause).toBe('a string was thrown');
    }
  });

  it('tryCatchAsync handles resolved and rejected promises', async () => {
    const good = await tryCatchAsync(async () => 'ok');
    expect(good).toEqual({ ok: true, value: 'ok' });

    const bad = await tryCatchAsync(async () => {
      throw new HttpError('gone', 410);
    });
    expect(bad.ok).toBe(false);
    if (!bad.ok) expect(isHttpError(bad.error)).toBe(true);
  });

  it('safeJsonParse gives unknown, not any', () => {
    const parsed = safeJsonParse('{"a":1}');
    expect(parsed).toEqual({ ok: true, value: { a: 1 } });
    if (parsed.ok) expectTypeOf(parsed.value).toBeUnknown();

    const broken = safeJsonParse('{oops');
    expect(broken.ok).toBe(false);
    if (!broken.ok) expect(broken.error).toBeInstanceOf(SyntaxError);
  });
});
