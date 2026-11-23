import { Module } from '@nestjs/common';
import { CounterService } from '../counter/counter.service.js';
import { LegacyService } from './legacy.service.js';

// TODO(1.2) Task 5
// This module has a BUG: it lists CounterService in its own providers, so Nest creates a
// second CounterService just for this module. Fix it so the whole app has exactly ONE
// CounterService. Do not change LegacyService.
@Module({
  providers: [CounterService, LegacyService],
  exports: [LegacyService],
})
export class LegacyModule {}
