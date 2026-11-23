import { Injectable } from '@nestjs/common';

// Not part of this exercise. This is the provider that must stay PRIVATE to AuditModule.
@Injectable()
export class AuditLogStore {
  readonly events: string[] = [];
}
