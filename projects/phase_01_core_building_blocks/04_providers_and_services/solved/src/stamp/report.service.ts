import { Injectable } from '@nestjs/common';
import { ClockService } from '../clock/clock.service.js';

// Not part of this exercise: a second consumer of ClockService, finished, so that Task 1's
// tests can show that two consumers share one instance. Read it as the model for Task 1.
@Injectable()
export class ReportService {
  constructor(private readonly clock: ClockService) {}

  line(text: string): string {
    return `${this.clock.now()}: ${text}`;
  }
}
