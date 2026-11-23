import { Module } from '@nestjs/common';
import { AuditLogStore } from './audit-log.store.js';
import { AuditService } from './audit.service.js';

// AuditService is the public API of this module, AuditLogStore is an implementation detail.
// Exporting only AuditService lets us change how events are stored later without touching
// any other module.
@Module({
  providers: [AuditLogStore, AuditService],
  exports: [AuditService],
})
export class AuditModule {}
