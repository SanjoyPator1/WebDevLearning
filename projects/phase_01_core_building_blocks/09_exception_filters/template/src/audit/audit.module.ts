import { Module } from '@nestjs/common';
import { ErrorLog } from './error-log.js';

// TODO(1.9) Task 4b
// Register LoggingFilter as a GLOBAL filter that Nest builds with dependency injection (it needs
// ErrorLog): add a provider under the APP_FILTER token (from @nestjs/core) with `useClass`.
// Unlike app.useGlobalFilters(new LoggingFilter()), which takes an instance built outside the container,
// this form injects ErrorLog, and it applies to the WHOLE application, including controllers of modules
// that never import this one. (A provider of the form { provide, useClass } is a custom provider, topic
// 2.2: copy the shape.)
@Module({ providers: [ErrorLog] })
export class AuditModule {}
