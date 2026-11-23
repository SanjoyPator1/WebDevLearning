import { Injectable } from '@nestjs/common';
import { ClockService } from '../clock/clock.service.js';

// Task 1: two things make this a working provider.
//
// 1. A provider is registered in a module's `providers` list (the tests do that). That is
//    what lets Nest build it.
// 2. `private readonly clock: ClockService` is a constructor parameter property. TypeScript
//    records the parameter types as `design:paramtypes` (topic 0.3), and Nest reads them to
//    know what to pass in. ClockService is a class, so it is a usable token. An interface
//    would be erased to `Object` and could not be injected.
//
// What @Injectable() does is smaller than it looks: it only sets a marker (and the scope
// options, 2.4). The parameter types are emitted because the class has *a* decorator at all.
// Still, always write it: without any decorator TypeScript emits nothing, Nest builds the
// class with no arguments, and `this.clock` is silently undefined.
@Injectable()
export class StampService {
  constructor(private readonly clock: ClockService) {}

  stamp(text: string): string {
    return `${this.clock.now()} ${text}`;
  }
}
