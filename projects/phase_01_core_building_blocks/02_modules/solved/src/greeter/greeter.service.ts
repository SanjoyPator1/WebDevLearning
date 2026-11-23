import { Injectable } from '@nestjs/common';
import { CounterService } from '../counter/counter.service.js';

// Not part of this exercise.
@Injectable()
export class GreeterService {
  constructor(private readonly counter: CounterService) {}

  greet(name: string): string {
    return `Hello, ${name}! (#${this.counter.next()})`;
  }
}
