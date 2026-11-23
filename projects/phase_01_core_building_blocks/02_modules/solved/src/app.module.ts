import { Module } from '@nestjs/common';
import { AuditModule } from './audit/audit.module.js';
import { GreeterModule } from './greeter/greeter.module.js';
import { LegacyModule } from './legacy/legacy.module.js';
import { LoggerModule } from './logger/logger.module.js';
import { NoticeModule } from './notice/notice.module.js';
import { PrefixModule } from './prefix/prefix.module.js';
import { ReportModule } from './report/report.module.js';

// The root module only composes. Import order does not matter here because no two imported
// modules export the same token. LoggerModule is imported once, which is what registers its
// global scope for everyone else.
@Module({
  imports: [
    LoggerModule,
    GreeterModule,
    ReportModule,
    AuditModule,
    NoticeModule,
    LegacyModule,
    PrefixModule.forRoot({ prefix: '> ' }),
  ],
})
export class AppModule {}
