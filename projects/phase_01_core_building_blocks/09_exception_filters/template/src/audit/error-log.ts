import { Injectable } from '@nestjs/common';

// Not part of this exercise: a shared notebook for the logging filter of Task 4.
@Injectable()
export class ErrorLog {
  readonly entries: string[] = [];

  add(entry: string): void {
    this.entries.push(entry);
  }
}
