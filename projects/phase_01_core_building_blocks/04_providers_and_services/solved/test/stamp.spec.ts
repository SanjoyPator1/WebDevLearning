import { Test } from '@nestjs/testing';
import { ClockService } from '../src/clock/clock.service.js';
import { ReportService } from '../src/stamp/report.service.js';
import { StampService } from '../src/stamp/stamp.service.js';

describe('Task 1: @Injectable and constructor injection', () => {
  beforeEach(() => {
    ClockService.created = 0;
  });

  it('StampService receives ClockService through its constructor', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ClockService, StampService],
    }).compile();

    expect(moduleRef.get(StampService).stamp('hello')).toBe('tick-1 hello');
  });

  it('two consumers share ONE ClockService: the ticks continue where the other stopped', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ClockService, StampService, ReportService],
    }).compile();
    const stamps = moduleRef.get(StampService);
    const reports = moduleRef.get(ReportService);

    expect(stamps.stamp('a')).toBe('tick-1 a');
    expect(reports.line('b')).toBe('tick-2: b');
    expect(stamps.stamp('c')).toBe('tick-3 c');
    expect(ClockService.created).toBe(1);
  });

  it('every get() returns the same StampService instance (a provider is a singleton)', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ClockService, StampService],
    }).compile();

    expect(moduleRef.get(StampService)).toBe(moduleRef.get(StampService));
  });

  it('guard: Nest builds every provider at startup, even one nobody injects', async () => {
    await Test.createTestingModule({ providers: [ClockService] }).compile();

    expect(ClockService.created).toBe(1);
  });
});
