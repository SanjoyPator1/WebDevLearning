import { Injectable } from '@nestjs/common';

// Not part of this exercise: counts how many times a handler really ran, so the tests can tell
// that a guard stopped a request BEFORE the handler.
@Injectable()
export class CallCounter {
  calls = 0;

  hit(): number {
    return ++this.calls;
  }
}
