import { Injectable } from '@nestjs/common';
import { sleep } from './sleep.js';

// Task 2: Nest builds ONE GreeterService and every request shares it. The old version wrote
// the name into `this.current`, waited, and read it back. While it waited, another call
// overwrote the field, so both calls answered with the last name.
//
// The fix is to keep per-call data where per-call data belongs: in the arguments and local
// variables of the call. A singleton provider should hold only what is the same for every
// caller (its dependencies, a cache, a connection), never "the current user" or "the current
// request". If you really need data that follows one request around, see 2.4 (request
// scope) and 10.3 (AsyncLocalStorage).
@Injectable()
export class GreeterService {
  async greet(name: string, delayMs: number): Promise<string> {
    await sleep(delayMs);
    return `hello ${name}`;
  }
}
