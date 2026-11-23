import { Injectable } from '@nestjs/common';
import { CounterService } from '../counter/counter.service.js';

// Not part of this exercise.
@Injectable()
export class ReportService {
  constructor(private readonly counter: CounterService) {}

  summary(): string {
    return `greetings so far: ${this.counter.current()}`;
  }
}
