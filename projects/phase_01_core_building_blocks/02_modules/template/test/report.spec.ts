import { Test } from '@nestjs/testing';
import { CoreModule } from '../src/core/core.module.js';
import { CounterService } from '../src/counter/counter.service.js';
import { GreeterModule } from '../src/greeter/greeter.module.js';
import { GreeterService } from '../src/greeter/greeter.service.js';
import { ReportModule } from '../src/report/report.module.js';
import { ReportService } from '../src/report/report.service.js';

describe('Task 3: one shared instance, reached through a re-export', () => {
  beforeEach(() => {
    CounterService.created = 0;
  });

  it('ReportModule gets CounterService through CoreModule, which re-exports CounterModule', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [ReportModule] }).compile();

    expect(moduleRef.get(ReportService).summary()).toBe('greetings so far: 0');
  });

  it('guard: ReportModule imports CoreModule and nothing else', () => {
    expect(Reflect.getMetadata('imports', ReportModule)).toEqual([CoreModule]);
  });

  it('GreeterModule and ReportModule share ONE CounterService instance', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [GreeterModule, ReportModule] }).compile();

    moduleRef.get(GreeterService).greet('ada');

    expect(moduleRef.get(ReportService).summary()).toBe('greetings so far: 1');
    expect(CounterService.created).toBe(1);
  });
});
