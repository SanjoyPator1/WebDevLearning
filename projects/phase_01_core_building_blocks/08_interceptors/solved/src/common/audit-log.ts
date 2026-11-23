import { Injectable } from '@nestjs/common';

// Not part of this exercise: a shared notebook that interceptors and handlers write into, so the
// tests can read what happened and in which order.
@Injectable()
export class AuditLog {
  readonly entries: string[] = [];

  add(entry: string): void {
    this.entries.push(entry);
  }
}
