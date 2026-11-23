import { Inject } from '@nestjs/common';
import { ClockService } from '../clock/clock.service.js';

// Task 3: `@Inject()` on a property is property injection. With no argument it uses the
// property's declared type (`design:type`, emitted by TypeScript) as the token: ClockService.
//
// Nest applies it AFTER it has called the constructor (`Injector.applyProperties`), so the
// property is undefined inside the constructor. That is why `clockSeenInConstructor` is
// undefined, and why code that needs the dependency during construction must use a
// constructor parameter instead.
//
// Why use it here at all: the metadata is stored on this class and is found for every
// subclass through the prototype chain. DailyReporter has no constructor and WeeklyReporter
// has one with a different dependency, and neither has to accept a ClockService and forward
// it with super(clock). With constructor injection, every subclass would.
//
// The cost: the dependency is no longer visible in the constructor signature, `new
// DailyReporter()` in a test leaves `clock` undefined, and the `!` tells TypeScript to
// trust that Nest fills it. Prefer the constructor, and keep this for base classes.
export abstract class BaseReporter {
  @Inject()
  protected readonly clock!: ClockService;
  readonly clockSeenInConstructor: unknown;

  constructor() {
    this.clockSeenInConstructor = this.clock;
  }

  protected abstract title(): string;

  header(): string {
    return `[${this.title()}] ${this.clock.now()}`;
  }
}
