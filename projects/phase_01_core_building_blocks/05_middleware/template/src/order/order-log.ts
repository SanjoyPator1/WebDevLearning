import { Injectable } from '@nestjs/common';

// Not part of this exercise: a shared notebook that every middleware and the handler write into,
// so the tests can read in which order things ran.
@Injectable()
export class OrderLog {
  readonly entries: string[] = [];

  add(entry: string): void {
    this.entries.push(entry);
  }
}
