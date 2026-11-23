import { Module } from '@nestjs/common';
import { CoreModule } from '../core/core.module.js';
import { ReportController } from './report.controller.js';
import { ReportService } from './report.service.js';

// CounterService arrives through CoreModule's re-export. It is the same instance GreeterModule
// uses, because both paths lead to the one CounterModule in the module graph.
@Module({
  imports: [CoreModule],
  controllers: [ReportController],
  providers: [ReportService],
})
export class ReportModule {}
