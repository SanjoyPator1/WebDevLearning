import { Test } from '@nestjs/testing';
import { CounterModule } from '../src/counter/counter.module.js';
import { CounterService } from '../src/counter/counter.service.js';
import { LegacyModule } from '../src/legacy/legacy.module.js';
import { LegacyService } from '../src/legacy/legacy.service.js';

describe('Task 5: no second instance', () => {
  beforeEach(() => {
    CounterService.created = 0;
  });

  it('CounterModule and LegacyModule together create exactly one CounterService', async () => {
    await Test.createTestingModule({ imports: [CounterModule, LegacyModule] }).compile();

    expect(CounterService.created).toBe(1);
  });

  it('LegacyService counts on the very same CounterService that CounterModule owns', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [CounterModule, LegacyModule] }).compile();

    moduleRef.get(LegacyService).tick();

    expect(moduleRef.select(CounterModule).get(CounterService, { strict: true }).current()).toBe(1);
  });
});
