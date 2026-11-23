import { Injectable } from '@nestjs/common';

// Not part of this exercise: providers are topic 1.4. This one is given.
@Injectable()
export class CounterService {
  /** How many CounterService objects Nest has created. The tests use it to spot duplicate instances. */
  static created = 0;

  readonly instanceNo = ++CounterService.created;
  private count = 0;

  next(): number {
    return ++this.count;
  }

  current(): number {
    return this.count;
  }
}
