import { Module } from '@nestjs/common';
import { CounterModule } from '../counter/counter.module.js';
import { LegacyService } from './legacy.service.js';

// The bug was listing CounterService in this module's providers: that creates a SECOND
// instance owned by this module, with its own state. A provider has one home. Everyone else
// gets it by importing the module that owns it.
@Module({
  imports: [CounterModule],
  providers: [LegacyService],
  exports: [LegacyService],
})
export class LegacyModule {}
