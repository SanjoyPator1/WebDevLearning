import { Module } from '@nestjs/common';

// TODO(1.2) Task 7
// Wire the application together. The root module should import:
//   LoggerModule, GreeterModule, ReportModule, AuditModule, NoticeModule, LegacyModule
//   and PrefixModule.forRoot({ prefix: '> ' })
// Then run the end-to-end test: `pnpm test:e2e`.
@Module({})
export class AppModule {}
