// Kata 10: `using`, `await using` and DisposableStack (topic 0.2, TypeScript 5.2)
//
// Explicit resource management: a resource releases itself when the scope that
// declared it ends, whether by return, throw or break. It replaces the
// try/finally you would otherwise write by hand around every resource.

/** Sync resource. Implementing Disposable means having a [Symbol.dispose] method. */
export class Connection implements Disposable {
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

  [Symbol.dispose](): void {
    this.log.push(`close:${this.id}`);
  }
}

/** Async resource. Releasing it needs to await something, so it uses asyncDispose. */
export class AsyncConnection implements AsyncDisposable {
  constructor(
    private readonly log: string[],
    readonly id: number,
  ) {
    this.log.push(`open:${id}`);
  }

  async [Symbol.asyncDispose](): Promise<void> {
    await Promise.resolve();
    this.log.push(`close:${this.id}`);
  }
}

/** The connection is closed after the query, and also when the query throws. */
export function runQuery(log: string[], shouldThrow = false): string {
  using connection = new Connection(log, 1);
  if (shouldThrow) {
    throw new Error('query failed');
  }
  return connection.query('select 1');
}

export async function runQueryAsync(log: string[]): Promise<void> {
  await using connection = new AsyncConnection(log, 2);
  log.push(`using:${connection.id}`);
}

/**
 * DisposableStack collects cleanup callbacks and runs them in reverse order
 * (last registered, first released), like nested using declarations would.
 */
export function cleanupInReverse(log: string[]): void {
  using stack = new DisposableStack();
  stack.defer(() => log.push('first registered'));
  stack.defer(() => log.push('second registered'));
  stack.defer(() => log.push('third registered'));
  log.push('body');
}
