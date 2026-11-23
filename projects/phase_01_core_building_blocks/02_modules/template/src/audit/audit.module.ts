import { Module } from '@nestjs/common';
import { AuditLogStore } from './audit-log.store.js';
import { AuditService } from './audit.service.js';

// TODO(1.2) Task 2
// Other modules should be able to use AuditService, but AuditLogStore is an
// implementation detail and must stay private to this module.
@Module({
  providers: [AuditLogStore, AuditService],
})
export class AuditModule {}
