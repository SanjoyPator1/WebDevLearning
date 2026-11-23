import { Injectable } from '@nestjs/common';
import { CounterService } from '../counter/counter.service.js';

// Not part of this exercise.
@Injectable()
export class LegacyService {
  constructor(private readonly counter: CounterService) {}

  tick(): number {
    return this.counter.next();
  }
}
