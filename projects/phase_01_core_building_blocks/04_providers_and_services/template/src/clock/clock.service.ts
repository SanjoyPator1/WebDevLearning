import { Injectable } from '@nestjs/common';

// Not part of this exercise: a tiny stateful provider that the tasks inject. Every call to
// now() returns the next tick, so the tests can tell how many consumers share one instance.
// `created` counts how many times Nest built it: a duplicate instance shows up as a failing test.
@Injectable()
export class ClockService {
  static created = 0;
  private ticks = 0;

  constructor() {
    ClockService.created++;
  }

  now(): string {
    return `tick-${++this.ticks}`;
  }
}
