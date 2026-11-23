import { ClockService } from '../clock/clock.service.js';

// TODO(1.4) Task 3
// BaseReporter is the parent of DailyReporter and WeeklyReporter. It needs ClockService, but
// it must NOT get it through a constructor: neither subclass should have to take a
// ClockService and pass it up with super(clock). Inject `clock` as a PROPERTY instead.
//
// Property injection is not available in the constructor: Nest fills the property after the
// object is built. `clockSeenInConstructor` records what the constructor saw, and a test
// checks it.
export abstract class BaseReporter {
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
