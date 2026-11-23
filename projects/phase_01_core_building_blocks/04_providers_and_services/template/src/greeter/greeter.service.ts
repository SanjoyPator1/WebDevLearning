import { Injectable } from '@nestjs/common';
import { sleep } from './sleep.js';

// TODO(1.4) Task 2
// This provider has a bug that only shows up when two calls overlap. Nest builds ONE instance
// and every request uses it, so look at what the instance remembers between calls.
// Run test/greeter.spec.ts, read what comes back, then fix the class. Do not change the
// signature of greet(): the delay only simulates real work such as a database call.
@Injectable()
export class GreeterService {
  private current = '';

  async greet(name: string, delayMs: number): Promise<string> {
    this.current = name;
    await sleep(delayMs);
    return `hello ${this.current}`;
  }
}
