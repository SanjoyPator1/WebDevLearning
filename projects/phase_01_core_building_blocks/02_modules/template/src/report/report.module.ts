import { Module } from '@nestjs/common';
import { ReportController } from './report.controller.js';
import { ReportService } from './report.service.js';

// TODO(1.2) Task 3
// ReportService needs CounterService. Get it through CoreModule only (do NOT import
// CounterModule here), and do NOT list CounterService in providers.
@Module({
  controllers: [ReportController],
  providers: [ReportService],
})
export class ReportModule {}
