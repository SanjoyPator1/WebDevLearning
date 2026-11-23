import { Controller, Get } from '@nestjs/common';
import { ReportService } from './report.service.js';

// Not part of this exercise: controllers are topic 1.3.
@Controller('report')
export class ReportController {
  constructor(private readonly report: ReportService) {}

  @Get()
  summary(): string {
    return this.report.summary();
  }
}
