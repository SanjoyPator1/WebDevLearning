import { Module } from '@nestjs/common';
import { CounterModule } from '../counter/counter.module.js';

// Re-exporting: CoreModule imports CounterModule and then exports the whole module. A module
// that imports only CoreModule can inject everything CounterModule exports.
//
// The module has to be imported before it can be exported. And you re-export the MODULE:
// exporting the CounterService provider by itself would throw, because CoreModule does not
// own that provider.
@Module({
  imports: [CounterModule],
  exports: [CounterModule],
})
export class CoreModule {}
