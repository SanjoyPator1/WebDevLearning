// Kata 10: `using`, `await using` and DisposableStack (topic 0.2, TypeScript 5.2)
//
// Explicit resource management: a resource releases itself when the scope that
// declared it ends, whether by return, throw or break.
// Syntax reminder: `using x = new Thing();` calls x[Symbol.dispose]() at scope end,
// and `await using x = ...` calls x[Symbol.asyncDispose]() and awaits it.

/**
 * TODO(0.2): make this class Disposable. Its dispose method must push `close:${id}` onto the log.
 * Not part of this exercise: the constructor and `query` are given.
 */
export class Connection {
  constructor(
    private readonly log: string[],
    readonly id: number,
  ) {
    this.log.push(`open:${id}`);
  }

  query(sql: string): string {
    this.log.push(`query:${sql}`);
    return `result of ${sql}`;
  }
}

/**
 * TODO(0.2): make this class AsyncDisposable. Its async dispose method awaits
 * something (for example Promise.resolve()) and then pushes `close:${id}`.
 */
export class AsyncConnection {
  constructor(
    private readonly log: string[],
    readonly id: number,
  ) {
    this.log.push(`open:${id}`);
  }
}

/**
 * TODO(0.2): open a Connection(log, 1) with `using`. If shouldThrow, throw
 * new Error('query failed'). Otherwise return connection.query('select 1').
 * Expected log on success: open:1, query:select 1, close:1. On throw: open:1, close:1.
 */
export function runQuery(log: string[], shouldThrow = false): string {
  throw new Error('TODO(0.2): implement runQuery');
}

/** TODO(0.2): open an AsyncConnection(log, 2) with `await using`, then push `using:2`. Expected log: open:2, using:2, close:2. */
export async function runQueryAsync(log: string[]): Promise<void> {
  throw new Error('TODO(0.2): implement runQueryAsync');
}

/**
 * TODO(0.2): create a DisposableStack with `using`, register three cleanups with
 * stack.defer pushing 'first registered', 'second registered', 'third registered',
 * then push 'body'. Cleanups run in reverse order, so the log must be:
 * body, third registered, second registered, first registered.
 */
export function cleanupInReverse(log: string[]): void {
  throw new Error('TODO(0.2): implement cleanupInReverse');
}
