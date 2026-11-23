import { Module } from '@nestjs/common';
import { CounterService } from './counter.service.js';

// Providers are private to the module that declares them. `exports` is the module's public
// API: a module that imports CounterModule can inject CounterService, nothing else from here.
// Because a module is a singleton, every importer shares this one CounterService instance.
@Module({
  providers: [CounterService],
  exports: [CounterService],
})
export class CounterModule {}
