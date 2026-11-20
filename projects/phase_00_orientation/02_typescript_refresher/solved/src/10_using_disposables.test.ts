import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  AsyncConnection,
  cleanupInReverse,
  Connection,
  runQuery,
  runQueryAsync,
} from './10_using_disposables.js';

describe('10 using and disposables', () => {
  it('Connection and AsyncConnection satisfy the disposable interfaces', () => {
    expectTypeOf<Connection>().toExtend<Disposable>();
    expectTypeOf<AsyncConnection>().toExtend<AsyncDisposable>();
  });

  it('runQuery closes the connection after the query', () => {
    const log: string[] = [];
    expect(runQuery(log)).toBe('result of select 1');
    expect(log).toEqual(['open:1', 'query:select 1', 'close:1']);
  });

  it('runQuery closes the connection even when it throws', () => {
    const log: string[] = [];
    expect(() => runQuery(log, true)).toThrow('query failed');
    expect(log).toEqual(['open:1', 'close:1']);
  });

  it('runQueryAsync awaits the asynchronous cleanup', async () => {
    const log: string[] = [];
    await runQueryAsync(log);
    expect(log).toEqual(['open:2', 'using:2', 'close:2']);
  });

  it('cleanupInReverse releases in reverse registration order', () => {
    const log: string[] = [];
    cleanupInReverse(log);
    expect(log).toEqual([
      'body',
      'third registered',
      'second registered',
      'first registered',
    ]);
  });
});
