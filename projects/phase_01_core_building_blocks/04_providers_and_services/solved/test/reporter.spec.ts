import { Test } from '@nestjs/testing';
import { ClockService } from '../src/clock/clock.service.js';
import { DailyReporter } from '../src/reporter/daily-reporter.js';
import { FormatterService } from '../src/reporter/formatter.service.js';
import { WeeklyReporter } from '../src/reporter/weekly-reporter.js';

describe('Task 3: property injection', () => {
  beforeEach(() => {
    ClockService.created = 0;
  });

  it('DailyReporter has no constructor, and still gets the clock from BaseReporter', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ClockService, DailyReporter],
    }).compile();

    expect(moduleRef.get(DailyReporter).header()).toBe('[daily] tick-1');
  });

  it('WeeklyReporter has its own constructor dependency and inherits the property one', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ClockService, FormatterService, WeeklyReporter],
    }).compile();

    expect(moduleRef.get(WeeklyReporter).header()).toBe('[WEEKLY] tick-1');
  });

  it('both reporters share ONE ClockService', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ClockService, FormatterService, DailyReporter, WeeklyReporter],
    }).compile();

    expect(moduleRef.get(DailyReporter).header()).toBe('[daily] tick-1');
    expect(moduleRef.get(WeeklyReporter).header()).toBe('[WEEKLY] tick-2');
    expect(ClockService.created).toBe(1);
  });

  it('the property is filled AFTER construction: the constructor sees undefined', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ClockService, DailyReporter],
    }).compile();

    expect(moduleRef.get(DailyReporter).clockSeenInConstructor).toBeUndefined();
  });
});
