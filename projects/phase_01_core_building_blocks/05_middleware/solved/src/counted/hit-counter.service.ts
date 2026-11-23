import { Injectable } from '@nestjs/common';

// Not part of this exercise: a provider (topic 1.4) that the class middleware of Task 2 needs.
@Injectable()
export class HitCounterService {
  private hits = 0;

  next(): number {
    return ++this.hits;
  }
}
