import { Injectable } from '@nestjs/common';

// Not part of this exercise: a provider (topic 1.4) that StampInterceptor needs.
@Injectable()
export class StampService {
  private count = 0;

  next(): string {
    return `stamp-${++this.count}`;
  }
}
