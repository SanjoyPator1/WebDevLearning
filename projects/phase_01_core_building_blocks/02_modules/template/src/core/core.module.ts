import { Module } from '@nestjs/common';

// TODO(1.2) Task 3
// CoreModule is a small "bundle" module. Anyone who imports CoreModule should get
// CounterService without having to import CounterModule themselves.
// Hint: this module has no providers of its own.
@Module({})
export class CoreModule {}
