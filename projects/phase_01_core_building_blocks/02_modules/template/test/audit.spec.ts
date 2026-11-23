import { Injectable, Module } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AuditLogStore } from '../src/audit/audit-log.store.js';
import { AuditModule } from '../src/audit/audit.module.js';
import { AuditService } from '../src/audit/audit.service.js';

describe('Task 2: private by default, public through exports', () => {
  it('a module that imports AuditModule can inject AuditService', async () => {
    @Injectable()
    class Consumer {
      constructor(readonly audit: AuditService) {}
    }
    @Module({ imports: [AuditModule], providers: [Consumer] })
    class ConsumerModule {}

    const moduleRef = await Test.createTestingModule({ imports: [ConsumerModule] }).compile();

    const { audit } = moduleRef.get(Consumer);
    audit.record('created');
    expect(audit.count()).toBe(1);
  });

  // This is a guard: it passes before you start, and it fails if you over-export.
  it('guard: AuditLogStore stays private, so a consumer cannot inject it', async () => {
    @Injectable()
    class Snoop {
      constructor(readonly store: AuditLogStore) {}
    }
    @Module({ imports: [AuditModule], providers: [Snoop] })
    class SnoopModule {}

    await expect(Test.createTestingModule({ imports: [SnoopModule] }).compile()).rejects.toThrow(
      /Nest can't resolve dependencies of the Snoop/,
    );
  });
});
