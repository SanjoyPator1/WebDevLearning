import { Injectable } from '@nestjs/common';
import { AuditLogStore } from './audit-log.store.js';

// Not part of this exercise. This is the provider that other modules are allowed to use.
@Injectable()
export class AuditService {
  constructor(private readonly store: AuditLogStore) {}

  record(event: string): void {
    this.store.events.push(event);
  }

  count(): number {
    return this.store.events.length;
  }
}
